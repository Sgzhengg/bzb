"""完整测试ccgp适配器"""
import sys, os
import logging
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adapters.ccgp_adapter import CcgpAdapter

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')

config = {
    'max_pages': 2,  # 测试2页
    'min_delay': 8.0,  # 增加延迟避免反爬
    'max_delay': 12.0,
    'categories': ['gkzb'],  # 只测试公开招标
    'scope': 'central',  # 只测试中央
}

print("=" * 70)
print("完整测试 ccgp 适配器 (中央公开招标)")
print("=" * 70)

adapter = CcgpAdapter(config)

try:
    results = adapter.run(save_to_db=False, max_pages=2)
    print(f"\n采集完成: {len(results)} 条广告类项目")

    print("\n前5条结果:")
    for i, item in enumerate(results[:5]):
        print(f"[{i+1}] {item.get('title', 'N/A')[:60]}")
        print(f"    类型: {item.get('project_category', 'N/A')}")
        print(f"    是否广告: {item.get('is_ad', False)}")
        print(f"    预算: {item.get('budget', 'N/A')}")

except Exception as e:
    print(f"测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("测试完成")
print("=" * 70)
