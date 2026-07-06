"""
Alembic 数据库迁移配置 - 标中宝
"""
import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.models.base import Base
from app.models import *  # noqa: F401,F403 - 导入所有模型以注册元数据
from app.core.config import settings

# Alembic 使用的目标元数据
target_metadata = Base.metadata

# 解析日志配置
if context.config.config_file_name is not None:
    fileConfig(context.config.config_file_name)

# 从环境变量获取数据库 URL
def get_database_url():
    """获取数据库连接 URL"""
    db_url = os.getenv("BZB_DATABASE_URL", "sqlite:///./biaozhongbao.db")
    # Alembic 不支持异步驱动，需要转换
    return db_url.replace("sqlite+aiosqlite", "sqlite").replace(
        "postgresql+asyncpg", "postgresql"
    )

# 设置 SQLAlchemy URL
context.config.set_main_option("sqlalchemy.url", get_database_url())


# ============================================================
# 迁移运行上下文
# ============================================================

def run_migrations_offline() -> None:
    """离线模式运行迁移（生成 SQL 脚本）"""
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线模式运行迁移（直接连接数据库）"""
    configuration = context.config.get_section(context.config.config_ini_section)
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# 根据上下文决定运行模式
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
