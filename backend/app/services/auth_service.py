from app.core import settings, create_access_token, verify_token, get_password_hash, verify_password
from app.core.exceptions import UnauthorizedException, ValidationException
from app.repositories import UserRepository
from app.database import get_db
from app.schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta
from typing import Optional


class AuthService:
    def __init__(self, db: AsyncSession):
        self.repo = UserRepository(db)

    async def register(self, req: RegisterRequest) -> TokenResponse:
        existing = await self.repo.get_by_email(req.email)
        if existing:
            raise ValidationException("该邮箱已被注册")
        existing = await self.repo.get_by_username(req.username)
        if existing:
            raise ValidationException("该用户名已被使用")
        user = await self.repo.create(
            username=req.username,
            email=req.email,
            hashed_password=get_password_hash(req.password),
            display_name=req.display_name or req.username,
        )
        token = create_access_token({"sub": str(user.id), "role": user.role})
        return TokenResponse(access_token=token)

    async def login(self, req: LoginRequest) -> TokenResponse:
        user = await self.repo.get_by_username(req.username)
        if not user or not verify_password(req.password, user.hashed_password):
            raise UnauthorizedException("用户名或密码错误")
        token = create_access_token({"sub": str(user.id), "role": user.role})
        return TokenResponse(access_token=token)

    async def get_user(self, user_id: str) -> Optional[UserResponse]:
        from uuid import UUID
        user = await self.repo.get(UUID(user_id))
        if not user:
            return None
        return UserResponse.model_validate(user)