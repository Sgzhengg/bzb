"""
Redis 缓存服务 - 标中宝
提供统一的缓存接口和装饰器
"""

import json
import logging
from functools import wraps
from typing import Optional, Any, Callable, TypeVar, Union

import redis.asyncio as aioredis
from redis.exceptions import RedisError

from app.core.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ============================================================
# Redis 连接管理
# ============================================================

class RedisCache:
    """Redis 缓存管理器（异步）"""

    _client: Optional[aioredis.Redis] = None
    _enabled: bool = False

    @classmethod
    async def get_client(cls) -> Optional[aioredis.Redis]:
        """获取 Redis 客户端（懒加载）"""
        if cls._client is not None:
            return cls._client

        # 检查是否启用 Redis
        if not settings.REDIS_URL:
            cls._enabled = False
            logger.warning("Redis 未配置（BZB_REDIS_URL 为空），缓存已禁用")
            return None

        try:
            cls._client = await aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
            # 测试连接
            await cls._client.ping()
            cls._enabled = True
            logger.info(f"Redis 连接成功: {settings.REDIS_URL}")
            return cls._client
        except RedisError as e:
            cls._enabled = False
            logger.error(f"Redis 连接失败: {e}")
            return None

    @classmethod
    async def close(cls):
        """关闭 Redis 连接"""
        if cls._client:
            await cls._client.aclose()
            cls._client = None
            cls._enabled = False
            logger.info("Redis 连接已关闭")

    @classmethod
    def is_enabled(cls) -> bool:
        """检查缓存是否启用"""
        return cls._enabled

    @classmethod
    async def get(cls, key: str) -> Optional[str]:
        """获取缓存"""
        if not cls.is_enabled():
            return None
        try:
            client = await cls.get_client()
            if client:
                return await client.get(key)
        except RedisError as e:
            logger.error(f"Redis GET 失败: {e}")
        return None

    @classmethod
    async def set(cls, key: str, value: str, ttl: int = 300) -> bool:
        """设置缓存"""
        if not cls.is_enabled():
            return False
        try:
            client = await cls.get_client()
            if client:
                await client.setex(key, ttl, value)
                return True
        except RedisError as e:
            logger.error(f"Redis SET 失败: {e}")
        return False

    @classmethod
    async def delete(cls, *keys: str) -> int:
        """删除缓存"""
        if not cls.is_enabled():
            return 0
        try:
            client = await cls.get_client()
            if client and keys:
                return await client.delete(*keys)
        except RedisError as e:
            logger.error(f"Redis DEL 失败: {e}")
        return 0

    @classmethod
    async def exists(cls, *keys: str) -> int:
        """检查键是否存在"""
        if not cls.is_enabled():
            return 0
        try:
            client = await cls.get_client()
            if client:
                return await client.exists(*keys)
        except RedisError as e:
            logger.error(f"Redis EXISTS 失败: {e}")
        return 0

    @classmethod
    async def get_json(cls, key: str) -> Optional[Any]:
        """获取 JSON 缓存"""
        value = await cls.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError as e:
                logger.error(f"JSON 解析失败: {e}")
        return None

    @classmethod
    async def set_json(cls, key: str, value: Any, ttl: int = 300) -> bool:
        """设置 JSON 缓存"""
        try:
            json_str = json.dumps(value, ensure_ascii=False, default=str)
            return await cls.set(key, json_str, ttl)
        except (json.JSONEncodeError, TypeError) as e:
            logger.error(f"JSON 序列化失败: {e}")
        return False

    @classmethod
    async def incr(cls, key: str, amount: int = 1) -> Optional[int]:
        """原子递增（用于限流）"""
        if not cls.is_enabled():
            return None
        try:
            client = await cls.get_client()
            if client:
                return await client.incrby(key, amount)
        except RedisError as e:
            logger.error(f"Redis INCR 失败: {e}")
        return None

    @classmethod
    async def expire(cls, key: str, ttl: int) -> bool:
        """设置过期时间"""
        if not cls.is_enabled():
            return False
        try:
            client = await cls.get_client()
            if client:
                return await client.expire(key, ttl)
        except RedisError as e:
            logger.error(f"Redis EXPIRE 失败: {e}")
        return False


