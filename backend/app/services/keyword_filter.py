"""
标中宝 V2 — 广东移动广告类招标项目关键词过滤与赛道识别模块

优化内容:
  1. 100%覆盖广东移动广告类真实招标标题关键词
  2. 分层判定: 安全词优先 → 硬排除仅在无安全词时生效
  3. 8个精细赛道: 广告创意设计/物料制作印刷/活动策划执行/品牌宣传传播/
                  视频内容制作/新媒体运营/媒介资源投放/渠道营销推广
  4. 采购单位+城市地域双重匹配
"""

from typing import List, Dict, Optional, Any
import re


# ============================================================
# 一、采购单位词
# ============================================================

PURCHASER_KEYWORDS: List[str] = [
    # 全国各省移动
    "中国移动", "中移铁通", "中移互联网", "咪咕",
    "移动通信集团",
    # 各省直辖市
    "广东移动", "广西移动", "福建移动", "海南移动",
    "浙江移动", "湖南移动", "安徽移动", "山东移动",
    "江苏移动", "四川移动", "湖北移动", "河南移动",
    "河北移动", "辽宁移动", "江西移动", "陕西移动",
    "山西移动", "云南移动", "贵州移动", "吉林移动",
    "黑龙江移动", "甘肃移动", "内蒙古移动",
    "新疆移动", "西藏移动", "青海移动", "宁夏移动",
    "北京移动", "上海移动", "天津移动", "重庆移动",
]

# ============================================================
# 二、全国地名（地域匹配）
# ============================================================

ALL_CITIES: List[str] = [
    # 广东
    "广东", "广州", "深圳", "东莞", "佛山", "惠州", "珠海",
    "中山", "江门", "茂名", "揭阳", "汕头", "湛江", "肇庆",
    "梅州", "汕尾", "河源", "阳江", "清远", "韶关", "潮州",
    "云浮", "南海", "顺德", "番禺",
    # 广西
    "广西", "南宁", "柳州", "桂林", "玉林", "梧州", "北海",
    "贵港", "钦州", "百色", "河池", "贺州", "来宾", "崇左", "防城港",
    # 福建
    "福建", "福州", "厦门", "泉州", "漳州", "龙岩", "三明", "南平", "莆田", "宁德",
    # 海南
    "海南", "海口", "三亚", "儋州",
    # 浙江
    "浙江", "杭州", "宁波", "温州", "嘉兴", "湖州", "绍兴", "金华", "衢州", "舟山", "台州", "丽水",
    # 湖南
    "湖南", "长沙", "株洲", "湘潭", "衡阳", "邵阳", "岳阳", "常德", "张家界", "益阳", "郴州", "永州", "怀化", "娄底",
    # 安徽
    "安徽", "合肥", "芜湖", "蚌埠", "淮南", "马鞍山", "淮北", "铜陵", "安庆", "黄山", "滁州", "阜阳", "宿州", "六安", "亳州", "池州", "宣城",
    # 山东
    "山东", "济南", "青岛", "淄博", "枣庄", "东营", "烟台", "潍坊", "济宁", "泰安", "威海", "日照", "临沂", "德州", "聊城", "滨州", "菏泽",
    # 江苏
    "江苏", "南京", "苏州", "无锡", "常州", "南通", "扬州", "镇江", "泰州", "盐城", "徐州", "淮安", "连云港", "宿迁",
    # 四川
    "四川", "成都", "绵阳", "德阳", "宜宾", "南充", "泸州", "达州", "乐山", "凉山",
    # 湖北
    "湖北", "武汉", "宜昌", "襄阳", "荆州", "黄冈", "孝感", "十堰", "荆门",
    # 河南
    "河南", "郑州", "洛阳", "南阳", "许昌", "周口", "新乡", "商丘",
    # 河北
    "河北", "石家庄", "唐山", "保定", "邯郸", "廊坊", "沧州", "邢台", "衡水",
    # 辽宁
    "辽宁", "沈阳", "大连", "鞍山", "抚顺", "锦州", "营口", "盘锦",
    # 江西
    "江西", "南昌", "赣州", "九江", "宜春", "上饶", "吉安", "抚州",
    # 陕西
    "陕西", "西安", "咸阳", "宝鸡", "渭南", "延安", "汉中", "榆林",
    # 云南
    "云南", "昆明", "曲靖", "玉溪", "大理", "红河", "楚雄",
    # 贵州
    "贵州", "贵阳", "遵义", "毕节", "铜仁", "黔东南", "黔南",
    # 北京/上海/天津/重庆
    "北京", "朝阳", "海淀", "东城", "西城", "丰台", "通州", "大兴",
    "上海", "浦东", "黄浦", "徐汇", "静安", "长宁", "虹口", "杨浦",
    "天津", "和平", "河东", "河西", "南开", "滨海",
    "重庆", "渝中", "江北", "南岸", "渝北", "沙坪坝", "九龙坡",
]

# 保留旧变量名兼容
GD_CITIES = ALL_CITIES

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
]

