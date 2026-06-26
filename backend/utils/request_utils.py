"""
标中宝 V1 — HTTP 请求工具模块

提供增强的反爬策略:
  - 智能随机延迟（3-8s 可配置）
  - 按域名限速（令牌桶算法）
  - User-Agent 轮换池（20+ 真实浏览器）
  - 代理 IP 轮换支持
  - 指数退避重试（403/429/5xx）
  - 会话保持 + Cookie 管理
  - 请求统计与监控

使用:
    from utils.request_utils import RequestSession, random_delay

    session = RequestSession(domain="zhaobiao.cn", rpm=12)
    resp = session.get("https://www.zhaobiao.cn/search", params={...})
"""

import logging
import random
import time
import threading
from typing import Optional, Dict, List
from urllib.parse import urlparse

import httpx

logger = logging.getLogger("request_utils")


# ============================================================
# User-Agent 池（20 个真实浏览器）
# ============================================================

USER_AGENT_POOL = [
    # Chrome Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    # Chrome Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    # Firefox Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    # Firefox Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.5; rv:126.0) Gecko/20100101 Firefox/126.0",
    # Edge Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    # Safari Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    # Chrome Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
    # Opera
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 OPR/110.0.0.0",
    # Mobile
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.33 Mobile Safari/537.36",
    # Additional desktop
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]


def random_ua() -> str:
    """随机选取一个 User-Agent。"""
    return random.choice(USER_AGENT_POOL)


def random_delay(min_sec: float = 3.0, max_sec: float = 8.0):
    """随机延迟，避免规律性请求。"""
    delay = random.uniform(min_sec, max_sec)
    logger.debug(f"⏳ 随机延迟 {delay:.1f}s")
    time.sleep(delay)


# ============================================================
# 令牌桶限速器（按域名）
# ============================================================

class TokenBucket:
    """
    令牌桶算法实现按域名限速。

    用法:
        bucket = TokenBucket(rpm=15)   # 每分钟最多15次
        bucket.acquire()               # 阻塞直到获取令牌
    """

    def __init__(self, rpm: int = 15):
        self.rpm = rpm
        self.rate = rpm / 60.0
        self.capacity = rpm
        self.tokens = float(rpm)
        self.last_refill = time.monotonic()
        self.lock = threading.Lock()

    def acquire(self):
        """获取一个令牌，阻塞直到可用。"""
        with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_refill = now

            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return

            wait = (1.0 - self.tokens) / self.rate
            logger.debug(f"⏳ 限速等待 {wait:.1f}s (桶: {self.tokens:.1f}/{self.capacity})")

        time.sleep(wait)
        with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_refill = now
            self.tokens -= 1.0


# 全局域名限速器注册表
_domain_buckets: Dict[str, TokenBucket] = {}
_buckets_lock = threading.Lock()


def get_domain_bucket(domain: str, rpm: int = 15) -> TokenBucket:
    """获取或创建域名对应的限速桶。"""
    with _buckets_lock:
        if domain not in _domain_buckets:
            _domain_buckets[domain] = TokenBucket(rpm)
        return _domain_buckets[domain]


# ============================================================
# 增强型请求会话
# ============================================================

