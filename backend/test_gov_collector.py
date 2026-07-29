"""
使用项目已有采集模块 test: data_collector 直接调用政府适配器
"""
import sys, os, logging, json

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("test")

from data_collector import DataCollector

collector = DataCollector()

# 测试 ccgp（中国政府采购网）
print("=" * 60)
print("  🧪 [1/3] 测试 ccgp (中国政府采购网)")
print("=" * 60)
try:
    results = collector.collect(adapter_name="ccgp", save_to_db=True)
    print(f"  结果: {len(results)} 条")
except Exception as e:
    print(f"  ❌ 失败: {e}")

# 测试 gd_zbtb（广东省招标投标监管网）
print("\n" + "=" * 60)
print("  🧪 [2/3] 测试 gd_zbtb (广东招标投标监管网)")
print("=" * 60)
try:
    results = collector.collect(adapter_name="gd_zbtb", save_to_db=True)
    print(f"  结果: {len(results)} 条")
except Exception as e:
    print(f"  ❌ 失败: {e}")

# 测试 gd_ygp（广东公共资源交易平台）
print("\n" + "=" * 60)
print("  🧪 [3/3] 测试 gd_ygp (广东公共资源交易平台)")
print("=" * 60)
try:
    results = collector.collect(adapter_name="gd_ygp", save_to_db=True)
    print(f"  结果: {len(results)} 条")
except Exception as e:
    print(f"  ❌ 失败: {e}")

print("\n" + "=" * 60)
print("  📊 数据库汇总")
print("=" * 60)
import sqlite3
db = sqlite3.connect("biaozhongbao.db")
for src in ["ccgp", "gd_zbtb", "gd_ygp", "b2b_10086"]:
    count = db.execute("SELECT COUNT(*) FROM announcements WHERE data_source=?", (src,)).fetchone()[0]
    print(f"  {src}: {count} 条")
total = db.execute("SELECT COUNT(*) FROM announcements").fetchone()[0]
print(f"  全部: {total} 条")
db.close()
