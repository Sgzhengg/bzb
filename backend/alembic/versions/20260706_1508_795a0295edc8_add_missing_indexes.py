"""Add missing indexes

Revision ID: 795a0295edc8
Revises: 5ef50b68bb41
Create Date: 2026-07-06 15:08:19.539232+08:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '795a0295edc8'
down_revision: Union[str, None] = '5ef50b68bb41'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    # 添加缺失的索引（跳过已存在的）
    # client_relations
    try:
        op.create_index('ix_client_relations_purchaser_id', 'client_relations', ['purchaser_id'], unique=False)
    except Exception:
        pass
    try:
        op.create_index('ix_client_relations_rating', 'client_relations', ['rating'], unique=False)
    except Exception:
        pass
    try:
        op.create_index('ix_client_relations_next_followup', 'client_relations', ['next_followup_date'], unique=False)
    except Exception:
        pass

    # historical_awards
    try:
        op.create_index('ix_historical_awards_purchaser_id', 'historical_awards', ['purchaser_id'], unique=False)
    except Exception:
        pass
    try:
        op.create_index('ix_historical_awards_bid_open_date', 'historical_awards', ['bid_open_date'], unique=False)
    except Exception:
        pass
    try:
        op.create_index('ix_historical_awards_project_category', 'historical_awards', ['project_category'], unique=False)
    except Exception:
        pass
    try:
        op.create_index('ix_historical_awards_winner_name', 'historical_awards', ['winner_name'], unique=False)
    except Exception:
        pass

    # project_relation_alerts
    try:
        op.create_index('ix_project_relation_alerts_announcement_id', 'project_relation_alerts', ['announcement_id'], unique=False)
    except Exception:
        pass
    try:
        op.create_index('ix_project_relation_alerts_relation_id', 'project_relation_alerts', ['relation_id'], unique=False)
    except Exception:
        pass
    try:
        op.create_index('ix_project_relation_alerts_is_read', 'project_relation_alerts', ['is_read'], unique=False)
    except Exception:
        pass
    try:
        op.create_index('ix_project_relation_alerts_created_at', 'project_relation_alerts', ['created_at'], unique=False)
    except Exception:
        pass

    # purchasers
    try:
        op.create_index('ix_purchasers_name', 'purchasers', ['name'], unique=False)
    except Exception:
        pass
    try:
        op.create_index('ix_purchasers_level', 'purchasers', ['level'], unique=False)
    except Exception:
        pass
    try:
        op.create_index('ix_purchasers_region', 'purchasers', ['region'], unique=False)
    except Exception:
        pass

    # 唯一约束（使用批量模式）
    try:
        with op.batch_alter_table('announcements') as batch_op:
            batch_op.create_unique_constraint('uq_announcements_source_url', ['source_url'])
    except Exception:
        pass


def downgrade() -> None:
    # 回滚操作
    op.drop_index('ix_client_relations_next_followup', table_name='client_relations')
    op.drop_index('ix_client_relations_rating', table_name='client_relations')
    op.drop_index('ix_client_relations_purchaser_id', table_name='client_relations')
    op.drop_index('ix_historical_awards_winner_name', table_name='historical_awards')
    op.drop_index('ix_historical_awards_project_category', table_name='historical_awards')
    op.drop_index('ix_historical_awards_bid_open_date', table_name='historical_awards')
    op.drop_index('ix_historical_awards_purchaser_id', table_name='historical_awards')
    op.drop_index('ix_project_relation_alerts_created_at', table_name='project_relation_alerts')
    op.drop_index('ix_project_relation_alerts_is_read', table_name='project_relation_alerts')
    op.drop_index('ix_project_relation_alerts_relation_id', table_name='project_relation_alerts')
    op.drop_index('ix_project_relation_alerts_announcement_id', table_name='project_relation_alerts')
    op.drop_index('ix_purchasers_region', table_name='purchasers')
    op.drop_index('ix_purchasers_level', table_name='purchasers')
    op.drop_index('ix_purchasers_name', table_name='purchasers')
    try:
        with op.batch_alter_table('announcements') as batch_op:
            batch_op.drop_constraint('uq_announcements_source_url', type_='unique')
    except Exception:
        pass
