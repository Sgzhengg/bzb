"""清理数据库中非广东移动的记录"""
import asyncio, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.db.session import AsyncSessionLocal
from app.models.announcement import Announcement
from sqlalchemy import select, delete

async def clean():
    async with AsyncSessionLocal() as s:
        r = await s.execute(select(Announcement))
        total = len(r.scalars().all())
        print(f'当前数据库: {total} 条')
        
        # 删除不含"广东"的记录
        await s.execute(delete(Announcement).where(~Announcement.province.contains('广东')))
        await s.commit()
        
        r = await s.execute(select(Announcement))
        items = r.scalars().all()
        print(f'清理后: {len(items)} 条')
        for i in items[:10]:
            print(f'  [{i.province}] {i.title[:60]}...')

asyncio.run(clean())
