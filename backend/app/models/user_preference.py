"""
用户偏好模型 — 存储用户的关注方向和筛选条件
"""

from sqlalchemy import Column, Integer, String, Float, Text, DateTime, func
from app.models.base import Base


class UserPreference(Base):
    """
    用户偏好设置。

    存储用户关注的招标赛道、预算偏好、最低评分等。
    只有一个默认用户（id=1），后续可扩展多用户。
    """

    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, default=1)
    focus_description = Column(Text, default="", comment="关注方向自然语言描述")
    preferred_categories = Column(Text, default="", comment="偏好赛道，JSON数组字符串")
    min_budget = Column(Float, default=0, comment="最低预算过滤（万元）")
    min_score = Column(Float, default=0, comment="最低机会评分（0-100）")
    llm_enabled = Column(String(10), default="true", comment="LLM是否启用")
    llm_api_key = Column(Text, default="", comment="LLM API Key")
    llm_model = Column(String(100), default="deepseek-chat", comment="LLM模型")
    llm_base_url = Column(Text, default="https://api.deepseek.com/v1", comment="LLM API地址")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def to_dict(self) -> dict:
        import json
        return {
            "id": self.id,
            "focus_description": self.focus_description or "",
            "preferred_categories": self._parse_categories(),
            "min_budget": self.min_budget or 0,
            "min_score": self.min_score or 0,
            "llm_enabled": self.llm_enabled or "true",
            "llm_api_key": self.llm_api_key or "",
            "llm_model": self.llm_model or "deepseek-chat",
            "llm_base_url": self.llm_base_url or "https://api.deepseek.com/v1",
            "updated_at": str(self.updated_at) if self.updated_at else "",
        }

    def _parse_categories(self) -> list:
        """解析 preferred_categories JSON 字符串为列表。"""
        import json
        if not self.preferred_categories:
            return []
        try:
            return json.loads(self.preferred_categories)
        except (json.JSONDecodeError, TypeError):
            return []

    @classmethod
    def build_categories(cls, categories: list) -> str:
        """将列表序列化为 JSON 字符串。"""
        import json
        return json.dumps(categories or [], ensure_ascii=False)
