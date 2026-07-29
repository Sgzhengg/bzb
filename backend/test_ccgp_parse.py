"""快速验证 ccgp parse_list + 完整 run 流程"""
import sys, os, logging
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

from adapters.ccgp_adapter import CcgpAdapter

# 最小化配置：只测1页1分类
config = {"max_pages": 1, "min_delay": 2, "max_delay": 4, "max_retries": 2,
          "categories": ["gkzb"], "scope": "local"}
adapter = CcgpAdapter(config)

print("=== 测试1: parse_list ===")
url = adapter._get_list_url("gkzb", 1, "local")
html = adapter._fetch_list_page(url)
items = adapter.parse_list(html, list_url=url)
print(f"解析到 {len(items)} 条")
for i, item in enumerate(items[:3]):
    print(f"  [{i+1}] {item.get('title', '')[:70]}")

print("\n=== 测试2: fetch_detail + normalize ===")
if items:
    item = items[0]
    print(f"  抓取详情: {item['title'][:50]}")
    title_html, pdf = adapter.fetch_detail(item["url"])
    print(f"  title_html: {(title_html or '')[:80]}")
    parsed = adapter.parse_detail(title_html, pdf)
    record = adapter._normalize_record(parsed)
    print(f"  is_target={record.get('is_ad')}, industry_type={record.get('industry_type')}, category={record.get('project_category')}")
