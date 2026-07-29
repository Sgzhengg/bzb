import sqlite3
db = sqlite3.connect("d:/bzb/backend/biaozhongbao.db")
db.execute("DELETE FROM announcements WHERE industry_type != '运营商'")
db.commit()
c = db.execute("SELECT COUNT(1) FROM announcements").fetchone()[0]
print(f"remaining: {c}")
db.close()
