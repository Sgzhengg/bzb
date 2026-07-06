"""
标中宝 V2.1 — 广东移动广告类招标项目关键词过滤与赛道识别模块

新增:
  - config/keywords.txt DSL 配置文件加载（可选）
  - validate_source_url() 域名白名单校验
  - calculate_bidding_score() 权重评分
"""

import os
from typing import List, Dict, Set
from datetime import datetime, date
from urllib.parse import urlparse

_all = dir()  # noqa - placeholder


# ============================================================
# 一、采购单位词
# ============================================================

PURCHASER_KEYWORDS: List[str] = [
    "中国移动", "广东移动", "中国移动通信集团广东",
    "中国移动通信集团广东有限公司", "中国移动广东",
    "中移铁通", "中移互联网", "咪咕",
]

# ============================================================
# 二、广东省内地名（地域限定）
# ============================================================

GD_CITIES: List[str] = [
    "广东", "广州", "深圳", "东莞", "佛山", "惠州", "珠海",
    "中山", "江门", "茂名", "揭阳", "汕头", "湛江", "肇庆",
    "梅州", "汕尾", "河源", "阳江", "清远", "韶关", "潮州",
    "云浮", "南海", "顺德", "番禺",
]

# ============================================================
# 三、广东移动广告类项目核心关键词（安全词，一条不漏）
# ============================================================

# 3.1 广告设计/全案类
AD_DESIGN_KW: List[str] = [
    "广告", "广告设计", "广告创意", "广告策划", "广告全案",
    "广告全案策划", "广告整合推广", "广告代理",
    "平面设计", "视觉设计", "创意设计", "VI设计", "VI标识",
    "品牌VI", "视觉识别系统", "形象设计", "品牌设计",
    "全案策划", "广告策划设计", "广告设计制作", "广告创意设计",
    "品牌形象设计", "品牌视觉", "视觉创意",
]

# 3.2 广告物料/制作类
AD_MATERIAL_KW: List[str] = [
    "广告物料", "广告物料制作", "广告制作", "宣传物料",
    "宣传物料制作", "物料制作", "物料采购",
    "喷绘制作", "写真制作", "标识标牌", "门头招牌",
    "灯箱广告", "发光字", "户外广告牌",
    "营业厅门头", "营业厅背景墙", "VI标识制作",
    "广告宣传品", "印刷品", "宣传品印制", "广告宣传物料",
    "营销物料", "促销物料", "终端物料", "陈列展示",
    "展架", "易拉宝", "横幅", "宣传单页", "宣传册", "画册",
    "海报", "展板",
]

# 3.3 活动策划/执行类
AD_EVENT_KW: List[str] = [
    "活动策划", "活动执行", "活动服务", "营销活动",
    "市场活动", "推广活动", "品牌活动", "客户活动",
    "客户服务活动", "客户关怀", "关怀活动",
    "集团客户活动", "政企客户活动", "校园营销", "校园活动",
    "社区活动", "发布会", "推介会", "展会", "展览展示",
    "会议会展", "路演", "快闪", "运动会", "文体活动",
    "工会活动", "党建活动", "文化宣传活动", "促销活动",
    "庆典活动", "年会", "启动仪式",
    # 新增
    "会议营销", "培训", "参观学习", "考察交流",
    "业务培训", "技能培训", "学习交流", "参观考察",
]

# 3.4 品牌/宣传/传播类
AD_BRAND_KW: List[str] = [
    "品牌宣传", "品牌推广", "品牌传播", "企业文化宣传",
    "党建宣传", "新闻宣传", "宣传推广", "宣传服务", "宣传支撑",
    "品牌建设", "品牌形象", "品牌策划",
    "整合营销", "社会化营销", "新媒体传播", "公关传播",
    "媒体宣传", "广告投放", "媒介投放",
    # 新增
    "咨询", "品牌咨询", "营销咨询", "管理咨询",
    "策划咨询", "设计咨询", "战略咨询",
]

# 3.5 视频/新媒体类
AD_VIDEO_KW: List[str] = [
    "视频制作", "宣传片拍摄", "宣传片制作", "短视频制作",
    "视频拍摄", "视频剪辑", "品牌视频", "形象宣传片",
    "产品视频", "动画制作", "微电影", "直播",
    "新媒体运营", "公众号运营", "抖音运营", "视频号运营",
    "新媒体策划", "新媒体内容制作", "新媒体代运营",
    "内容运营", "H5制作", "线上活动", "直播运营",
    "自媒体运营", "社交媒体运营",
]

