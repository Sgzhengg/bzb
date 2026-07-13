"""
全国省份城市配置 — 标中宝 V2 多省扩展

用途：
  1. 爬虫多关键词轮询
  2. API 省份/城市筛选
  3. 城市名动态正则匹配
  4. 调度器分省采集

数据来源：中国移动各省分公司架构
"""

from typing import List, Dict


# ============================================================
# 省份配置
# ============================================================

class ProvinceConfig:
    """省份配置"""
    def __init__(self, name: str, code: str, cities: List[str], priority: bool = True):
        self.name = name
        self.code = code
        self.cities = cities
        self.priority = priority

    @property
    def b2b_search_keyword(self) -> str:
        """生成 b2b.10086.cn 搜索关键词"""
        return f"{self.name}移动 广告 宣传 品牌 活动 物料"

    @property
    def zhaobiao_search_keyword(self) -> str:
        """生成招标网搜索关键词"""
        return f"{self.name}移动 广告"

    @property
    def general_search_keyword(self) -> str:
        """生成通用搜索关键词（含重点城市）"""
        top_cities = " ".join(self.cities[:3])
        return f"{self.name}移动 {top_cities} 招标 采购"


# ============================================================
# 重点省份（高频采集，含所有地市）
# ============================================================

PRIORITY_PROVINCES: List[ProvinceConfig] = [
    ProvinceConfig("广东", "GD", [
        "广州", "深圳", "东莞", "佛山", "珠海", "惠州", "中山",
        "江门", "汕头", "湛江", "茂名", "肇庆", "梅州", "汕尾",
        "河源", "阳江", "清远", "韶关", "潮州", "揭阳", "云浮",
    ]),
    ProvinceConfig("广西", "GX", [
        "南宁", "柳州", "桂林", "玉林", "梧州", "北海", "贵港",
        "钦州", "百色", "河池", "贺州", "来宾", "崇左", "防城港",
    ]),
    ProvinceConfig("福建", "FJ", [
        "福州", "厦门", "泉州", "漳州", "龙岩", "三明", "南平", "莆田", "宁德",
    ]),
    ProvinceConfig("海南", "HI", [
        "海口", "三亚", "儋州", "三沙",
    ]),
    ProvinceConfig("浙江", "ZJ", [
        "杭州", "宁波", "温州", "嘉兴", "湖州", "绍兴", "金华", "衢州", "舟山", "台州", "丽水",
    ]),
    ProvinceConfig("湖南", "HN", [
        "长沙", "株洲", "湘潭", "衡阳", "邵阳", "岳阳", "常德",
        "张家界", "益阳", "郴州", "永州", "怀化", "娄底", "湘西",
    ]),
    ProvinceConfig("安徽", "AH", [
        "合肥", "芜湖", "蚌埠", "淮南", "马鞍山", "淮北", "铜陵",
        "安庆", "黄山", "滁州", "阜阳", "宿州", "六安", "亳州", "池州", "宣城",
    ]),
    ProvinceConfig("山东", "SD", [
        "济南", "青岛", "淄博", "枣庄", "东营", "烟台", "潍坊",
        "济宁", "泰安", "威海", "日照", "临沂", "德州", "聊城", "滨州", "菏泽",
    ]),
]

# ============================================================
# 普通省份（低频采集，仅搜省公司级别）
# ============================================================

NORMAL_PROVINCES: List[ProvinceConfig] = [
    ProvinceConfig("江苏", "JS", ["南京", "苏州", "无锡"], priority=False),
    ProvinceConfig("四川", "SC", ["成都", "绵阳"], priority=False),
    ProvinceConfig("湖北", "HB", ["武汉", "宜昌"], priority=False),
    ProvinceConfig("河南", "HA", ["郑州", "洛阳"], priority=False),
    ProvinceConfig("河北", "HE", ["石家庄", "唐山"], priority=False),
    ProvinceConfig("辽宁", "LN", ["沈阳", "大连"], priority=False),
    ProvinceConfig("江西", "JX", ["南昌", "赣州"], priority=False),
    ProvinceConfig("陕西", "SN", ["西安"], priority=False),
    ProvinceConfig("山西", "SX", ["太原"], priority=False),
    ProvinceConfig("云南", "YN", ["昆明"], priority=False),
    ProvinceConfig("贵州", "GZ", ["贵阳", "遵义"], priority=False),
    ProvinceConfig("吉林", "JL", ["长春"], priority=False),
    ProvinceConfig("黑龙江", "HL", ["哈尔滨"], priority=False),
    ProvinceConfig("甘肃", "GS", ["兰州"], priority=False),
    ProvinceConfig("内蒙古", "NM", ["呼和浩特", "包头"], priority=False),
    ProvinceConfig("新疆", "XJ", ["乌鲁木齐"], priority=False),
    ProvinceConfig("西藏", "XZ", ["拉萨"], priority=False),
    ProvinceConfig("青海", "QH", ["西宁"], priority=False),
    ProvinceConfig("宁夏", "NX", ["银川"], priority=False),
    ProvinceConfig("天津", "TJ", ["天津"], priority=False),
    ProvinceConfig("重庆", "CQ", ["重庆"], priority=False),
    ProvinceConfig("上海", "SH", ["上海"], priority=False),
    ProvinceConfig("北京", "BJ", ["北京"], priority=False),
]


# ============================================================
# 工具函数
# ============================================================

def get_all_provinces() -> List[ProvinceConfig]:
    """获取所有省份配置"""
    return PRIORITY_PROVINCES + NORMAL_PROVINCES


def get_all_cities() -> List[str]:
    """获取全国所有城市名列表（用于正则匹配）"""
    cities = []
    for p in get_all_provinces():
        cities.extend(p.cities)
    # 去重并排序（长地名优先，避免短匹配）
    cities = sorted(set(cities), key=lambda x: -len(x))
    return cities


def get_city_to_province_map() -> Dict[str, str]:
    """城市名 → 省份名 映射（用于自动识别归属省份）"""
    mapping = {}
    for p in get_all_provinces():
        for city in p.cities:
            mapping[city] = p.name
    return mapping


def get_province_by_city(city: str) -> str:
    """根据城市名推断所属省份"""
    return get_city_to_province_map().get(city, "")


def get_province_by_name(name: str):
    """根据省份名获取 ProvinceConfig"""
    for p in get_all_provinces():
        if p.name == name:
            return p
    return None


def build_city_regex_pattern() -> str:
    """构建全国城市名正则模式（长地名优先）"""
    cities = get_all_cities()
    # 转义特殊字符
    import re
    escaped = [re.escape(c) for c in cities]
    return '|'.join(escaped)