class RequestSession:
    """
    增强型 HTTP 会话，集成全部反爬策略。

    特性:
      - UA 轮换（20 个真实浏览器）
      - 按域名限速（令牌桶）
      - 代理支持（轮换代理列表）
      - 指数退避重试（403/429/5xx）
      - Cookie 自动管理 + 会话保持
      - 请求统计（成功/失败/重试/限流次数）
    """

    def __init__(
        self,
        domain: str = "default",
        rpm: int = 12,
        min_delay: float = 3.0,
        max_delay: float = 8.0,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
        timeout: float = 30.0,
        proxies: List[str] = None,
        proxy_enabled: bool = False,
        referer: str = "",
        extra_headers: Dict[str, str] = None,
    ):
        self.domain = domain
        self.rpm = rpm
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.timeout = timeout
        self.proxies = proxies or []
        self.proxy_enabled = proxy_enabled and bool(self.proxies)
        self.referer = referer
        self.extra_headers = extra_headers or {}

        self._bucket = get_domain_bucket(self.domain, rpm)

        self.stats = {
            "total_requests": 0,
            "success": 0,
            "retries": 0,
            "failures": 0,
            "429_count": 0,
            "403_count": 0,
        }

        self._client: Optional[httpx.Client] = None
        self._ua_index = 0
        self._cookie_jar = None  # 跨客户端保持 Cookie

        self.logger = logging.getLogger(f"req.{self.domain}")

    # ── 客户端管理 ──

    def _build_client(self) -> httpx.Client:
        """构建带完整反爬头的 httpx 客户端。"""
        headers = {
            "User-Agent": self._next_ua(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Sec-Ch-Ua": '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        }
        if self.referer:
            headers["Referer"] = self.referer
        headers.update(self.extra_headers)

        kwargs: dict = {
            "timeout": httpx.Timeout(self.timeout),
            "follow_redirects": True,
            "headers": headers,
        }

        # http2 可选
        try:
            import h2  # noqa: F401
            kwargs["http2"] = True
        except ImportError:
            pass

        # Cookie 保持
        if self._cookie_jar is not None:
            kwargs["cookies"] = self._cookie_jar

        # 代理
        if self.proxy_enabled and self.proxies:
            proxy_url = random.choice(self.proxies)
            kwargs["proxy"] = proxy_url
            self.logger.debug(f"代理: {proxy_url[:60]}")

        return httpx.Client(**kwargs)

    def _next_ua(self) -> str:
        ua = USER_AGENT_POOL[self._ua_index % len(USER_AGENT_POOL)]
        self._ua_index += 1
        return ua

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = self._build_client()
        return self._client

    def refresh_client(self):
        """强制刷新客户端（轮换 UA + 代理，但保留 Cookie）。"""
        if self._client:
            try:
                # 保存 Cookie
                self._cookie_jar = dict(self._client.cookies)
                self._client.close()
            except Exception:
                pass
        self._client = self._build_client()

    def close(self):
        if self._client:
            try:
                self._cookie_jar = dict(self._client.cookies)
            except Exception:
                pass
            self._client.close()
            self._client = None

    # ── 核心请求方法 ──

    def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """
        带完整反爬策略的 HTTP 请求。

        流程:
          1. 域名限速检查（令牌桶）
          2. 随机延迟（重试时）
          3. 发送请求
          4. 403 → 长等待 + 刷新会话
          5. 429 → 指数退避 + 清空令牌桶
          6. 5xx → 指数退避
        """
        self.stats["total_requests"] += 1
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                # 限速
                self._bucket.acquire()

                # 重试时随机延迟
                if attempt > 0:
                    random_delay(self.min_delay, self.max_delay)

                # 每 10 次请求刷新 UA
                if self.stats["total_requests"] % 10 == 0:
                    self.refresh_client()

                self.logger.debug(
                    f"[{attempt+1}/{self.max_retries+1}] {method} {url[:120]}"
                )

                resp = self.client.request(method, url, **kwargs)

                if resp.status_code == 200:
                    self.stats["success"] += 1
                    return resp

                if resp.status_code == 403:
                    self.stats["403_count"] += 1
                    self.logger.warning(
                        f"⚠️ 403 禁止访问 (attempt {attempt+1}): {url[:100]}"
                    )
                    if attempt < self.max_retries:
                        wait = 60 * (self.backoff_factor ** attempt)
                        self.logger.info(f"   等待 {wait:.0f}s 后刷新会话...")
                        time.sleep(wait)
                        self.refresh_client()
                        continue

                elif resp.status_code == 429:
                    self.stats["429_count"] += 1
                    wait = 30 * (self.backoff_factor ** attempt)
                    self.logger.warning(f"⚠️ 429 限流，等待 {wait:.0f}s...")
                    time.sleep(wait)
                    self._bucket.tokens = 0.0
                    continue

                elif resp.status_code >= 500:
                    self.logger.warning(
                        f"⚠️ HTTP {resp.status_code} (attempt {attempt+1})"
                    )
                    if attempt < self.max_retries:
                        wait = 10 * (self.backoff_factor ** attempt)
                        time.sleep(wait)
                        continue

                else:
                    self.logger.warning(
                        f"⚠️ HTTP {resp.status_code}: {url[:100]}"
                    )
                    if attempt < self.max_retries:
                        time.sleep(5 * (self.backoff_factor ** attempt))
                        continue

            except (httpx.TimeoutException, httpx.ConnectError,
                    httpx.RemoteProtocolError, httpx.NetworkError) as e:
                last_error = e
                self.logger.warning(
                    f"⚠️ 网络错误 [{attempt+1}]: {type(e).__name__}"
                )
                if attempt < self.max_retries:
                    wait = 10 * (self.backoff_factor ** attempt)
                    time.sleep(wait)
                    self.refresh_client()
            except Exception as e:
                last_error = e
                self.logger.error(f"请求异常 [{attempt+1}]: {e}")
                if attempt < self.max_retries:
                    time.sleep(10 * (self.backoff_factor ** attempt))

        self.stats["failures"] += 1
        raise last_error or RuntimeError(
            f"请求失败 ({self.max_retries+1} attempts): {url}"
        )

    def get(self, url: str, params: dict = None, **kwargs) -> httpx.Response:
        return self.request("GET", url, params=params, **kwargs)

    def post(self, url: str, data: dict = None, json: dict = None, **kwargs) -> httpx.Response:
        return self.request("POST", url, data=data, json=json, **kwargs)

    def get_text(self, url: str, params: dict = None, **kwargs) -> str:
        resp = self.get(url, params=params, **kwargs)
        return resp.text

    def get_stats(self) -> dict:
        return dict(self.stats)

    def reset_stats(self):
        for k in self.stats:
            self.stats[k] = 0


# ============================================================
# 便捷工厂
# ============================================================

def create_session(domain: str, config: dict = None) -> RequestSession:
    """
    根据配置字典创建 RequestSession。

    config 键:
        request_interval: {min, max}
        retry: {max_attempts, backoff_factor}
        rpm: int
        proxy_enabled: bool
        proxy_list: [str]
        referer: str
    """
    cfg = config or {}
    interval = cfg.get("request_interval", {})
    retry_cfg = cfg.get("retry", {})

    return RequestSession(
        domain=domain,
        rpm=cfg.get("rpm", 12),
        min_delay=float(interval.get("min", 3.0)),
        max_delay=float(interval.get("max", 8.0)),
        max_retries=int(retry_cfg.get("max_attempts", 3)),
        backoff_factor=float(retry_cfg.get("backoff_factor", 2.0)),
        timeout=float(cfg.get("timeout", 30)),
        proxies=cfg.get("proxy_list", []),
        proxy_enabled=cfg.get("proxy_enabled", False),
        referer=cfg.get("referer", ""),
    )
