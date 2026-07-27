"""
用户模型
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, func

from app.models.base import Base


class User(Base):
    """系统用户"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)
    password_salt = Column(String(32), nullable=False)
    display_name = Column(String(100), default="")
    email = Column(String(200), default="")
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"
