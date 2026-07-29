"""测试运营商全品类采集：b2b_10086 搜索非广告关键词"""
import sys, os, logging
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

from data_collector import DataCollector

# 直接用 data_collector 调用 b2b_10086，它会走 base_adapter._normalize_record
collector = DataCollector()

# 测试：不传 province，让适配器用默认搜索
# 但默认搜索关键词是广告类，我们需要测试是否能用新分类器捕获非广告
# 
# 方案：直接调用 base_adapter 的 _normalize_record 测试几个典型标题

from adapters.b2b_10086_adapter import B2b10086Adapter
adapter = B2b10086Adapter({"max_pages": 1, "source_key": "b2b_10086"})

test_titles = [
    # 广告类（应走原过滤）
    {"title": "中国移动广东公司2026年广告设计服务项目", "content": "广告设计"},
    # 工程类（应走新分类器）
    {"title": "中国移动广东公司2026年机房建设工程项目", "content": "机房建设 土建施工"},
    # 维护类
    {"title": "中国移动浙江公司2026年网络维护服务项目", "content": "网络维护 代维服务"},
    # ICT集成类
    {"title": "中国移动江苏公司2026年ICT系统集成项目", "content": "系统集成 软件开发"},
    # 设备采购类
    {"title": "中国移动广东公司2026年服务器采购项目", "content": "服务器 交换机 采购"},
]

print("运营商全品类测试:\n")
for item in test_titles:
    raw = {"title": item["title"], "content_text": item["content"],
           "purchaser": "中国移动", "purchaser_level": "省公司",
           "procurement_method": "公开招标", "publish_date": "2026-07-29"}
    
    record = adapter._normalize_record(raw)
    is_target = record.get("is_ad", False) or record.get("is_target", False)
    ind = record.get("industry_type", "")
    cat = record.get("project_category", "")
    print(f"  {'✅' if is_target else '❌'} [{ind}/{cat}] {item['title'][:50]}")
