"""
客情记录 SQLAlchemy ORM 模型
"""

from sqlalchemy import (
    Column, Integer, String, Text, Date, DateTime,
    ForeignKey, CheckConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class ClientRelation(Base):
    """客情关系记录"""

    __tablename__ = "client_relations"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    purchaser_id = Column(Integer, ForeignKey("purchasers.id", ondelete="RESTRICT"), nullable=False, comment="采购方ID")
    contact_name = Column(String(100), nullable=False, comment="联系人姓名")
    title = Column(String(100), nullable=True, comment="职位")
    phone = Column(String(30), nullable=True, comment="电话")
    email = Column(String(200), nullable=True, comment="邮箱")
    last_contact_date = Column(Date, nullable=True, comment="最近接触时间")
    contact_method = Column(String(20), nullable=True, comment="接触方式")
    contact_summary = Column(Text, nullable=True, comment="接触内容摘要")
    rating = Column(String(1), nullable=False, default="C", comment="关系评级 S/A/B/C/D")
    next_followup_date = Column(Date, nullable=True, comment="下次跟进提醒日期")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # 关联
    purchaser = relationship("Purchaser", backref="relations", lazy="joined")

    __table_args__ = (
        CheckConstraint(
            "rating IN ('S', 'A', 'B', 'C', 'D')",
            name="chk_client_relations_rating",
        ),
    )

    def __repr__(self):
        return f"<ClientRelation(id={self.id}, name={self.contact_name}, rating={self.rating})>"


class Purchaser(Base):
    """采购方（最小模型，仅用于外键关联）"""

    __tablename__ = "purchasers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    level = Column(String(20), nullable=False, default="地市公司")
    region = Column(String(50), nullable=False)

    def __repr__(self):
        return f"<Purchaser(id={self.id}, name={self.name})>"
