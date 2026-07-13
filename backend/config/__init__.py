# 标中宝配置模块
from .provinces import (
    ProvinceConfig,
    PRIORITY_PROVINCES,
    NORMAL_PROVINCES,
    get_all_provinces,
    get_all_cities,
    get_city_to_province_map,
    get_province_by_city,
    get_province_by_name,
    build_city_regex_pattern,
)
