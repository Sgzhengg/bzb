"""
标中宝 — 广告类招标项目关键词过滤与赛道识别模块
用于从海量招标公告中筛选广东移动广告相关项目，并自动归类赛道。
"""

from typing import List, Dict, Optional
import re


# ============================================================
# 关键词配置
# ============================================================

# 保留关键词 — 命中任意一个即判定为广告/营销类项目
KEEP_KEYWORDS: List[str] = [
    # 品牌策略
    "品牌", "策略", "规划", "定位",
    # 创意设计
    "创意", "设计", "视觉", "VI", "海报", "画册",
    # 媒介投放
    "投放", "媒介", "KOL", "代理",
    # 活动会展
    "活动", "路演", "展会", "发布会", "文体", "工会",
    "运动会", "比赛", "竞赛", "评选", "表彰", "庆典", "开放日",
    "展览", "展厅", "展馆", "展示", "博览会",
    # 渠道营销
    "促销", "网格", "地推", "门店", "渠道",
    # 内容制作
    "制作", "拍摄", "物料", "H5", "脚本", "视频", "短视频",
    # 政企传播
    "党群", "党建", "宣传", "学习", "集团客户", "政企",
    "新闻", "采访", "舆情", "培训", "研修", "参访",
    "客户服务", "客户关怀", "客户体验",
    # 论坛交流
    "论坛", "峰会", "研讨会", "沙龙", "座谈会", "交流会", "推介会",
    # 新媒体
    "公众号", "视频号", "直播", "代运营", "新媒体", "运营",
    # 通用广告
    "广告", "营销", "推广", "传播", "策划",
]

# 排除关键词 — 命中任意一个即判定为非广告/营销类项目（优先级更高）
EXCLUDE_KEYWORDS: List[str] = [
    # 纯工程建设类
    "基站", "光缆", "机房", "机电", "施工", "监理", "勘察", "EPC",
    "土建", "装修", "布线", "配电", "空调", "电梯", "消防",
    # 后勤保障类
    "食材", "食堂", "保洁", "保安", "物业", "家具", "办公设备",
    # IT 技术类（非营销）
    "服务器", "交换机", "路由器", "数据库", "云计算",
]

# 赛道识别规则（按优先级排序，命中即停止）
CATEGORY_RULES: List[Dict[str, any]] = [
    {
        "category": "品牌策略类",
        "keywords": ["品牌策略", "品牌规划", "品牌定位", "品牌健康", "年度策略"],
    },
    {
        "category": "创意设计类",
        "keywords": ["创意设计", "视觉设计", "VI设计", "海报设计", "画册设计"],
    },
    {
        "category": "媒介投放类",
        "keywords": ["媒介投放", "广告投放", "KOL投放", "媒体代理", "投放代理"],
    },

    {
        "category": "渠道营销类",
        "keywords": ["渠道营销", "网格促销", "门店宣传", "地推", "促销活动"],
    },
    {
        "category": "内容制作类",
        "keywords": ["内容制作", "视频制作", "物料制作", "H5制作", "宣传片"],
    },
    {
        "category": "政企传播类",
        "keywords": [
            "党群宣传", "党建学习", "集团客户", "政企服务", "企业宣传",
            "新闻宣传", "舆情管理", "客户服务", "客户关怀", "客户体验",
            "培训学习", "研修班", "参访交流",
        ],
    },
    {
        "category": "活动会展类",
        "keywords": [
            "活动执行", "路演", "展会", "发布会", "工会活动", "文体活动",
            "运动会", "竞赛活动", "评选活动", "表彰大会", "庆典活动",
            "展览展示", "展厅设计", "博览会", "开放日", "体验日",
            "论坛活动", "峰会", "研讨会", "沙龙活动", "座谈会", "交流会",
        ],
    },
    {
        "category": "新媒体运营类",
        "keywords": ["新媒体运营", "公众号运营", "视频号运营", "直播运营", "代运营"],
    },
]

# 默认赛道（当保留关键词命中但无法匹配具体赛道时）
DEFAULT_CATEGORY = "其他营销类"


# ============================================================
# 核心过滤函数
# ============================================================

def _match_keywords(text: str, keywords: List[str]) -> List[str]:
    """
    在文本中匹配关键词，返回命中的关键词列表（去重）。

    Args:
        text: 待检索的文本
        keywords: 关键词列表

    Returns:
        命中的关键词列表（保持原顺序，去重）
    """
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


