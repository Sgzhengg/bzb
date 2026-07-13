"""
HTTP 抓取模块
提供带限速、重试、User-Agent 轮换的异步 HTTP 请求能力。
"""

import asyncio
import random
import time
import ssl
import logging
from typing import Optional, Dict, Tuple

import httpx

from .config import (
    USER_AGENTS,
    BASE_HEADERS,
    MIN_REQUEST_INTERVAL,
    REQUEST_TIMEOUT,
    MAX_RETRIES,
    RETRY_BACKOFF_BASE,
)

logger = logging.getLogger(__name__)


def _get_ssl_context() -> ssl.SSLContext:
    """创建兼容 b2b.10086.cn 的 SSL Context（旧版 TLS 重协商）。"""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    ctx.options |= 0x4  # SSL_OP_LEGACY_SERVER_CONNECT
    return ctx


class RateLimiter:
    """
    请求频率控制器。

    确保两次请求之间的间隔不小于 MIN_REQUEST_INTERVAL 秒。
    """

    def __init__(self, min_interval: float = MIN_REQUEST_INTERVAL):
        self.min_interval = min_interval
        self._last_request_time: float = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self):
        """获取请求许可，必要时等待。"""
        async with self._lock:
            now = time.monotonic()
            wait_time = self._last_request_time + self.min_interval - now
            if wait_time > 0:
                logger.debug(f"限速等待 {wait_time:.1f} 秒...")
                await asyncio.sleep(wait_time)
            self._last_request_time = time.monotonic()

    @property
    def last_request_time(self) -> float:
        return self._last_request_time


class BiddingFetcher:
    """
    招标公告 HTTP 抓取器。

    特性：
    - User-Agent 轮换
    - 指数退避重试（最多 MAX_RETRIES 次）
    - 请求频率限制
    - 自动解压 gzip/deflate/brotli
    - 超时控制
    """

    def __init__(
        self,
        rate_limiter: Optional[RateLimiter] = None,
        timeout: float = REQUEST_TIMEOUT,
    ):
        self._rate_limiter = rate_limiter or RateLimiter()
        self._timeout = timeout
        self._ua_index = 0
        self._client: Optional[httpx.AsyncClient] = None

    def _next_user_agent(self) -> str:
        """轮换获取下一个 User-Agent。"""
        ua = USER_AGENTS[self._ua_index % len(USER_AGENTS)]
        self._ua_index += 1
        return ua

    def _build_headers(self) -> Dict[str, str]:
        """构建请求头。"""
        headers = BASE_HEADERS.copy()
        headers["User-Agent"] = self._next_user_agent()
        return headers

    async def _ensure_client(self):
        """确保 HTTP 客户端已初始化。"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout),
                follow_redirects=True,
                limits=httpx.Limits(max_connections=5),
                verify=_get_ssl_context(),
            )

    async def close(self):
        """关闭 HTTP 客户端。"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def fetch(
        self,
        url: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Tuple[int, str]:
        """
        抓取指定 URL，返回 (状态码, 响应文本)。

        自动处理重试和限速。

        Args:
            url: 目标 URL
            params: 查询参数
            headers: 额外请求头

        Returns:
            (HTTP状态码, 响应文本)

        Raises:
            httpx.HTTPError: 所有重试均失败时抛出
        """
        await self._ensure_client()

        merged_headers = self._build_headers()
        if headers:
            merged_headers.update(headers)

        last_exception = None

        for attempt in range(MAX_RETRIES + 1):
            try:
                # 频率控制
                await self._rate_limiter.acquire()

                logger.info(
                    f"请求 [{attempt + 1}/{MAX_RETRIES + 1}]: {url[:120]}"
                )

                response = await self._client.get(
                    url,
                    params=params,
                    headers=merged_headers,
                )

                status = response.status_code

                # 成功
                if 200 <= status < 300:
                    # 检测编码
                    encoding = response.charset_encoding or "utf-8"
                    try:
                        text = response.text
                    except Exception:
                        text = response.content.decode(encoding, errors="replace")
                    logger.info(f"请求成功: {status} ({len(text)} 字节)")
                    return status, text

                # 429 限流特殊处理
                if status == 429:
                    wait = RETRY_BACKOFF_BASE * (2 ** attempt)
                    logger.warning(f"触发限流 429，等待 {wait} 秒...")
                    await asyncio.sleep(wait)
                    continue

                # 其他非 2xx
                logger.warning(f"HTTP {status}: {url[:120]}")
                if attempt < MAX_RETRIES:
                    wait = RETRY_BACKOFF_BASE * (2 ** attempt)
                    logger.info(f"重试等待 {wait} 秒...")
                    await asyncio.sleep(wait)

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_exception = e
                logger.warning(f"网络错误 (尝试 {attempt + 1}): {e}")
                if attempt < MAX_RETRIES:
                    wait = RETRY_BACKOFF_BASE * (2 ** attempt)
                    await asyncio.sleep(wait)

            except httpx.HTTPStatusError as e:
                last_exception = e
                logger.error(f"HTTP 状态错误: {e}")
                if attempt < MAX_RETRIES and e.response.status_code >= 500:
                    wait = RETRY_BACKOFF_BASE * (2 ** attempt)
                    await asyncio.sleep(wait)
                else:
                    raise

            except Exception as e:
                last_exception = e
                logger.error(f"未知错误: {e}")
                if attempt < MAX_RETRIES:
                    wait = RETRY_BACKOFF_BASE * (2 ** attempt)
                    await asyncio.sleep(wait)

        raise last_exception or RuntimeError(f"所有重试均失败: {url}")


# ============================================================
# 便捷函数
# ============================================================

async def fetch_page(url: str, params: Optional[Dict] = None) -> Tuple[int, str]:
    """
    便捷函数：单次抓取页面。

    Args:
        url: 目标 URL
        params: 查询参数

    Returns:
        (状态码, HTML 文本)
    """
    fetcher = BiddingFetcher()
    try:
        return await fetcher.fetch(url, params=params)
    finally:
        await fetcher.close()