# 3.6 媒介/资源类
AD_MEDIA_KW: List[str] = [
    "户外媒介", "户外广告", "社区广告", "社区道闸",
    "社区电梯广告", "公交车身广告", "公交候车亭广告",
    "地铁广告", "地铁灯箱", "高铁站广告", "火车站广告",
    "机场广告", "LED大屏", "户外大牌",
    "电梯框架广告", "电梯视频广告", "出租车广告",
    "网络广告", "互联网广告", "信息流广告", "KOL投放",
    "达人合作",
]

# 3.7 渠道/营销/运营类
AD_CHANNEL_KW: List[str] = [
    "渠道营销", "网格营销", "地推", "促销布展",
    "门店推广", "厅店推广", "营业厅推广", "商圈推广",
    "社区推广", "校园推广", "政企推广",
    "客户拓展", "市场拓展", "营销支撑", "运营支撑",
    "线上渠道", "线下渠道", "电子渠道", "实体渠道",
    "社会渠道", "O2O",
    "集团客户", "政企客户", "VIP客户", "高价值客户",
    "个人客户", "校园客户", "社区客户", "存量客户",
]

# 3.8 采购方式/规模词（辅助判断，非独立判定词）
PROCUREMENT_KW: List[str] = [
    "集中采购", "框架采购", "公开招标", "公开询比",
    "询比采购", "竞争性谈判", "单一来源", "邀请招标",
    "零星采购", "二级集采", "三级集采",
]

# ── 合并所有安全词（一条不漏）──
SAFETY_KEYWORDS: List[str] = list(dict.fromkeys(
    AD_DESIGN_KW + AD_MATERIAL_KW + AD_EVENT_KW +
    AD_BRAND_KW + AD_VIDEO_KW + AD_MEDIA_KW + AD_CHANNEL_KW
))

# 保留别名以兼容旧代码
KEEP_KEYWORDS = SAFETY_KEYWORDS


# ============================================================
# 四、硬排除词（仅在无安全词命中时生效）
# ============================================================

HARD_EXCLUDE_KEYWORDS: List[str] = [
    "基站建设", "光缆铺设", "软件开发", "系统编码",
    "服务器采购", "物业管理", "食堂承包", "保安服务", "保洁服务",
    # 广东移动常见但非广告的项目类型
    "DCN", "铁塔", "监理服务", "施工图审查", "数据中心",
    "网络技术支撑", "API接口", "DevOps", "数智化",
    "业务支撑系统", "定制软件", "通信铁塔",
    "食材", "福利品", "基建工程", "视频监控", "话务平台",
    "视频报警", "强弱电", "线路整治", "防护工具",
    "慧眼", "维护支撑", "传输管线", "机房", "电源", "空调",
    "消防", "防雷", "发电", "蓄电池", "综合布线",
    "前端服务优化", "智能体", "招租", "租赁",
]

EXCLUDE_KEYWORDS = HARD_EXCLUDE_KEYWORDS


# ============================================================
# 五、赛道分类规则（8个精细赛道，按优先级排序）
# ============================================================