def _identify_category(title: str, content: str) -> str:
    """
    根据标题和内容自动识别项目赛道。

    按 CATEGORY_RULES 的顺序依次匹配，首个命中即返回对应赛道；
    若无匹配则返回默认赛道。

    Args:
        title: 项目标题
        content: 项目描述内容

    Returns:
        赛道名称字符串
    """
    combined = f"{title} {content}"
    for rule in CATEGORY_RULES:
        matched = _match_keywords(combined, rule["keywords"])
        if matched:
            return rule["category"]
    return DEFAULT_CATEGORY


def filter_advertisement_projects(
    title: str,
    content: str = "",
) -> Dict[str, any]:
    """
    判断一个招标项目是否属于广告类，并识别其赛道。

    判定逻辑（按优先级）：
    1. 排除优先：若标题或内容命中任一排除关键词 → 非广告类
    2. 保留匹配：若标题或内容命中任一保留关键词 → 广告类
    3. 均未命中 → 非广告类

    Args:
        title: 项目名称/标题
        content: 项目描述/公告正文（可选）

    Returns:
        {
            "is_ad": True / False,
            "matched_keywords": [...],   # 命中的保留关键词
            "category": "赛道名称",       # 仅 is_ad=True 时有效
            "reason": "判定原因"           # 仅 is_ad=False 时有效
        }

    Examples:
        >>> filter_advertisement_projects("广东移动品牌策略规划项目", "包含品牌定位与创意设计")
        {'is_ad': True, 'matched_keywords': ['品牌', '创意', '设计'], 'category': '品牌策略类'}

        >>> filter_advertisement_projects("基站机房施工项目")
        {'is_ad': False, 'matched_keywords': [], 'category': '', 'reason': '命中排除关键词: 基站, 机房, 施工'}
    """
    combined_text = f"{title} {content}"

    # ── 第 1 步：排除关键词检查（优先级最高） ──
    excluded = _match_keywords(combined_text, EXCLUDE_KEYWORDS)
    if excluded:
        return {
            "is_ad": False,
            "matched_keywords": [],
            "category": "",
            "reason": f"命中排除关键词: {', '.join(excluded)}",
        }

    # ── 第 2 步：保留关键词匹配 ──
    matched = _match_keywords(combined_text, KEEP_KEYWORDS)
    if not matched:
        return {
            "is_ad": False,
            "matched_keywords": [],
            "category": "",
            "reason": "未命中任何广告类关键词",
        }

    # ── 第 3 步：赛道识别 ──
    category = _identify_category(title, content)

    return {
        "is_ad": True,
        "matched_keywords": matched,
        "category": category,
        "reason": "",
    }


def apply_preference_boost(
    item: Dict,
    preferred_categories: List[str] = None,
    min_budget: float = 0,
    min_score: float = 0,
) -> Dict:
    """
    根据用户偏好对项目进行加权。

    在原有过滤基础上，对匹配用户偏好赛道的项目增加加权标记，
    供前端排序和展示使用。

    Args:
        item: 已过滤的项目字典（含 project_category, budget, total_score 等）
        preferred_categories: 用户偏好的赛道列表
        min_budget: 最低预算过滤
        min_score: 最低评分过滤

    Returns:
        附加了 preference 字段的项目字典:
        {
            ...原字段,
            "preference": {
                "is_preferred": True/False,
                "category_match": True/False,
                "budget_meets": True/False,
                "score_meets": True/False,
                "boost_score": 0-10,  # 加权分
            }
        }
    """
    boost = {
        "is_preferred": False,
        "category_match": False,
        "budget_meets": True,
        "score_meets": True,
        "boost_score": 0,
    }

    # 预算过滤
    budget = float(item.get("budget", 0) or 0)
    if min_budget > 0 and budget < min_budget:
        boost["budget_meets"] = False

    # 评分过滤
    score = float(item.get("total_score", 0) or 0)
    if min_score > 0 and score < min_score:
        boost["score_meets"] = False

    # 赛道匹配加权
    category = item.get("project_category", "") or item.get("category", "")
    if preferred_categories and category:
        if category in preferred_categories:
            boost["category_match"] = True
            boost["boost_score"] = 5  # 匹配偏好赛道 +5

    # 综合判断
    boost["is_preferred"] = (
        boost["category_match"] or boost["budget_meets"]
    )

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
    """
    批量应用用户偏好。

    Args:
        items: 已过滤的项目列表
        preferred_categories: 偏好赛道
        min_budget: 最低预算
        min_score: 最低评分
        sort_by_preference: 是否按偏好排序（偏好匹配的排在前面）

    Returns:
        附加了 preference 字段并排序后的列表
    """
    result = [
        apply_preference_boost(item, preferred_categories, min_budget, min_score)
        for item in items
    ]

    if sort_by_preference:
        # 排序：偏好匹配 > 高分 > 高预算
        result.sort(
            key=lambda x: (
                0 if x["preference"]["category_match"] else 1,
                -(x.get("total_score", 0) or 0),
                -(x.get("budget", 0) or 0),
            )
        )

    return result


