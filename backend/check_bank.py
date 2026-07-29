import sqlite3
db = sqlite3.connect("biaozhongbao.db")
r = db.execute("SELECT id,industry_type,project_category,title,data_source FROM announcements WHERE data_source='bank'").fetchall()
for row in r:
    print(f"  #{row[0]} [{row[1]}/{row[2]}] {row[3][:70]}")
print(f"Total: {len(r)}")
db.close()