CATEGORY_RULES: List[Dict[str, Any]] = [
    {
        "category": "广告创意设计",
        "keywords": [
            "广告设计", "广告创意", "平面设计", "视觉设计",
            "创意设计", "VI设计", "VI标识", "品牌VI",
            "视觉识别系统", "形象设计", "品牌设计",
            "广告全案", "全案策划", "广告策划", "广告整合推广",
        ],
    },
    {
        "category": "物料制作印刷",
        "keywords": [
            "广告物料", "广告物料制作", "宣传物料", "宣传物料制作",
            "物料制作", "喷绘制作", "写真制作", "标识标牌",
            "门头招牌", "灯箱", "发光字", "户外广告牌",
            "广告宣传品", "印刷品", "宣传品印制",
            "展架", "易拉宝", "横幅", "宣传单页",
            "宣传册", "画册", "海报", "展板",
        ],
    },
    {
        "category": "活动策划执行",
        "keywords": [
            "活动策划", "活动执行", "营销活动", "市场活动",
            "推广活动", "品牌活动", "客户活动", "客户服务活动",
            "客户关怀", "集团客户活动", "政企客户活动",
            "校园营销", "发布会", "推介会", "展会", "展览展示",
            "会议会展", "路演", "快闪", "运动会", "文体活动",
            "工会活动", "党建活动", "促销活动", "年会", "启动仪式",
            "会议营销", "培训", "参观学习", "考察交流",
            "业务培训", "技能培训", "学习交流", "参观考察",
            "交流学习", "信息化参观", "客户信息化参观",
            "智慧展示", "智慧展示体验", "展示体验", "体验参观",
        ],
    },
    {
        "category": "品牌宣传传播",
        "keywords": [
            "品牌宣传", "品牌推广", "品牌传播", "企业文化宣传",
            "党建宣传", "新闻宣传", "宣传推广", "宣传服务",
            "品牌建设", "品牌形象", "品牌策划",
            "整合营销", "社会化营销", "新媒体传播", "公关传播",
            "媒体宣传", "广告投放", "媒介投放",
            "业务宣传", "企业文化", "企业文化建设",
            "咨询", "品牌咨询", "营销咨询", "管理咨询",
            "策划咨询", "设计咨询", "战略咨询",
        ],
    },
    {
        "category": "视频内容制作",
        "keywords": [
            "视频制作", "宣传片拍摄", "宣传片制作", "短视频制作",
            "视频拍摄", "视频剪辑", "品牌视频", "形象宣传片",
            "产品视频", "动画制作", "微电影", "直播",
        ],
    },
    {
        "category": "新媒体运营",
        "keywords": [
            "新媒体运营", "公众号运营", "抖音运营", "视频号运营",
            "新媒体策划", "新媒体内容制作", "新媒体代运营",
            "内容运营", "H5制作", "直播运营",
        ],
    },
    {
        "category": "媒介资源投放",
        "keywords": [
            "户外媒介", "户外广告", "社区广告", "社区道闸",
            "社区电梯广告", "公交车身广告", "公交候车亭广告",
            "地铁广告", "地铁灯箱", "LED大屏", "户外大牌",
            "电梯框架广告", "电梯视频广告", "出租车广告",
            "网络广告", "互联网广告", "信息流广告", "KOL投放",
        ],
    },
    {
        "category": "渠道营销推广",
        "keywords": [
            "渠道营销", "网格营销", "地推", "促销布展",
            "门店推广", "厅店推广", "营业厅推广", "商圈推广",
            "社区推广", "校园推广", "政企推广",
            "客户拓展", "市场拓展", "营销支撑", "运营支撑",
        ],
    },
]

DEFAULT_CATEGORY = "其他营销类"


# ============================================================
# 核心函数
# ============================================================

def _match_keywords(text: str, keywords: List[str]) -> List[str]:
    """在文本中匹配关键词，返回命中的关键词列表（去重，保持顺序）。"""
    if not text:
        return []
    text_lower = text.lower()
    matched = []
    seen = set()
    for kw in keywords:
        if kw.lower() in text_lower and kw not in seen:
            matched.append(kw)
            seen.add(kw)
    return matched


def _is_gd_mobile_purchaser(title: str) -> bool:
    """判断标题是否包含广东移动采购单位+广东省内地名。"""
    has_purchaser = any(kw in title for kw in PURCHASER_KEYWORDS)
    if not has_purchaser:
        return False
    return any(city in title for city in GD_CITIES)


def _identify_category(title: str, content: str = "") -> str:
    """按 CATEGORY_RULES 顺序匹配，首个命中即返回对应赛道。"""
    combined = f"{title} {content}"
    for rule in CATEGORY_RULES:
        if _match_keywords(combined, rule["keywords"]):
            return rule["category"]
    return DEFAULT_CATEGORY


# ── 广告暗示短词（用于采购单位+地域匹配时的辅助判断）──
_SHORT_AD_HINTS: List[str] = [
    "广告", "宣传", "活动", "品牌", "营销", "推广",
    "设计", "制作", "物料", "新媒体", "视频", "直播",
    "策划", "创意", "传播", "运营", "渠道", "媒介",
    "印刷", "喷绘", "展会", "展架", "海报", "画册",
    "地推", "促销", "路演", "发布会", "客户服务",
    "拍摄", "投放", "代理", "门店", "网格",
    "企业文化", "业务宣传", "党建", "工会", "参观",
    "交流学习", "智慧展示", "信息化参观",
]


