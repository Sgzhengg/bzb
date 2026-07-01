"""
数据库会话管理模块
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

_engine_kwargs = dict(
    echo=False,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
)
if not _is_sqlite:
    _engine_kwargs.update(pool_size=10, max_overflow=20)

engine = create_async_engine(
    settings.DATABASE_URL,
    **_engine_kwargs,
)

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """获取数据库会话的依赖注入"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
