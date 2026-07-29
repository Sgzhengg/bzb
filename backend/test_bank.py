"""测试银行适配器（不入库）"""
import sys, os, logging
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

from adapters.bank_adapter import BankAdapter

adapter = BankAdapter({"max_pages": 1, "min_delay": 1, "max_delay": 2})
print("=== 测试 bank_adapter ===\n")

results = adapter.run(save_to_db=False)
print(f"\n采集到 {len(results)} 条银行广告招标")
for r in results[:10]:
    title = r.get("title", "")[:70]
    date = r.get("announce_date", "")
    print(f"  [{date}] {title}")
