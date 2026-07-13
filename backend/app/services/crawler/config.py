"""
爬虫配置模块
"""

# ============================================================
# 目标 URL 配置
# ============================================================

# 中国移动采购与招标网 — 公告列表页
BASE_URL = "https://b2b.10086.cn"

# 列表页 URL（广东地区招标公告 — 保留作为默认值）
LIST_URL = (
    f"{BASE_URL}/b2b/main/listVendorNotice.html"
    "?noticeType=2&region=广东"
)

# 备选：直接搜索的 API 接口
SEARCH_API_URL = f"{BASE_URL}/b2b/main/searchNotice.html"

# 搜索关键词（保留作为默认值，实际使用时从 provinces 配置动态生成）
SEARCH_KEYWORDS = ["广东移动", "广告", "品牌", "宣传", "营销", "活动"]

# ============================================================
# 多省份搜索关键词生成（V2 扩展）
# ============================================================

def get_search_keywords_for_province(province_name: str, include_ad_topics: bool = True) -> list:
    """
    根据省份名生成搜索关键词组合。
    b2b API 不支持空格复合词，直接用 "{省份}移动" 搜索，
    后续由 pipeline 的关键词过滤器筛选广告类。
    """
    return [f"{province_name}移动"]


def get_default_province_list_url(province_name: str) -> str:
    """
    根据省份名生成 b2b.10086.cn 的地区筛选列表页 URL。

    Args:
        province_name: 省份名（如 "广东"）

    Returns:
        带 region 参数的完整 URL
    """
    return f"{BASE_URL}/b2b/main/listVendorNotice.html?noticeType=2&region={province_name}"

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
# AI 增强爬虫配置
# ============================================================

# 是否默认启用 AI 模式（处理 JS 渲染页面）
AI_CRAWLER_ENABLED = True

# AI 爬虫超时（秒），比 HTTP 模式更长因为需要渲染
AI_CRAWLER_TIMEOUT = 60

# AI 爬虫最大并发数
AI_CRAWLER_MAX_CONCURRENT = 3

# AI 爬虫内容最小词数阈值
AI_CRAWLER_WORD_THRESHOLD = 10

# 跳过 AI 缓存的 URL 模式（正则表达式，这些 URL 每次都重新渲染）
AI_CRAWLER_BYPASS_CACHE_PATTERNS = [
    r"detail",     # 详情页 URL 通常包含 detail
    r"notice",     # 公告页 URL 通常包含 notice
]

# ============================================================
# 输出配置
# ============================================================

OUTPUT_DIR = "output"
OUTPUT_FILENAME = "bidding_results.json"
