import sqlite3
db = sqlite3.connect("d:/bzb/backend/biaozhongbao.db")
patterns = [
    ("征集意见/技术规范", "%征集%"),
    ("技术规范书", "%技术规范书%"),
    ("技术评分表", "%技术评分表%"),
    ("供应商核查/入围", "%供应商核查%"),
    ("意见征询", "%意见征询%"),
]
for label, pat in patterns:
    cnt = db.execute("SELECT COUNT(1) FROM announcements WHERE title LIKE ?", (pat,)).fetchone()[0]
    if cnt > 0:
        print(f"  {label}: {cnt}条")
db.close()
