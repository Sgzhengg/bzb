"""直接测试 ccgp (中国政府采购网) 广东移动广告招标采集"""
import sys, os, logging, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("test")

from adapters.ccgp_adapter import CcgpAdapter

# 测试 ccgp
config = {
    "search_keyword": "广东移动 广告",
    "max_pages": 2,
    "min_delay": 3.0,
    "max_delay": 6.0,
    "timeout": 30,
    "max_retries": 2,
    "scope": "all",   # 中央+地方
}
adapter = CcgpAdapter(config)
print("=" * 60)
print("  测试: 中国政府采购网 (ccgp.gov.cn)")
print("=" * 60)
print(f"  适配器: {adapter.get_source_name()}")

# 直接测试 run() 方法（完整采集流程）
print("\n  正在运行完整采集...")
try:
    items = adapter.run(save_to_db=False)
    print(f"\n  ✅ 采集完成: {len(items)} 条")
    for i, item in enumerate(items[:10]):
        print(f"  [{i+1}] {item.get('title', 'N/A')[:70]}")
        print(f"      日期: {item.get('publish_date', 'N/A')}  来源: {item.get('source', 'N/A')}")
except Exception as e:
    print(f"\n  ❌ 采集失败: {e}")
    logger.error("ccgp test failed", exc_info=True)

print("\n" + "=" * 60)
