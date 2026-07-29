import sqlite3
db = sqlite3.connect("biaozhongbao.db")
db.execute("UPDATE announcements SET industry_type='运营商' WHERE data_source IN ('b2b_10086','telecom','unicom') AND industry_type=''")
db.commit()
r = db.execute("SELECT industry_type, COUNT(*) FROM announcements GROUP BY industry_type").fetchall()
print(r)
db.close()
