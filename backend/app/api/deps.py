from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.core import verify_token, UnauthorizedException
from app.repositories import UserRepository

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    payload = verify_token(credentials.credentials)
    if not payload:
        raise UnauthorizedException("无效的访问令牌")
    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException("令牌格式错误")
    repo = UserRepository(db)
    from uuid import UUID
    user = await repo.get(UUID(user_id))
    if not user:
        raise UnauthorizedException("用户不存在")
    return user


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_db),
):
    if not credentials:
        return None
    try:
        return await get_current_user(credentials, db)
    except Exception:
        return None