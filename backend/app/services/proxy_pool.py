"""
代理池服务 - 提高爬虫反爬能力

功能：
1. 动态代理池管理
2. 健康检查
3. 自动切换
4. 失败重试
"""

import asyncio
import logging
import random
from typing import List, Optional, Dict
from datetime import datetime, timedelta
import httpx

logger = logging.getLogger(__name__)


class ProxyPool:
    """代理池管理器"""

    def __init__(
        self,
        proxies: Optional[List[str]] = None,
        check_url: str = "http://httpbin.org/ip",
        check_interval: int = 300,  # 5分钟
        max_failures: int = 3,
    ):
        """
        Args:
            proxies: 代理列表 ["http://user:pass@host:port", ...]
            check_url: 用于健康检查的URL
            check_interval: 健康检查间隔（秒）
            max_failures: 最大失败次数后标记为不可用
        """
        self.proxies: List[Dict] = []
        self.current_index = 0
        self.check_url = check_url
        self.check_interval = check_interval
        self.max_failures = max_failures
        self.last_check = None
        self._check_task = None

        if proxies:
            for proxy in proxies:
                self.add_proxy(proxy)

    def add_proxy(self, proxy_url: str) -> bool:
        """添加代理到池中"""
        try:
            self.proxies.append({
                "url": proxy_url,
                "failed_count": 0,
                "last_used": None,
                "last_check": None,
                "is_healthy": True,
            })
            logger.info(f"添加代理: {proxy_url[:20]}...")
            return True
        except Exception as e:
            logger.error(f"添加代理失败: {e}")
            return False

    async def get_proxy(self) -> Optional[str]:
        """获取一个可用代理"""
        if not self.proxies:
            return None

        # 尝试获取健康的代理
        healthy_proxies = [p for p in self.proxies if p["is_healthy"]]

        if not healthy_proxies:
            logger.warning("所有代理不可用，返回 None")
            return None

        # 轮询选择
        proxy = healthy_proxies[self.current_index % len(healthy_proxies)]
        self.current_index += 1

        proxy["last_used"] = datetime.now()
        return proxy["url"]

    async def mark_failure(self, proxy_url: str):
        """标记代理失败"""
        for proxy in self.proxies:
            if proxy["url"] == proxy_url:
                proxy["failed_count"] += 1
                if proxy["failed_count"] >= self.max_failures:
                    proxy["is_healthy"] = False
                    logger.warning(f"代理已标记为不可用: {proxy_url[:20]}... (失败{proxy['failed_count']}次)")
                break

    async def mark_success(self, proxy_url: str):
        """标记代理成功（重置失败计数）"""
        for proxy in self.proxies:
            if proxy["url"] == proxy_url:
                proxy["failed_count"] = 0
                if not proxy["is_healthy"]:
                    proxy["is_healthy"] = True
                    logger.info(f"代理恢复可用: {proxy_url[:20]}...")
                break

    async def health_check(self) -> Dict:
        """执行代理健康检查"""
        if not self.proxies:
            return {"total": 0, "healthy": 0, "unhealthy": 0}

        logger.info(f"开始代理健康检查 ({len(self.proxies)} 个代理)")

        healthy_count = 0
        unhealthy_count = 0

        async with httpx.AsyncClient(timeout=10) as client:
            for proxy in self.proxies:
                try:
                    response = await client.get(
                        self.check_url,
                        proxy=proxy["url"],
                    )
                    if response.status_code == 200:
                        proxy["is_healthy"] = True
                        proxy["failed_count"] = 0
                        proxy["last_check"] = datetime.now()
                        healthy_count += 1
                    else:
                        proxy["is_healthy"] = False
                        proxy["last_check"] = datetime.now()
                        unhealthy_count += 1
                except Exception as e:
                    proxy["is_healthy"] = False
                    proxy["last_check"] = datetime.now()
                    unhealthy_count += 1

        self.last_check = datetime.now()
        result = {
            "total": len(self.proxies),
            "healthy": healthy_count,
            "unhealthy": unhealthy_count,
            "check_time": self.last_check.isoformat(),
        }

        logger.info(f"代理健康检查完成: {result}")
        return result

    async def start_auto_check(self):
        """启动自动健康检查"""
        if self._check_task is not None:
            logger.warning("自动健康检查已在运行")
            return

        async def auto_check():
            while True:
                try:
                    await self.health_check()
                    await asyncio.sleep(self.check_interval)
                except asyncio.CancelledError:
                    logger.info("自动健康检查已停止")
                    break
                except Exception as e:
                    logger.error(f"自动健康检查出错: {e}")
                    await asyncio.sleep(self.check_interval)

        self._check_task = asyncio.create_task(auto_check())
        logger.info(f"自动健康检查已启动（间隔: {self.check_interval}秒）")

    async def stop_auto_check(self):
        """停止自动健康检查"""
        if self._check_task:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass
            self._check_task = None
            logger.info("自动健康检查已停止")

    def get_status(self) -> Dict:
        """获取代理池状态"""
        healthy = sum(1 for p in self.proxies if p["is_healthy"])
        return {
            "total_proxies": len(self.proxies),
            "healthy_proxies": healthy,
            "unhealthy_proxies": len(self.proxies) - healthy,
            "current_index": self.current_index,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "auto_check_running": self._check_task is not None,
        }


# ============================================================
# 全局代理池实例
# ============================================================

_global_proxy_pool: Optional[ProxyPool] = None


def get_proxy_pool() -> ProxyPool:
    """获取全局代理池实例"""
    global _global_proxy_pool
    if _global_proxy_pool is None:
        # 从环境变量或配置加载代理
        proxies = _load_proxies_from_config()
        _global_proxy_pool = ProxyPool(proxies=proxies)
    return _global_proxy_pool


def _load_proxies_from_config() -> List[str]:
    """从配置加载代理列表"""
    import os

    proxy_env = os.getenv("BZB_PROXY_LIST")
    if proxy_env:
        return [p.strip() for p in proxy_env.split(",") if p.strip()]

    # 也可以从配置文件读取
    try:
        from app.core.config import settings
        if hasattr(settings, "PROXY_LIST") and settings.PROXY_LIST:
            return settings.PROXY_LIST
    except:
        pass

    return []


# ============================================================
# 代理装饰器（用于爬虫请求）
# ============================================================

def with_proxy(func):
    """
    代理装饰器：自动为请求添加代理

    Usage:
        @with_proxy
        async def fetch_url(url: str):
            return await httpx.get(url)
    """
    async def wrapper(*args, **kwargs):
        proxy_pool = get_proxy_pool()
        proxy = await proxy_pool.get_proxy() if proxy_pool else None

        try:
            if proxy:
                kwargs["proxy"] = proxy
                logger.debug(f"使用代理: {proxy[:20]}...")

            result = await func(*args, **kwargs)

            if proxy:
                await proxy_pool.mark_success(proxy)

            return result

        except Exception as e:
            if proxy:
                await proxy_pool.mark_failure(proxy)
            raise

    return wrapper
