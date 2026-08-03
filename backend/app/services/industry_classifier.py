"""
标中宝 V3 — 行业分类器（行业 + 业务类别二级分类）

设计原则:
  - 完全独立于原有 keyword_filter.py，不影响广告采集
  - 先判定行业(industry_type)，再判定业务类别(project_category)
  - 优先关键词匹配，回退 LLM 分类
"""

from typing import Dict, Any, List, Optional


# ============================================================
# 行业识别关键词
# ============================================================

INDUSTRY_KEYWORDS: Dict[str, List[str]] = {
    "运营商": [
        "中国移动", "移动通信", "广东移动", "移动广东", "中国电信", "电信股份",
        "中电信", "中国联通", "联通数字", "中移", "铁通", "咪咕",
    ],
    "银行": [
        "工商银行", "农业银行", "中国银行", "建设银行", "交通银行", "邮储银行",
        "招商银行", "浦发银行", "中信银行", "光大银行", "民生银行", "兴业银行",
        "平安银行", "华夏银行", "广发银行", "北京银行", "上海银行",
        "农商银行", "农村商业银行", "农信社", "人民银行", "银联",
    ],
    "政府": [
        "政府采购", "公共资源交易", "财政局", "教育局", "公安局", "交通局",
        "卫健委", "住建局", "城管局", "人社局", "民政局", "水利局",
        "人民医院", "中医院", "中心医院", "大学", "学院", "学校",
        "税务局", "海关", "法院", "检察院", "市场监督管理局",
        "自然资源", "生态环境", "退役军人", "应急管理",
        "街道办事处", "镇政府", "区政府", "市政府",
        "省政府", "部委", "直属单位", "事业单位", "机关",
    ],
    "保险": [
        "中国人寿", "中国平安", "太平洋保险", "人保财险", "泰康保险",
        "新华保险", "阳光保险", "太平保险", "大地保险", "中华保险",
        "人民保险", "保险公司",
    ],
    "能源": [
        "国家电网", "南方电网", "中石化", "中石油", "中海油",
        "华能", "大唐", "华电", "国电", "国家能源",
        "电网公司", "供电局", "电力公司", "燃气", "水务",
    ],
}

# 行业 -> 业务类别关键词
INDUSTRY_CATEGORIES: Dict[str, List[Dict[str, Any]]] = {
    "运营商": [
        # ── 广告营销类（8个赛道，由 keyword_filter 初筛后 LLM 精分类）──
        {"category": "广告创意设计", "keywords": ["广告设计", "广告创意", "平面设计", "VI设计", "全案策划", "品牌设计", "创意设计", "广告策划"]},
        {"category": "物料制作印刷", "keywords": ["物料制作", "物料采购", "宣传物料", "喷绘", "印刷品", "门头招牌", "展架", "海报", "宣传品制作", "广告制作", "宣传制作", "印制"]},
        {"category": "活动策划执行", "keywords": ["活动策划", "活动执行", "营销活动", "发布会", "路演", "展会", "校园营销", "客户活动", "客户关怀", "集团客户活动", "政企客户活动", "客户服务活动", "行业交流", "运动会", "嘉年华"]},
        {"category": "品牌宣传传播", "keywords": ["品牌宣传", "品牌推广", "媒体宣传", "公关传播", "整合营销", "品牌策划", "品牌代理", "宣传策划", "企业形象宣传", "品牌传播", "宣传推广", "宣传服务", "宣传支撑", "行业宣传", "广告宣传", "品牌运营", "宣推"]},
        {"category": "视频内容制作", "keywords": ["视频制作", "宣传片", "短视频", "动画", "拍摄"]},
        {"category": "新媒体运营", "keywords": ["新媒体", "公众号", "抖音", "直播运营", "H5", "内容运营", "触点运营", "电子渠道"]},
        {"category": "媒介资源投放", "keywords": ["广告投放", "媒介", "广告发布", "广告媒介", "广告宣传", "媒体广告", "户外广告", "电梯广告", "电子屏广告", "框架广告", "信息流", "阅报栏", "社区道闸", "楼宇广告", "广告代理", "广告综合"]},
        {"category": "渠道营销推广", "keywords": ["渠道营销", "网格营销", "地推", "门店推广", "商圈推广", "校园推广", "社区推广", "营销支撑", "运营支撑", "营销服务", "营销平台"]},
        # ── 非广告类（6个赛道，按 specificity 排序：先精确后宽泛）──
        {"category": "设计勘察", "keywords": ["勘察设计", "可行性研究", "工程设计", "规划设计"]},
        {"category": "通信工程建设", "keywords": ["基站", "机房建设", "机房配套", "光缆", "管线", "铁塔", "室分", "配套施工", "土建", "塔桅", "接入机房", "单管塔", "建设工程", "施工服务", "通信工程"]},
        {"category": "ICT系统集成", "keywords": ["系统集成", "ICT", "软件开发", "平台建设", "管理系统", "大数据", "云计算", "AI", "软硬件", "信息化"]},
        {"category": "设备采购", "keywords": ["服务器", "交换机", "路由器", "存储", "网络设备", "UPS", "空调", "电源", "设备采购", "设备租赁", "终端设备", "前置柜"]},
        {"category": "网络维护代维", "keywords": ["网络维护", "代维", "运维", "维保", "网络优化", "线路维护", "网络安全", "技术支持", "网络支撑"]},
        {"category": "行政物业", "keywords": ["物业", "保安", "保洁", "食堂", "绿化", "消防", "车辆", "办公用品", "速递", "快递", "租赁服务", "消防设施", "检测服务", "服务外包"]},
    ],
    "银行": [
        {"category": "IT设备采购", "keywords": ["服务器", "存储", "网络设备", "计算机", "打印机", "ATM", "自助设备"]},
        {"category": "软件开发集成", "keywords": ["软件开发", "系统开发", "平台建设", "APP", "小程序", "数据平台"]},
        {"category": "网络安全", "keywords": ["网络安全", "信息安全", "等保", "加密", "防火墙", "安全审计"]},
        {"category": "数据中心建设", "keywords": ["数据中心", "机房", "灾备", "UPS", "暖通", "综合布线"]},
        {"category": "网点装修", "keywords": ["网点装修", "营业厅装修", "门头", "标识", "家具"]},
        {"category": "营销宣传", "keywords": ["营销", "宣传", "广告", "活动", "物料", "礼品", "信用卡"]},
        {"category": "咨询服务", "keywords": ["咨询", "审计", "法律", "评估", "培训"]},
    ],
    "政府": [
        {"category": "信息化建设", "keywords": ["信息化", "软件开发", "系统建设", "大数据", "云平台", "智慧城市"]},
        {"category": "设备采购", "keywords": ["设备采购", "办公设备", "医疗设备", "教学设备", "实验室", "仪器"]},
        {"category": "工程建设", "keywords": ["建设工程", "施工", "装修", "市政", "道路", "桥梁", "水利"]},
        {"category": "物业服务", "keywords": ["物业", "保安", "保洁", "食堂", "绿化", "维保"]},
        {"category": "咨询服务", "keywords": ["咨询", "规划", "设计", "监理", "评估", "审计", "法律"]},
    ],
    "保险": [
        {"category": "IT系统建设", "keywords": ["系统开发", "平台建设", " IT", "软件", "数据"]},
        {"category": "宣传推广", "keywords": ["宣传", "广告", "活动", "品牌", "营销", "物料"]},
        {"category": "咨询服务", "keywords": ["咨询", "审计", "培训", "法律"]},
    ],
    "能源": [
        {"category": "设备采购", "keywords": ["设备采购", "变压器", "开关柜", "电缆", "电表", "仪表"]},
        {"category": "工程建设", "keywords": ["工程建设", "施工", "安装", "线路", "变电站", "管道"]},
        {"category": "IT系统", "keywords": ["系统", "软件", "平台", "信息化", "智能"]},
        {"category": "勘察设计", "keywords": ["勘察", "设计", "规划", "咨询"]},
    ],
}

