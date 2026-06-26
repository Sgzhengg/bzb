"""
历史中标采集 — 配置模块
"""

# ============================================================
# URL 配置
# ============================================================

BASE_URL = "https://b2b.10086.cn"

# 中标公告列表页
AWARD_LIST_URL = f"{BASE_URL}/b2b/main/listVendorNotice.html"

# 中标公告搜索 API
AWARD_SEARCH_URL = f"{BASE_URL}/b2b/main/searchNotice.html"

# 采集的关键词组合（适配不同年份的公告标题风格）
SEARCH_KEYWORD_COMBOS = [
    ("广东移动", "中标"),
    ("广东移动", "广告", "中标"),
    ("广东移动", "品牌", "中选"),
    ("广东移动", "宣传", "成交"),
    ("广东移动", "活动", "中选"),
    ("中国移动广东", "广告", "中标"),
    ("中国移动广东", "品牌", "结果"),
    ("中国移动广东", "营销", "中选"),
    ("广东移动", "新媒体", "中选"),
    ("广东移动", "设计", "中选"),
    ("广东移动", "制作", "中选"),
    ("广东移动", "投放", "中标"),
]

# 每页公告数
PAGE_SIZE = 20

# 最大翻页数（每种关键词组合）
MAX_PAGES_PER_SEARCH = 10

# ============================================================
# 采集范围
# ============================================================

START_DATE = "2023-01-01"  # 开始日期
# END_DATE 为 None 表示至今
END_DATE = None

# ============================================================
# 请求控制
# ============================================================

# 请求间隔范围（秒）
MIN_DELAY = 3.0
MAX_DELAY = 5.0

# User-Agent 池（从主爬虫复用）
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) "
    "Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

# ============================================================
# 请求头
# ============================================================

BASE_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Cache-Control": "max-age=0",
}

# ============================================================
# 断点续传
# ============================================================

CHECKPOINT_DIR = "output"
CHECKPOINT_FILE = "historical_checkpoint.json"
PARTIAL_DIR = "output/partial"

# ============================================================
# 输出配置
# ============================================================

OUTPUT_DIR = "output"
OUTPUT_FILENAME = "historical_awards.json"

# ============================================================
# 重试配置
# ============================================================

MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 15
REQUEST_TIMEOUT = 30