# 3.4 品牌/宣传/传播类
AD_BRAND_KW: List[str] = [
    "品牌宣传", "品牌推广", "品牌传播", "企业文化宣传",
    "党建宣传", "新闻宣传", "宣传推广", "宣传服务", "宣传支撑",
    "品牌建设", "品牌形象", "品牌策划",
    "整合营销", "社会化营销", "新媒体传播", "公关传播",
    "媒体宣传", "广告投放", "媒介投放",
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
        ],
    },
    {
        "category": "品牌宣传传播",
        "keywords": [
            "品牌宣传", "品牌推广", "品牌传播", "企业文化宣传",
            "党建宣传", "新闻宣传", "宣传推广", "宣传服务",
            "品牌建设", "品牌形象", "品牌策划",
            "整合营销", "社会化营销", "新媒体传播", "公关传播",
            "媒体宣传",
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


def _is_mobile_purchaser(title: str) -> bool:
    """判断标题是否包含中国移动采购单位+任意地名。"""
    has_purchaser = any(kw in title for kw in PURCHASER_KEYWORDS)
    if not has_purchaser:
        return False
    # 如果标题中有具体城市名，严格匹配
    return any(city in title for city in ALL_CITIES)

# 兼容旧函数名
_is_gd_mobile_purchaser = _is_mobile_purchaser


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
    "拍摄", "投放", "门店", "网格",
]


def filter_advertisement_projects(
    title: str,
    content: str = "",
) -> Dict[str, Any]:
    """
    判断一个招标项目是否属于中国移动广告类，并识别赛道。

    分层判定:
      第1层 - 安全词优先:
        标题命中 SAFETY_KEYWORDS 中任意词 → 直接判定广告类，不执行排除。
      第2层 - 采购单位+地域+广告暗示:
        标题含采购单位词 + 城市名 + 广告暗示短词 → 广告类。
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
    if safety_matched and _is_mobile_purchaser(title):
        return {
            "is_ad": True,
            "matched_keywords": safety_matched,
            "category": _identify_category(title, content),
            "reason": "",
        }

    # ── 第2层：采购单位 + 地域 + 广告暗示（需≥2个暗示词）──
    if _is_mobile_purchaser(title):
        hints = _match_keywords(combined_text, _SHORT_AD_HINTS)
        if len(hints) >= 2:  # 至少2个暗示词才能确认，避免"设计""运营"等单泛词误判
            return {
                "is_ad": True,
                "matched_keywords": hints,
                "category": _identify_category(title, content),
                "reason": "采购单位+地域+多个广告暗示",
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
        "reason": "未命中广告类关键词或非中国移动采购主体",
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
# V2.2: LLM 最终验证 — 关键词初筛 + LLM 终判
# ============================================================

def filter_with_llm_fallback(
    title: str,
    content: str = "",
) -> Dict[str, Any]:
    """
    混合分类策略：关键词初筛 → LLM 最终判定。

    流程:
      1. 关键词先判定：
         - 硬排除命中 → 非广告
         - 非广东移动采购主体 → 非广告
      2. 其余全部交由 LLM 对公告全文做最终判定。

    关键词不再做"广告类"的最终判断——只做排除。
    LLM 是唯一的广告类判定者。
    """
    import logging
    _logger = logging.getLogger(__name__)

    # ── 关键词初筛（仅做排除，不做确认）──
    kw_result = filter_advertisement_projects(title, content)

    # 关键词明确排除（非移动采购主体 / 硬排除词）→ 直接拒绝
    if not kw_result["is_ad"]:
        kw_result["classifier"] = "keyword"
        return kw_result

    # 非中国移动采购主体 → 直接拒绝
    if not _is_mobile_purchaser(title):
        return {
            "is_ad": False, "matched_keywords": [],
            "category": "", "reason": "非中国移动采购主体",
            "classifier": "keyword",
        }

    # ── 以上只是粗筛（Step 1），以下 LLM 逐条精判（Step 2）──
    # 不设任何关键词跳过 LLM 的捷径。
    # 即使是"广告设计"这类看似明确的标题，也可能实际是"广告位招租"等非采购公告。
    # 所有候选公告必须经 LLM 阅读全文后最终判定。

    # ── LLM 最终判定 ──
    try:
        from app.services.llm_classifier import classify_by_llm
        _logger.info(f"LLM验证: {title[:50]}...")
        llm_result = classify_by_llm(title, content)

        if llm_result["is_ad"]:
            return {
                "is_ad": True,
                "matched_keywords": kw_result.get("matched_keywords", []),
                "category": llm_result.get("category", kw_result.get("category", "其他营销类")),
                "reason": f"LLM验证通过: {llm_result.get('reason', '')}",
                "classifier": "llm",
            }
        else:
            return {
                "is_ad": False,
                "matched_keywords": [],
                "category": "",
                "reason": f"LLM排除: {llm_result.get('reason', '')}",
                "classifier": "llm",
            }
    except Exception as e:
        _logger.warning(f"LLM验证异常，回退关键词结果: {e}")
        kw_result["classifier"] = "keyword"
        return kw_result


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

    print(f"\n{'='*40}")
    print(f"通过: {passed}, 失败: {failed}, 总计: {passed + failed}")
