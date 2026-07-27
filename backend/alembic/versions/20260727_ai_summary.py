"""添加公告 AI 摘要字段 (ai_summary)

Revision ID: 20260727_ai_summary
Create Date: 2026-07-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = "20260727_ai_summary"
down_revision: Union[str, None] = "20260727_auth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "announcements",
        sa.Column("ai_summary", sa.JSON(), nullable=True,
                  comment="AI智能摘要+资格预审分析 (JSON)"),
    )


def downgrade() -> None:
    op.drop_column("announcements", "ai_summary")
