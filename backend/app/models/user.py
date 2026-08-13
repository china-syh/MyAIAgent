from sqlalchemy import Column, String, Boolean
from app.models.base import Base, BaseModel


class User(Base, BaseModel):
    __tablename__ = "users"

    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    display_name = Column(String(100), default="")
    avatar_url = Column(String(500), default="")
    role = Column(String(20), default="user", nullable=False)  # user / admin