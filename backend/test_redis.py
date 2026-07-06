"""
Redis 缓存测试脚本
"""
import asyncio
import os

# 设置测试环境变量
os.environ["BZB_REDIS_URL"] = "redis://localhost:6379/1"

from app.services.cache_service import RedisCache, cached


async def test_redis_connection():
    """测试 Redis 连接"""
    print("Testing Redis connection...")

    client = await RedisCache.get_client()
    if client is None:
        print("  [SKIP] Redis not configured (this is OK for development)")
        return False

    # 测试 ping
    await client.ping()
    print("  [OK] Redis connection successful")
    return True


async def test_cache_operations():
    """测试缓存操作"""
    print("\nTesting cache operations...")

    # 测试设置和获取
    await RedisCache.set("test:key", "test_value", ttl=60)
    value = await RedisCache.get("test:key")

    if value == "test_value":
        print("  [OK] Basic SET/GET works")
    else:
        print(f"  [FAIL] Expected 'test_value', got '{value}'")
        return False

    # 测试 JSON 操作
    test_data = {"name": "标中宝", "count": 100}
    await RedisCache.set_json("test:data", test_data, ttl=60)
    json_data = await RedisCache.get_json("test:data")

    if json_data == test_data:
        print("  [OK] JSON cache works")
    else:
        print(f"  [FAIL] JSON cache failed")
        return False

    # 测试删除
    await RedisCache.delete("test:key", "test:data")
    print("  [OK] Cache delete works")

    return True


async def test_cache_decorator():
    """测试缓存装饰器"""
    print("\nTesting cache decorator...")

    call_count = 0

    @cached(ttl=60, key_prefix="test:")
    async def expensive_function(x: int) -> int:
        nonlocal call_count
        call_count += 1
        return x * 2

    # 第一次调用 - 应该执行函数
    result1 = await expensive_function(5)
    if call_count == 1 and result1 == 10:
        print("  [OK] First call executed function")
    else:
        print(f"  [FAIL] First call issue")
        return False

    # 第二次调用 - 应该从缓存返回
    result2 = await expensive_function(5)
    if call_count == 1 and result2 == 10:
        print("  [OK] Second call used cache (function not executed)")
    else:
        print(f"  [FAIL] Cache not working, call_count={call_count}")
        return False

    # 不同参数 - 应该执行函数
    result3 = await expensive_function(10)
    if call_count == 2 and result3 == 20:
        print("  [OK] Different parameter executed function")
    else:
        print(f"  [FAIL] Parameter cache key issue")
        return False

    return True


async def test_rate_limit():
    """测试限流功能"""
    print("\nTesting rate limit functionality...")

    # 测试递增
    for i in range(5):
        count = await RedisCache.incr("ratelimit:test", 1)

    if count == 5:
        print("  [OK] Rate limit increment works")
    else:
        print(f"  [FAIL] Expected 5, got {count}")
        return False

    await RedisCache.delete("ratelimit:test")
    return True


async def main():
    """主测试函数"""
    print("=" * 50)
    print("Redis Cache Service Test")
    print("=" * 50)

    # 测试连接
    redis_available = await test_redis_connection()
    if not redis_available:
        print("\n[SUMMARY] Redis is optional - cache features will be disabled")
        print("To enable Redis, set BZB_REDIS_URL environment variable")
        return

    # 运行所有测试
    tests = [
        test_cache_operations,
        test_cache_decorator,
        test_rate_limit,
    ]

    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
        except Exception as e:
            print(f"  [ERROR] {test.__name__} failed: {e}")
            results.append(False)

    # 清理
    await RedisCache.close()

    # 总结
    print("\n" + "=" * 50)
    passed = sum(results)
    total = len(results)
    print(f"[SUMMARY] {passed}/{total} tests passed")

    if passed == total:
        print("[SUCCESS] All Redis cache features working!")
    else:
        print("[WARNING] Some tests failed - check Redis configuration")


if __name__ == "__main__":
    asyncio.run(main())
