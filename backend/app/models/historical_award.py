"""
历史中标记录 SQLAlchemy ORM 模型
"""

from sqlalchemy import (
    Column, Integer, String, Numeric, Date, DateTime, Boolean,
    ForeignKey, Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class HistoricalAward(Base):
    """历史中标记录"""

    __tablename__ = "historical_awards"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    project_name = Column(String(500), nullable=False, comment="项目名称")
    purchaser_id = Column(Integer, ForeignKey("purchasers.id", ondelete="RESTRICT"), nullable=False, comment="采购方ID")
    winner_name = Column(String(300), nullable=False, comment="中标方名称")
    winner_type = Column(String(30), nullable=False, comment="中标方类型: 头部常客/中小公司/新进入者")
    bid_amount = Column(Numeric(12, 2), nullable=False, comment="中标金额（万元）")
    budget_amount = Column(Numeric(12, 2), default=0, comment="招标预算（万元）")
    discount_rate = Column(Numeric(6, 2), default=0, comment="折扣率（%）")
    project_category = Column(String(30), nullable=False, comment="项目类别")
    bid_open_date = Column(Date, nullable=False, comment="开标日期")
    contract_start = Column(Date, nullable=True, comment="合同开始日期")
    contract_end = Column(Date, nullable=True, comment="合同结束日期")
    is_continuous = Column(Boolean, nullable=False, default=False, comment="是否连续中标")
    continuous_count = Column(Integer, default=0, comment="连续中标次数")
    source_url = Column(String(1000), default="", comment="中标公告原始链接")
    data_source = Column(String(30), default="", comment="数据来源: b2b_10086(移动)/telecom(电信)/unicom(联通)/gd_zbtb/gd_ygp")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    purchaser = relationship("Purchaser", backref="historical_awards", lazy="joined")

    __table_args__ = (
        Index("ix_historical_awards_purchaser_id", "purchaser_id"),
        Index("ix_historical_awards_bid_open_date", "bid_open_date"),
        Index("ix_historical_awards_project_category", "project_category"),
        Index("ix_historical_awards_winner_name", "winner_name"),
        Index("ix_historical_awards_data_source", "data_source"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_name": self.project_name,
            "purchaser_id": self.purchaser_id,
            "winner_name": self.winner_name,
            "winner_type": self.winner_type,
            "bid_amount": float(self.bid_amount) if self.bid_amount else None,
            "budget_amount": float(self.budget_amount) if self.budget_amount else None,
            "discount_rate": float(self.discount_rate) if self.discount_rate else None,
            "project_category": self.project_category,
            "bid_open_date": self.bid_open_date.isoformat() if self.bid_open_date else None,
            "contract_start": self.contract_start.isoformat() if self.contract_start else None,
            "contract_end": self.contract_end.isoformat() if self.contract_end else None,
            "is_continuous": self.is_continuous,
            "continuous_count": self.continuous_count,
            "source_url": self.source_url or "",
            "data_source": self.data_source or "",
        }

    def __repr__(self):
        return f"<HistoricalAward(id={self.id}, project={self.project_name[:30]}...)>"
