"""
创建默认管理员账户

用法:
    python -m app.scripts.seed_admin
"""
import asyncio
import logging
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.core.security import hash_password

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"


async def seed_admin():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.username == DEFAULT_ADMIN_USERNAME)
        )
        existing = result.scalar_one_or_none()

        if existing:
            logger.info(f"管理员用户已存在: {existing.username}")
            return

        password_hash, password_salt = hash_password(DEFAULT_ADMIN_PASSWORD)
        admin = User(
            username=DEFAULT_ADMIN_USERNAME,
            password_hash=password_hash,
            password_salt=password_salt,
            display_name="系统管理员",
            is_admin=True,
        )
        db.add(admin)
        await db.commit()
        logger.info(f"✅ 默认管理员创建成功: {DEFAULT_ADMIN_USERNAME} / {DEFAULT_ADMIN_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(seed_admin())
