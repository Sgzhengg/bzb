"""快速验证 ccgp 完整 run 流程 (1类1页, 不入库)"""
import sys, os, logging
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

from adapters.ccgp_adapter import CcgpAdapter

config = {"max_pages": 1, "min_delay": 2, "max_delay": 4, "max_retries": 2,
          "categories": ["gkzb"], "scope": "local"}
adapter = CcgpAdapter(config)

results = adapter.run(save_to_db=False)
print(f"\n{'='*60}")
print(f"  采集完成: {len(results)} 条")
for r in results[:10]:
    ind = r.get("industry_type", "")
    cat = r.get("project_category", "")
    title = r.get("title", "")[:60]
    budget = r.get("budget")
    print(f"  [{ind}/{cat}] {title}" + (f" | 预算{budget}万" if budget else ""))
