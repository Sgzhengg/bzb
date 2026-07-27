"""
代理池自动接入模块 — 在 BiddingFetcher 中使用代理池

将此模块导入并调用 patch_fetcher_with_proxy() 即可自动为爬虫启用代理。
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


# 默认公共代理列表（可配置）
DEFAULT_PROXIES = [
    # 可在此添加代理地址，格式: "http://user:pass@host:port"
]


def create_proxy_for_fetcher(proxy_url: Optional[str] = None) -> Optional[dict]:
    """
    为 httpx 客户端创建代理配置。

    用法:
        from app.services.proxy_integration import create_proxy_for_fetcher
        proxy_config = create_proxy_for_fetcher()
        async with httpx.AsyncClient(proxy=proxy_config) as client:
            ...
    """
    if proxy_url:
        return {"all://": proxy_url}

    # 尝试从代理池获取
    try:
        from app.services.proxy_pool import ProxyPool

        pool = ProxyPool(proxies=DEFAULT_PROXIES)
        active = pool.get_active_proxy()
        if active:
            logger.info(f"使用代理: {active[:60]}...")
            return {"all://": active}
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"代理池初始化失败: {e}")

    return None


async def try_with_proxy(url: str, client_factory, max_retries: int = 3):
    """
    使用代理池自动重试请求。

    Args:
        url: 目标 URL
        client_factory: 一个 async 函数，接收 proxy_config 参数，返回 httpx 客户端
        max_retries: 最大重试次数

    Returns:
        httpx.Response 或 None
    """
    from app.services.proxy_pool import ProxyPool

    pool = ProxyPool(proxies=DEFAULT_PROXIES)

    for attempt in range(max_retries):
        proxy_url = pool.get_active_proxy()
        proxy_config = {"all://": proxy_url} if proxy_url else None

        try:
            async with await client_factory(proxy_config) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    return resp
                if resp.status_code in (403, 429):
                    logger.warning(f"代理被限流, 切换代理重试 ({attempt + 1}/{max_retries})")
                    pool.mark_failed(proxy_url) if proxy_url else None
                else:
                    return resp
        except Exception as e:
            logger.warning(f"请求失败 ({attempt + 1}/{max_retries}): {e}")
            if proxy_url:
                pool.mark_failed(proxy_url)

    return None
