import uuid
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.utils.pagination import paginate, calc_pages

logger = logging.getLogger(__name__)


class AuditService:
    """审计日志服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        action: str,
        resource_type: str,
        resource_id: str,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """记录审计日志，异步写入数据库"""
        audit_log = AuditLog(
            id=uuid.uuid4(),
            user_id=uuid.UUID(user_id) if user_id else None,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(audit_log)
        await self.db.commit()
        await self.db.refresh(audit_log)
        logger.debug(
            f"审计日志已记录: action={action}, resource_type={resource_type}, "
            f"resource_id={resource_id}, user_id={user_id}"
        )
        return audit_log

    async def fire_and_forget(
        self,
        action: str,
        resource_type: str,
        resource_id: str,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """以 fire-and-forget 方式异步记录审计日志，不阻塞主流程。

        调用方可直接 await 或使用 asyncio.create_task() 触发。
        """
        import asyncio
        asyncio.ensure_future(
            self.log(
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                user_id=user_id,
                details=details,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        )

    async def query(
        self,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """查询审计日志，返回分页结果"""
        conditions = []

        if user_id:
            conditions.append(AuditLog.user_id == uuid.UUID(user_id))
        if action:
            conditions.append(AuditLog.action == action)
        if resource_type:
            conditions.append(AuditLog.resource_type == resource_type)
        if start_time:
            conditions.append(AuditLog.created_at >= start_time)
        if end_time:
            conditions.append(AuditLog.created_at <= end_time)

        # 查询总数
        count_query = select(func.count(AuditLog.id))
        if conditions:
            count_query = count_query.where(*conditions)
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # 查询分页数据
        skip, limit = paginate(page, page_size)
        data_query = select(AuditLog)
        if conditions:
            data_query = data_query.where(*conditions)
        data_query = data_query.order_by(desc(AuditLog.created_at)).offset(skip).limit(limit)

        result = await self.db.execute(data_query)
        items = result.scalars().all()

        return {
            "items": [
                {
                    "id": str(item.id),
                    "user_id": str(item.user_id) if item.user_id else None,
                    "action": item.action,
                    "resource_type": item.resource_type,
                    "resource_id": item.resource_id,
                    "details": item.details,
                    "ip_address": item.ip_address,
                    "user_agent": item.user_agent,
                    "created_at": item.created_at.isoformat() if item.created_at else None,
                }
                for item in items
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": calc_pages(total, page_size),
        }