"""清理 _parse_date 返回 date.today() 导致的假日期记录，然后重新采集。"""
import sqlite3
import sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "biaozhongbao.db")
db = sqlite3.connect(db_path)

# 1. 统计
total = db.execute("SELECT COUNT(*) FROM announcements").fetchone()[0]
bad_date = db.execute(
    "SELECT COUNT(*) FROM announcements WHERE announce_date='2026-07-29' AND data_source='b2b_10086'"
).fetchone()[0]
bad_deadline = db.execute(
    "SELECT COUNT(*) FROM announcements WHERE deadline='1900-01-01 00:00:00'"
).fetchone()[0]

print(f"总记录: {total}")
print(f"b2b_10086 假日期 (2026-07-29): {bad_date}")
print(f"空 deadline (1900-01-01): {bad_deadline}")

# 2. 删除假日期记录（删除后重新采集）
if bad_date > 0:
    db.execute(
        "DELETE FROM announcements WHERE announce_date='2026-07-29' AND data_source='b2b_10086'"
    )
    print(f"✅ 已删除 {bad_date} 条 b2b_10086 假日期记录")
    
# 3. 清理空 deadline 
if bad_deadline > 0:
    db.execute(
        "UPDATE announcements SET deadline=NULL WHERE deadline='1900-01-01 00:00:00'"
    )
    print(f"✅ 已将 {bad_deadline} 条空 deadline 设为 NULL")

db.commit()
remaining = db.execute("SELECT COUNT(*) FROM announcements").fetchone()[0]
print(f"剩余记录: {remaining}")
db.close()