def filter_advertisement_projects(
    title: str,
    content: str = "",
) -> Dict[str, Any]:
    """
    判断一个招标项目是否属于广东移动广告类，并识别赛道。

    分层判定:
      第1层 - 安全词优先:
        标题命中 SAFETY_KEYWORDS 中任意词 → 直接判定广告类，不执行排除。
      第2层 - 采购单位+地域+广告暗示:
        标题含采购单位词 + 广东省内城市名 + 广告暗示短词 → 广告类。
      第3层 - 硬排除（最低优先级）:
        仅当标题完全不包含安全词时，才检查排除词。

    Args:
        title: 项目名称/标题
        content: 项目描述/正文（可选）

    Returns:
        {is_ad, matched_keywords, category, reason}
    """
    combined_text = f"{title} {content}"

    # ── 第1层：安全词优先 ──
    safety_matched = _match_keywords(combined_text, SAFETY_KEYWORDS)
    if safety_matched and _is_gd_mobile_purchaser(title):
        return {
            "is_ad": True,
            "matched_keywords": safety_matched,
            "category": _identify_category(title, content),
            "reason": "",
        }

    # ── 第2层：采购单位 + 地域 + 广告暗示 ──
    if _is_gd_mobile_purchaser(title):
        hints = _match_keywords(combined_text, _SHORT_AD_HINTS)
        if hints:
            return {
                "is_ad": True,
                "matched_keywords": hints,
                "category": _identify_category(title, content),
                "reason": "采购单位+地域+广告暗示",
            }

    # ── 第3层：硬排除（仅在无安全词时生效）──
    excluded = _match_keywords(combined_text, HARD_EXCLUDE_KEYWORDS)
    if excluded:
        return {
            "is_ad": False,
            "matched_keywords": [],
            "category": "",
            "reason": f"命中排除关键词: {', '.join(excluded)}",
        }

    return {
        "is_ad": False,
        "matched_keywords": [],
        "category": "",
        "reason": "未命中广告类关键词且非广东移动采购主体",
    }


# ============================================================
# 用户偏好加权
# ============================================================

def apply_preference_boost(
    item: Dict,
    preferred_categories: List[str] = None,
    min_budget: float = 0,
    min_score: float = 0,
) -> Dict:
    """根据用户偏好对项目进行加权。"""
    boost = {
        "is_preferred": False,
        "category_match": False,
        "budget_meets": True,
        "score_meets": True,
        "boost_score": 0,
    }

    budget = float(item.get("budget", 0) or 0)
    if min_budget > 0 and budget < min_budget:
        boost["budget_meets"] = False

    score = float(item.get("total_score", 0) or 0)
    if min_score > 0 and score < min_score:
        boost["score_meets"] = False

    category = item.get("project_category", "") or item.get("category", "")
    if preferred_categories and category and category in preferred_categories:
        boost["category_match"] = True
        boost["boost_score"] = 5

    boost["is_preferred"] = boost["category_match"] or boost["budget_meets"]

    result = dict(item)
    result["preference"] = boost
    return result


def batch_apply_preferences(
    items: List[Dict],
    preferred_categories: List[str] = None,
    min_budget: float = 0,
    min_score: float = 0,
    sort_by_preference: bool = True,
) -> List[Dict]:
    """批量应用用户偏好并排序。"""
    result = [
        apply_preference_boost(item, preferred_categories, min_budget, min_score)
        for item in items
    ]
    if sort_by_preference:
        result.sort(
            key=lambda x: (
                0 if x["preference"]["category_match"] else 1,
                -(x.get("total_score", 0) or 0),
                -(x.get("budget", 0) or 0),
            )
        )
    return result


def batch_filter(
    projects: List[Dict[str, str]],
    title_key: str = "title",
    content_key: str = "content",
) -> List[Dict[str, Any]]:
    """批量过滤招标项目列表。"""
    return [
        {
            **project,
            **filter_advertisement_projects(
                title=project.get(title_key, ""),
                content=project.get(content_key, ""),
            ),
        }
        for project in projects
    ]


# ============================================================
# V2.1 新增: 域名校验 + 权重计算 + 配置文件加载
# ============================================================

URL_DOMAIN_WHITELIST: Set[str] = {
    "b2b.10086.cn",
    "zb.zhaobiao.cn",
    "www.zhaobiao.cn",
    "s.zhaobiao.cn",
    "zbtb.gd.gov.cn",
    "ygp.gdzwfw.gov.cn",
}

WEIGHT_CONFIG = {
    "CATEGORY_WEIGHT": 0.40,
    "BUDGET_WEIGHT": 0.30,
    "FRESHNESS_WEIGHT": 0.20,
    "LEVEL_WEIGHT": 0.10,
}