# ============================================================
# 缓存装饰器
# ============================================================

def cached(ttl: int = 300, key_prefix: str = "", key_func: Optional[Callable] = None):
    """
    缓存装饰器（异步函数）

    Args:
        ttl: 缓存过期时间（秒）
        key_prefix: 缓存键前缀
        key_func: 自定义键生成函数

    Usage:
        @cached(ttl=600, key_prefix="announcement:")
        async def get_announcement(id: int):
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # 默认键生成策略：prefix:func_name:args_hash
                args_str = f"{args}:{kwargs}"
                import hashlib
                args_hash = hashlib.md5(args_str.encode()).hexdigest()[:8]
                cache_key = f"{key_prefix}{func.__name__}:{args_hash}"

            # 尝试从缓存获取
            cached_value = await RedisCache.get_json(cache_key)
            if cached_value is not None:
                logger.debug(f"缓存命中: {cache_key}")
                return cached_value

            # 执行原函数
            result = await func(*args, **kwargs)

            # 存入缓存
            if result is not None:
                await RedisCache.set_json(cache_key, result, ttl)
                logger.debug(f"缓存已设置: {cache_key} (TTL={ttl}s)")

            return result

        return wrapper
    return decorator


def invalidate_pattern(*patterns: str):
    """
    批量删除缓存模式

    Usage:
        @invalidate_pattern("announcement:*", "city:*")
        async def update_announcement(...):
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            result = await func(*args, **kwargs)

            # 删除匹配的缓存键
            if RedisCache.is_enabled():
                try:
                    client = await RedisCache.get_client()
                    if client:
                        for pattern in patterns:
                            keys = []
                            async for key in client.scan_iter(match=pattern):
                                keys.append(key)
                            if keys:
                                await client.delete(*keys)
                                logger.info(f"已清除缓存模式: {pattern} ({len(keys)} keys)")
                except RedisError as e:
                    logger.error(f"缓存清除失败: {e}")

            return result
        return wrapper
    return decorator


# ============================================================
# 限流装饰器（基于 Redis）
# ============================================================

def rate_limit(max_requests: int, window: int, key_func: Callable):
    """
    限流装饰器（基于 Redis 滑动窗口）

    Args:
        max_requests: 时间窗口内最大请求数
        window: 时间窗口（秒）
        key_func: 限流键生成函数（如 lambda request: request.client.host）

    Raises:
        HTTPException: 超过限流阈值

    Usage:
        @rate_limit(max_requests=30, window=60, key_func=lambda r: r.client.host)
        async def my_endpoint(request: Request):
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            from fastapi import HTTPException, Request

            # 提取 Request 对象
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request:
                return await func(*args, **kwargs)

            # 生成限流键
            limit_key = f"ratelimit:{key_func(request)}"

            # 原子递增
            current = await RedisCache.incr(limit_key)
            if current is None:
                # Redis 不可用，直接放行
                return await func(*args, **kwargs)

            # 首次请求设置过期时间
            if current == 1:
                await RedisCache.expire(limit_key, window)

            # 检查是否超过限制
            if current > max_requests:
                logger.warning(f"限流触发: {limit_key} (current={current}, max={max_requests})")
                raise HTTPException(
                    status_code=429,
                    detail=f"请求过于频繁，请稍后再试 ({window}秒内最多{max_requests}次)",
                )

            return await func(*args, **kwargs)

        return wrapper
    return decorator


# ============================================================
# 生命周期钩子
# ============================================================

async def init_cache():
    """初始化缓存（在应用启动时调用）"""
    await RedisCache.get_client()


async def close_cache():
    """关闭缓存（在应用关闭时调用）"""
    await RedisCache.close()
