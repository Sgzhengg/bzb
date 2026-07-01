"""
招标公告 SQLAlchemy ORM 模型（最小模型，用于客情关联提醒）
"""

from sqlalchemy import (
    Column, Integer, String, Text, Date, DateTime, Numeric,
    ForeignKey, JSON,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class Announcement(Base):
    """
    招标公告

    字段对齐「致合项目查询汇总」Excel 模板：
      日期 / 招标单位 / 省份 / 地市 / 项目名称 / 种类 / 预算金额 / 网址 /
      报名截止日期 / 截止时间 / 投标日期 / 投标时间 / 报名费 / 保证金 / 备注
    """

    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)

    # ── 模板核心字段 ──
    announce_date = Column(Date, nullable=False, comment="日期（公告发布日期）")
    industry = Column(String(200), default="", comment="招标单位")
    province = Column(String(50), default="", comment="省份")
    city = Column(String(50), default="", comment="地市")
    title = Column(String(500), nullable=False, comment="项目名称")
    project_category = Column(String(30), nullable=False, comment="种类（项目类别）")
    budget = Column(Numeric(12, 2), default=0, comment="预算金额（万元）")
    source_url = Column(String(1000), comment="网址")

    # ── 原始 deadline 拆分 ──
    deadline = Column(DateTime, nullable=False, comment="报名截止日期")
    deadline_time = Column(String(10), default="", comment="截止时间")

    bid_date = Column(Date, nullable=True, comment="投标日期")
    bid_time = Column(String(10), default="", comment="投标时间")

    # ── 费用与保证金 ──
    registration_fee = Column(Numeric(10, 2), default=0, comment="报名费（元）")
    deposit = Column(Numeric(12, 2), default=0, comment="保证金（元）")

    # ── 备注 ──
    remark = Column(Text, default="", comment="备注")

    # ── 原有辅助字段 ──
    purchaser_id = Column(Integer, ForeignKey("purchasers.id", ondelete="RESTRICT"), nullable=True, comment="采购方ID")
    purchaser_level = Column(String(50), nullable=True, comment="采购方层级")
    procurement_method = Column(String(30), nullable=False, default="公开招标", comment="采购方式")
    qualification_requirements = Column(Text, comment="资格要求")
    score_weight = Column(JSON, comment="评分权重（JSON）")

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # 关联
    purchaser = relationship("Purchaser", backref="announcements", lazy="joined")

    def __repr__(self):
        return f"<Announcement(id={self.id}, title={self.title[:30]}...)>"
