"""修复公告数据：补充预算、URL、投标日期、报名费、保证金"""
import asyncio, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def fix():
    from app.db.session import AsyncSessionLocal
    from sqlalchemy import text

    async with AsyncSessionLocal() as db:
        updates = [
            (2, 85.0, "2026-07-20", 
             "https://zb.zhaobiao.cn/free_v_a3d904fb8979505423646c5aa695d292.html",
             300, 50000),
            (3, 60.0, "2026-07-22",
             "https://zb.zhaobiao.cn/free_v_1beee0b803bed7fda7b16bb233a09227.html",
             0, 30000),
        ]
        for aid, budget, bid_date, url, fee, deposit in updates:
            await db.execute(text(
                "UPDATE announcements SET budget = :budget, bid_date = :bid_date, "
                "source_url = :url, registration_fee = :fee, deposit = :deposit "
                "WHERE id = :id"
            ), {"budget": budget, "bid_date": bid_date, "url": url,
               "fee": fee, "deposit": deposit, "id": aid})
        await db.commit()
        print("Updated all fields")

        result = await db.execute(text("SELECT id, title, budget, source_url, bid_date, registration_fee, deposit FROM announcements"))
        for row in result.fetchall():
            print(f"  ID={row[0]}: budget={row[2]}万, url={str(row[3])[:50]}..., bid={row[4]}, fee={row[5]}, deposit={row[6]}")

asyncio.run(fix())
