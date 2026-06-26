"""
招标公告 SQLAlchemy ORM 模型（最小模型，用于客情关联提醒）
"""

from sqlalchemy import (
    Column, Integer, String, Text, Date, DateTime, Numeric,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class Announcement(Base):
    """招标公告"""

    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    title = Column(String(500), nullable=False, comment="项目名称")
    purchaser_id = Column(Integer, ForeignKey("purchasers.id", ondelete="RESTRICT"), nullable=False, comment="采购方ID")
    purchaser_level = Column(String(50), nullable=False, comment="采购方层级")
    procurement_method = Column(String(30), nullable=False, default="公开招标", comment="采购方式")
    budget = Column(Numeric(12, 2), default=0, comment="预算金额（万元）")
    project_category = Column(String(30), nullable=False, comment="项目类别")
    announce_date = Column(Date, nullable=False, comment="公告发布时间")
    deadline = Column(DateTime, nullable=False, comment="投标截止时间")
    qualification_requirements = Column(Text, comment="资格要求")
    score_weight = Column(JSONB, comment="评分权重（JSON）")
    source_url = Column(String(1000), comment="原文链接")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # 关联
    purchaser = relationship("Purchaser", backref="announcements", lazy="joined")

    def __repr__(self):
        return f"<Announcement(id={self.id}, title={self.title[:30]}...)>"
