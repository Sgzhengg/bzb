"""
爬虫配置模块
"""

# ============================================================
# 目标 URL 配置
# ============================================================

# 中国移动采购与招标网 — 公告列表页
BASE_URL = "https://b2b.10086.cn"

# 列表页 URL（广东地区招标公告）
LIST_URL = (
    f"{BASE_URL}/b2b/main/listVendorNotice.html"
    "?noticeType=2&region=广东"
)

# 备选：直接搜索 "广东移动广告" 的 API 接口
SEARCH_API_URL = f"{BASE_URL}/b2b/main/searchNotice.html"

# 搜索关键词
SEARCH_KEYWORDS = ["广东移动", "广告", "品牌", "宣传", "营销", "活动"]

# ============================================================
# 请求配置
# ============================================================

# 请求最小间隔（秒），每分钟最多 1 次
MIN_REQUEST_INTERVAL = 60.0

# 请求超时（秒）
REQUEST_TIMEOUT = 30

# 最大重试次数
MAX_RETRIES = 3

# 重试等待基数（秒），指数退避：base * (2 ** attempt)
RETRY_BACKOFF_BASE = 10

# 每页公告数
PAGE_SIZE = 20

# 最大翻页数（防止无限翻页）
MAX_PAGES = 50

# ============================================================
# User-Agent 池
# ============================================================

USER_AGENTS = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    # Chrome on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) "
    "Gecko/20100101 Firefox/126.0",
    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
    # Safari on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.5 Safari/605.1.15",
]

# ============================================================
# 请求头模板
# ============================================================

BASE_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Cache-Control": "max-age=0",
}

# ============================================================
# 输出配置
# ============================================================

OUTPUT_DIR = "output"
OUTPUT_FILENAME = "bidding_results.json"
