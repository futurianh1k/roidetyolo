"""
사용자 모델
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from enum import Enum


class UserRole(str, Enum):
    """사용자 역할"""
    ADMIN = "admin"
    USER = "user"


class User(BaseModel):
    """사용자 모델"""
    user_id: str
    username: str
    email: Optional[EmailStr] = None
    role: UserRole = UserRole.USER
    created_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = True


class UserCreate(BaseModel):
    """사용자 생성 요청"""
    username: str
    password: str
    email: Optional[EmailStr] = None
    role: UserRole = UserRole.USER


class UserLogin(BaseModel):
    """로그인 요청"""
    username: str
    password: str


class Token(BaseModel):
    """JWT 토큰 응답"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: User


class TokenData(BaseModel):
    """토큰 데이터"""
    username: Optional[str] = None
    role: Optional[str] = None