LEVEL_SCORE_MAP = {
    "省公司": 100, "广州分公司": 90, "深圳分公司": 90,
    "东莞分公司": 80, "佛山分公司": 80, "珠海分公司": 75,
    "惠州分公司": 75, "中山分公司": 70, "江门分公司": 70,
}


def validate_source_url(url: str) -> bool:
    """校验 URL 是否安全（HTTPS + 域名白名单）。"""
    if not url:
        return True
    try:
        parsed = urlparse(url)
        if parsed.scheme != "https":
            return False
        hostname = (parsed.hostname or "").lower()
        if not hostname:
            return True
        for domain in URL_DOMAIN_WHITELIST:
            if hostname == domain or hostname.endswith("." + domain):
                return True
        return False
    except Exception:
        return False


def calculate_bidding_score(
    title: str = "",
    budget: float = 0,
    publish_date: date = None,
    purchaser_level: str = "",
    preferred_categories: List[str] = None,
) -> float:
    """
    计算招标项目综合评分 0-100。

    维度: 赛道匹配(40%) + 预算规模(30%) + 时效性(20%) + 级别(10%)
    """
    cat = _identify_category(title)
    if preferred_categories and cat in preferred_categories:
        cat_score = 40
    else:
        cat_score = 20
    score = cat_score * WEIGHT_CONFIG["CATEGORY_WEIGHT"]

    budget = float(budget or 0)
    budget_score = max(0, min(100, (budget / 500) * 100)) if budget > 0 else 10
    score += budget_score * WEIGHT_CONFIG["BUDGET_WEIGHT"]

    if publish_date:
        days = max(0, (date.today() - publish_date).days)
        freshness = 100 if days <= 7 else max(0, 100 - (days - 7) * (100 / 23)) if days <= 30 else 0
    else:
        freshness = 50
    score += freshness * WEIGHT_CONFIG["FRESHNESS_WEIGHT"]

    level_score = LEVEL_SCORE_MAP.get(purchaser_level, 50)
    score += level_score * WEIGHT_CONFIG["LEVEL_WEIGHT"]

    return round(min(score, 100), 1)


# ── 配置文件加载（可选）──
def _try_load_config_overrides():
    """尝试从 config/keywords.txt 加载关键词覆盖（失败则保持默认）。"""
    candidates = [
        os.path.join(os.path.dirname(__file__), "..", "..", "config", "keywords.txt"),
        os.path.join(os.path.dirname(__file__), "config", "keywords.txt"),
        "config/keywords.txt",
    ]
    for p in candidates:
        path = os.path.normpath(os.path.abspath(p))
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    sections = {}
                    current = None
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if line.startswith("[") and line.endswith("]"):
                            current = line[1:-1].upper()
                            sections.setdefault(current, [])
                            continue
                        clean = line
                        for px in ("@", "!", "+"):
                            if clean.startswith(px):
                                clean = clean[1:].strip()
                                break
                        if "=>" in clean:
                            clean = clean.split("=>")[0].strip()
                        if clean and current:
                            sections[current].append(clean)
                return sections
            except Exception:
                pass
    return None


_config_overrides = _try_load_config_overrides()
if _config_overrides:
    for section, keywords in _config_overrides.items():
        if section == "GLOBAL_FILTER":
            HARD_EXCLUDE_KEYWORDS[:] = keywords
        elif section == "PURCHASER":
            PURCHASER_KEYWORDS[:] = keywords
        elif section == "GD_CITIES":
            GD_CITIES[:] = keywords
        elif section in {r["category"] for r in CATEGORY_RULES}:
            for rule in CATEGORY_RULES:
                if rule["category"] == section:
                    rule["keywords"] = keywords
        elif section == "SHORT_HINTS":
            _SHORT_AD_HINTS[:] = keywords


# ============================================================
# 单元测试
# ============================================================