# ============================================================
# 批量过滤便捷函数
# ============================================================

def batch_filter(
    projects: List[Dict[str, str]],
    title_key: str = "title",
    content_key: str = "content",
) -> List[Dict[str, any]]:
    """
    批量过滤招标项目列表。

    Args:
        projects: 项目列表，每项为包含标题和内容的字典
        title_key: 标题字段名
        content_key: 内容字段名

    Returns:
        每个项目的过滤结果列表（与输入同序），每项在原字典基础上增加
        is_ad / matched_keywords / category / reason 字段
    """
    results = []
    for project in projects:
        result = filter_advertisement_projects(
            title=project.get(title_key, ""),
            content=project.get(content_key, ""),
        )
        results.append({**project, **result})
    return results


# ============================================================
# 单元测试
# ============================================================

if __name__ == "__main__":
    import json

    passed = 0
    failed = 0

    def assert_equal(actual, expected, test_name):
        global passed, failed
        if actual == expected:
            passed += 1
            print(f"  ✅ {test_name}")
        else:
            failed += 1
            print(f"  ❌ {test_name}")
            print(f"     期望: {expected}")
            print(f"     实际: {actual}")

    print("=" * 60)
    print("标中宝 — 关键词过滤与赛道识别 单元测试")
    print("=" * 60)

    # ── 测试组 1: 明确的广告类项目 ──
    print("\n📌 测试组 1: 明确的广告类项目")

    r = filter_advertisement_projects(
        "广东移动2024年度品牌传播策略规划服务项目",
        "本项目旨在为中国移动广东公司提供品牌策略规划、品牌定位及品牌健康度调研服务"
    )
    assert_equal(r["is_ad"], True, "品牌策略项目判定")
    assert_equal("品牌" in r["matched_keywords"], True, "命中'品牌'关键词")
    assert_equal("策略" in r["matched_keywords"] or "策略" in str(r), True, "命中'策略'关键词")
    assert_equal(r["category"], "品牌策略类", "赛道识别为品牌策略类")

    r = filter_advertisement_projects(
        "广东移动新媒体广告创意设计与VI视觉系统开发",
        "包含平面广告创意设计、VI视觉识别系统、品牌视觉规范"
    )
    assert_equal(r["is_ad"], True, "创意设计项目判定")
    assert_equal(r["category"], "创意设计类", "赛道：创意+设计+VI → 创意设计类")

    r = filter_advertisement_projects(
        "广东移动短视频KOL广告投放",
        "抖音、快手KOL达人资源采购与信息流广告媒介投放"
    )
    assert_equal(r["is_ad"], True, "媒介投放项目判定")
    assert_equal(r["category"], "媒介投放类", "赛道识别为媒介投放类")

    r = filter_advertisement_projects(
        "广东移动5G校园路演推广活动",
        "在大学城举办5G品牌路演及产品体验活动"
    )
    assert_equal(r["is_ad"], True, "活动执行项目判定")
    assert_equal(r["category"], "活动执行类", "赛道识别为活动执行类")

    r = filter_advertisement_projects(
        "广东移动宣传物料设计与制作项目",
        "包括海报、折页、H5页面等宣传物料的设计与拍摄制作"
    )
    assert_equal(r["is_ad"], True, "内容制作项目判定")
    # "设计"在赛道规则中的优先级高于"制作/物料"，先命中创意设计类
    assert_equal(r["category"], "创意设计类", "赛道：设计先于制作命中 → 创意设计类")

    r = filter_advertisement_projects(
        "广东移动微信公众号代运营与视频号直播服务",
        "负责公众号日常内容策划、视频号直播运营"
    )
    assert_equal(r["is_ad"], True, "新媒体运营项目判定")
    assert_equal(r["category"], "新媒体运营类", "赛道识别为新媒体运营类")

    # ── 测试组 2: 明确的非广告类项目（排除关键词） ──
    print("\n📌 测试组 2: 排除关键词过滤")

    r = filter_advertisement_projects(
        "广东移动基站机房建设工程施工项目",
        "5G基站土建施工及机房配套工程"
    )
    assert_equal(r["is_ad"], False, "基站施工项目排除")
    assert_equal("命中排除关键词" in r["reason"], True, "返回排除原因")

    r = filter_advertisement_projects(
        "广东移动办公大楼物业管理服务项目",
        "含保洁、保安、空调及电梯维保"
    )
    assert_equal(r["is_ad"], False, "物业管理项目排除")

    r = filter_advertisement_projects(
        "广东移动光缆线路勘察设计及EPC总承包",
        "通信光缆线路的勘察设计与施工总承包"
    )
    assert_equal(r["is_ad"], False, "光缆勘察项目排除")

    r = filter_advertisement_projects(
        "广东移动食材采购及食堂运营服务",
        "员工食堂食材供应与餐饮服务"
    )
    assert_equal(r["is_ad"], False, "食材采购项目排除")

    r = filter_advertisement_projects(
        "广东移动办公家具及空调设备采购",
        "办公桌椅、文件柜及中央空调采购安装"
    )
    assert_equal(r["is_ad"], False, "办公设备采购排除")

    # ── 测试组 3: 边界情况 ──
    print("\n📌 测试组 3: 边界情况")

    r = filter_advertisement_projects("", "")
    assert_equal(r["is_ad"], False, "空标题空内容")
    assert_equal(r["reason"], "未命中任何广告类关键词", "空输入原因")

    r = filter_advertisement_projects(
        "网络优化技术服务项目",
        "提供移动通信网络质量优化与技术支持"
    )
    assert_equal(r["is_ad"], False, "无关技术项目")

    # 同时命中保留词和排除词 → 排除优先
    r = filter_advertisement_projects(
        "品牌宣传活动物料制作及基站施工",
        "品牌宣传物料设计与制作，含部分基站施工内容"
    )
    assert_equal(r["is_ad"], False, "保留+排除共存：排除优先")
    assert_equal("基站" in r["reason"], True, "排除原因含'基站'")

    # 含"设计"但属于工程设计
    r = filter_advertisement_projects(
        "通信工程设计服务项目",
        "移动通信网络工程设计"
    )
    assert_equal(r["is_ad"], True, "'设计'属于保留关键词命中")
    assert_equal(r["category"], "创意设计类", "'设计'归属创意设计赛道")

    # ── 测试组 4: 赛道优先级 ──
    print("\n📌 测试组 4: 赛道优先级")

    # 同时含"策略"和"创意" → 策略优先
    r = filter_advertisement_projects(
        "品牌策略与创意设计综合服务",
        "品牌策略规划、广告创意设计"
    )
    assert_equal(r["category"], "品牌策略类", "策略关键词优先级高于创意")

    # ── 测试组 5: 批量过滤 ──
    print("\n📌 测试组 5: 批量过滤")

    projects = [
        {"title": "基站机房施工项目", "content": "土建施工"},
        {"title": "品牌广告投放项目", "content": "媒介投放KOL"},
        {"title": "保洁服务采购", "content": ""},
        {"title": "微信公众号运营", "content": "内容策划与代运营"},
        {"title": "办公设备采购", "content": "空调电梯"},
    ]
    results = batch_filter(projects)
    assert_equal(len(results), 5, "批量过滤返回5条结果")
    assert_equal(results[0]["is_ad"], False, "第1条排除")
    assert_equal(results[1]["is_ad"], True, "第2条保留")
    assert_equal(results[2]["is_ad"], False, "第3条排除")
    assert_equal(results[3]["is_ad"], True, "第4条保留")
    assert_equal(results[4]["is_ad"], False, "第5条排除")

    # ── 结果汇总 ──
    print("\n" + "=" * 60)
    total = passed + failed
    print(f"  测试结果: {passed}/{total} 通过", end="")
    if failed > 0:
        print(f"  ❌ {failed} 个失败")
    else:
        print("  🎉 全部通过！")
    print("=" * 60)
