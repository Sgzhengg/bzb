"""
项目-客情关联提醒 SQLAlchemy ORM 模型
"""

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, ForeignKey, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class ProjectRelationAlert(Base):
    """项目-客情关联提醒"""

    __tablename__ = "project_relation_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    announcement_id = Column(
        Integer,
        ForeignKey("announcements.id", ondelete="CASCADE"),
        nullable=False,
        comment="公告ID",
    )
    relation_id = Column(
        Integer,
        ForeignKey("client_relations.id", ondelete="CASCADE"),
        nullable=False,
        comment="客情记录ID",
    )
    alert_reason = Column(Text, nullable=False, comment="提醒原因")
    is_read = Column(Boolean, nullable=False, default=False, comment="是否已读")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # 关联
    announcement = relationship("Announcement", backref="alerts", lazy="joined")
    relation = relationship("ClientRelation", backref="alerts", lazy="joined")

    # 唯一约束：同一公告+同一客情关系只保留一条提醒
    __table_args__ = (
        UniqueConstraint(
            "announcement_id", "relation_id",
            name="uq_alerts_announcement_relation",
        ),
    )

    def __repr__(self):
        return f"<ProjectRelationAlert(id={self.id}, ann={self.announcement_id}, read={self.is_read})>"
