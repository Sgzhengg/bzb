import sqlite3
db = sqlite3.connect("biaozhongbao.db")
try:
    db.execute('ALTER TABLE announcements ADD COLUMN industry_type VARCHAR(20) DEFAULT ""')
    print("OK - column added")
except sqlite3.OperationalError as e:
    if "duplicate column" in str(e):
        print("Column already exists")
    else:
        raise
db.execute("CREATE INDEX IF NOT EXISTS ix_announcements_industry_type ON announcements(industry_type)")
db.commit()
# 将现有 b2b_10086 数据标记为运营商
db.execute("UPDATE announcements SET industry_type = '运营商' WHERE data_source IN ('b2b_10086', 'telecom', 'unicom') AND industry_type = ''")
updated = db.execute("SELECT changes()").fetchone()[0]
print(f"Updated {updated} existing records to industry_type='运营商'")
db.close()
print("Done")
