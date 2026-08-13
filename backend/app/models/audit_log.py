from sqlalchemy import Column, String, Text, JSON
from sqlalchemy.types import Uuid
from app.models.base import Base, BaseModel


class AuditLog(Base, BaseModel):
    """审计日志模型"""
    __tablename__ = "audit_logs"

    user_id = Column(Uuid(), index=True, nullable=True)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(100), nullable=False, index=True)
    resource_id = Column(String(255), nullable=True, index=True)
    details = Column(JSON, nullable=True, default=dict)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)