DEFAULT_INDUSTRY = "其他"
DEFAULT_CATEGORY = "其他采购"


def classify_industry(title: str, content: str = "") -> str:
    """
    根据标题和正文判定行业。

    Returns:
        运营商/银行/政府/保险/能源/其他
    """
    combined = f"{title} {content}"
    scores = {}
    for industry, keywords in INDUSTRY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in combined)
        if score > 0:
            scores[industry] = score

    if scores:
        return max(scores, key=scores.get)
    return DEFAULT_INDUSTRY


def classify_category(title: str, content: str = "", industry: str = "") -> str:
    """
    在指定行业下判定业务类别。

    Args:
        title: 项目标题
        content: 公告正文
        industry: 行业类型。如果为空则先自动判定。

    Returns:
        业务类别名称
    """
    if not industry:
        industry = classify_industry(title, content)

    rules = INDUSTRY_CATEGORIES.get(industry, [])
    if not rules:
        return DEFAULT_CATEGORY

    combined = f"{title} {content}"

    # ── 排除标准模板语中的误匹配 ──
    # "发布公告的媒介" 是招标公告的标准模板语，不应匹配到 "媒介资源投放"
    BOILERPLATE_PATTERNS = [
        ("媒介", "发布公告的媒介"),
    ]

    for rule in rules:
        for kw in rule["keywords"]:
            if kw in combined:
                # 检查是否为模板语误匹配
                is_boilerplate = False
                for kw_check, pattern in BOILERPLATE_PATTERNS:
                    if kw == kw_check and pattern in combined:
                        # 确认该关键词出现的位置是否在模板语上下文中
                        idx = combined.find(kw)
                        pattern_idx = combined.find(pattern)
                        if pattern_idx != -1 and abs(idx - pattern_idx) < 30:
                            is_boilerplate = True
                            break
                if not is_boilerplate:
                    return rule["category"]

    return DEFAULT_CATEGORY


def classify_industry_and_category(
    title: str,
    content: str = "",
    data_source: str = "",
) -> Dict[str, str]:
    """
    一站式分类：同时返回行业和业务类别。

    Args:
        title: 项目标题
        content: 公告正文
        data_source: 数据来源（辅助判断行业）

    Returns:
        {"industry_type": "运营商", "project_category": "广告创意设计"}
    """
    # 数据来源辅助：运营商来源直接判定行业
    if data_source in ("b2b_10086", "telecom", "unicom"):
        industry = "运营商"
    else:
        industry = classify_industry(title, content)

    category = classify_category(title, content, industry)
    return {
        "industry_type": industry,
        "project_category": category,
    }
