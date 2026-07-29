import sqlite3
db = sqlite3.connect("d:/bzb/backend/biaozhongbao.db")
rows = db.execute(
    "SELECT id, title, source_url FROM announcements WHERE title LIKE ?",
    ("%直接采购%",)
).fetchall()
for r in rows:
    url = (r[2] or "")[:40]
    title = (r[1] or "")[:60]
    print(f"#{r[0]} | {url} | {title}")
db.close()
