"""直接测试 zhaobiao.cn 广东移动广告招标采集"""
import sys, os, logging
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("test")

from adapters.zhaobiao_adapter import ZhaobiaoAdapter

config = {
    "search_keyword": "广东移动 广告",
    "max_pages": 2,
    "min_delay": 2.0,
    "max_delay": 4.0,
    "timeout": 30,
    "max_retries": 2,
}
adapter = ZhaobiaoAdapter(config)
print("=== 测试 zhaobiao.cn (中国招标网) ===")
print(f"适配器: {adapter.get_source_name()}")

all_items = []
for page in range(1, config["max_pages"] + 1):
    print(f"\n--- 第 {page} 页 ---")
    html = adapter.fetch_list(page=page)
    print(f"HTML长度: {len(html) if html else 0}")
    if not html or len(html) < 200:
        print("  WARN: HTML内容过短或为空，停止")
        break
    
    items = adapter.parse_list(html)
    print(f"解析到 {len(items)} 条")
    for i, item in enumerate(items[:10]):
        title = item.get("title", "")[:70]
        date = item.get("publish_date", "")
        url = item.get("detail_url", "")[:70]
        print(f"  [{i+1}] {title}")
        print(f"       日期: {date}  链接: {url}")
    
    all_items.extend(items)
    if not items:
        break

print(f"\n=== 汇总: 共 {len(all_items)} 条 ===")