if __name__ == "__main__":
    passed = 0
    failed = 0

    def check(actual, expected, name):
        global passed, failed
        if actual == expected:
            passed += 1
            print(f"  ✅ {name}")
        else:
            failed += 1
            print(f"  ❌ {name}")
            print(f"     期望: {expected}")
            print(f"     实际: {actual}")

    print("=== keyword_filter V2 单元测试 ===\n")

    # 安全词测试
    r = filter_advertisement_projects(
        "中国移动通信集团广东有限公司广州分公司2026年广告全案策划服务项目"
    )
    check(r["is_ad"], True, "安全词: 广告全案策划")
    check(r["category"], "广告创意设计", "赛道: 广告创意设计")

    r = filter_advertisement_projects(
        "广东移动东莞分公司2026年宣传物料制作采购项目"
    )
    check(r["is_ad"], True, "安全词: 宣传物料制作")
    check(r["category"], "物料制作印刷", "赛道: 物料制作印刷")

    r = filter_advertisement_projects(
        "中国移动广东深圳分公司2026年客户服务活动执行项目"
    )
    check(r["is_ad"], True, "安全词: 客户服务活动")
    check(r["category"], "活动策划执行", "赛道: 活动策划执行")

    # 基站广告牌：安全词覆盖排除词
    r = filter_advertisement_projects(
        "广东移动广州分公司2026年基站广告牌制作安装项目"
    )
    check(r["is_ad"], True, "安全词优先: 广告牌 > 基站建设")

    # 纯工程：无安全词，排除生效
    r = filter_advertisement_projects(
        "中国移动通信集团广东有限公司2026年基站建设项目"
    )
    check(r["is_ad"], False, "硬排除: 基站建设（无安全词）")

    r = filter_advertisement_projects(
        "广东移动物业管理服务采购项目"
    )
    check(r["is_ad"], False, "硬排除: 物业管理")

    # 采购单位+地域匹配
    r = filter_advertisement_projects(
        "中国移动广东广州分公司2026年度品牌咨询项目"
    )
    check(r["is_ad"], True, "采购单位+地域+品牌暗示")

    # 视频制作
    r = filter_advertisement_projects(
        "中国移动通信集团广东有限公司2026年宣传片拍摄制作项目"
    )
    check(r["is_ad"], True, "安全词: 宣传片拍摄")
    check(r["category"], "视频内容制作", "赛道: 视频内容制作")

    # 新媒体
    r = filter_advertisement_projects(
        "广东移动佛山分公司2026年公众号运营服务采购"
    )
    check(r["is_ad"], True, "安全词: 公众号运营")
    check(r["category"], "新媒体运营", "赛道: 新媒体运营")

    # 媒介投放
    r = filter_advertisement_projects(
        "中国移动广东公司2026年公交车身广告投放项目"
    )
    check(r["is_ad"], True, "安全词: 公交车身广告")
    check(r["category"], "媒介资源投放", "赛道: 媒介资源投放")

    # 渠道营销
    r = filter_advertisement_projects(
        "广东移动深圳分公司2026年网格营销支撑服务项目"
    )
    check(r["is_ad"], True, "安全词: 网格营销")
    check(r["category"], "渠道营销推广", "赛道: 渠道营销推广")

    # 非广东移动
    r = filter_advertisement_projects("北京移动2026年广告投放项目")
    check(r["is_ad"], False, "非广东移动: 北京不在广东省内")

    # 非广告IT
    r = filter_advertisement_projects(
        "中国移动通信集团广东有限公司2026年服务器采购项目"
    )
    check(r["is_ad"], False, "硬排除: 服务器采购")

    # 灯箱广告
    r = filter_advertisement_projects("广东移动深圳2026年灯箱广告制作项目")
    check(r["is_ad"], True, "安全词: 灯箱广告")
    check(r["category"], "物料制作印刷", "赛道: 灯箱→物料制作印刷")

    # 党建活动（广东移动）
    r = filter_advertisement_projects("广东移动2026年党建活动服务项目")
    check(r["is_ad"], True, "安全词: 党建活动")
    check(r["category"], "活动策划执行", "赛道: 党建→活动策划执行")

    # ── V2.1 新增测试 ──
    print("\n--- V2.1 域名校验 ---")
    check(validate_source_url("https://b2b.10086.cn/page"), True, "白名单: b2b.10086.cn")
    check(validate_source_url("https://zb.zhaobiao.cn/page"), True, "白名单: zb.zhaobiao.cn")
    check(validate_source_url("http://evil.com"), False, "非HTTPS: evil.com")
    check(validate_source_url("https://evil.com"), False, "非白名单: evil.com")
    check(validate_source_url(""), True, "空URL放行")

    print("\n--- V2.1 权重计算 ---")
    s = calculate_bidding_score("广东移动品牌宣传项目", budget=300, purchaser_level="省公司")
    check(isinstance(s, (int, float)), True, "权重返回数值")
    check(s > 0, True, "权重 > 0")

    print(f"\n{'='*40}")
    print(f"通过: {passed}, 失败: {failed}, 总计: {passed + failed}")
