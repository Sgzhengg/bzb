"""重新采集 b2b_10086，验证日期修复"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adapters.b2b_10086_adapter import B2b10086Adapter
import yaml

BASE = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(BASE, "adapters", "adapter_config.yaml"), encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

a = B2b10086Adapter(cfg["b2b_10086"])
r = a.run(save_to_db=True)
print(f"\n采集完成: {len(r)} 条")

# 验证日期
import sqlite3
db = sqlite3.connect(os.path.join(BASE, "biaozhongbao.db"))
rows = db.execute(
    "SELECT title, announce_date, deadline FROM announcements WHERE data_source='b2b_10086' ORDER BY id DESC LIMIT 5"
).fetchall()
for row in rows:
    print(f"  date={row[1]}, deadline={row[2]}  {row[0][:50]}")
db.close()
