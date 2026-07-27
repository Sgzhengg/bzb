"""
添加 users 表

Revision ID: 20260727_auth
Create Date: 2026-07-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = "20260727_auth"
down_revision: Union[str, None] = "20260706_1508"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(50), nullable=False),
        sa.Column("password_hash", sa.String(128), nullable=False),
        sa.Column("password_salt", sa.String(32), nullable=False),
        sa.Column("display_name", sa.String(100), server_default=""),
        sa.Column("email", sa.String(200), server_default=""),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1")),
        sa.Column("is_admin", sa.Boolean(), server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    op.create_index("ix_users_username", "users", ["username"])


def downgrade() -> None:
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
