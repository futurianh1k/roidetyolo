"""
JWT 인증 API 엔드포인트
"""
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from typing import Dict

from ..models.user import (
    UserCreate, UserLogin, UserResponse, TokenResponse, UserRole
)
from ..core.security import (
    create_access_token, verify_password, get_current_user, get_current_admin
)
from ..services.redis_session_manager import redis_session_manager

router = APIRouter(prefix="/auth", tags=["authentication"])


# 임시 사용자 데이터베이스 (실제 환경에서는 PostgreSQL 등 사용)
USERS_DB: Dict[str, dict] = {
    "admin": {
        "username": "admin",
        "email": "admin@example.com",
        "full_name": "System Administrator",
        "hashed_password": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYvLcLqnq5W",  # admin123
        "role": UserRole.ADMIN,
        "is_active": True
    },
    "operator": {
        "username": "operator",
        "email": "operator@example.com",
        "full_name": "System Operator",
        "hashed_password": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYvLcLqnq5W",  # admin123
        "role": UserRole.OPERATOR,
        "is_active": True
    }
}


@router.post("/login", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    로그인 - JWT 토큰 발급
    
    기본 계정:
    - admin / admin123 (관리자)
    - operator / admin123 (운영자)
    """
    user = USERS_DB.get(form_data.username)
    
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # JWT 토큰 생성
    access_token = create_access_token(
        data={
            "sub": user["username"],
            "role": user["role"],
            "email": user.get("email", "")
        }
    )
    
    # Redis에 세션 정보 저장
    await redis_session_manager.store_user_session(
        username=user["username"],
        token=access_token,
        user_data={
            "username": user["username"],
            "email": user.get("email", ""),
            "full_name": user.get("full_name", ""),
            "role": user["role"]
        }
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "username": user["username"],
            "email": user.get("email", ""),
            "full_name": user.get("full_name", ""),
            "role": user["role"]
        }
    }


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """로그아웃 - 세션 제거"""
    await redis_session_manager.remove_user_session(current_user["username"])
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """현재 로그인한 사용자 정보"""
    return current_user


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(current_user: dict = Depends(get_current_user)):
    """토큰 갱신"""
    # 새 토큰 생성
    new_token = create_access_token(
        data={
            "sub": current_user["username"],
            "role": current_user["role"],
            "email": current_user.get("email", "")
        }
    )
    
    # Redis 세션 업데이트
    await redis_session_manager.store_user_session(
        username=current_user["username"],
        token=new_token,
        user_data=current_user
    )
    
    return {
        "access_token": new_token,
        "token_type": "bearer",
        "user": current_user
    }


@router.get("/users", response_model=list)
async def list_users(current_admin: dict = Depends(get_current_admin)):
    """사용자 목록 조회 (관리자 전용)"""
    users_list = []
    for username, user_data in USERS_DB.items():
        users_list.append({
            "username": user_data["username"],
            "email": user_data.get("email", ""),
            "full_name": user_data.get("full_name", ""),
            "role": user_data["role"],
            "is_active": user_data.get("is_active", True)
        })
    return users_list


@router.get("/sessions/active")
async def list_active_sessions(current_admin: dict = Depends(get_current_admin)):
    """활성 세션 목록 (관리자 전용)"""
    sessions = await redis_session_manager.get_all_user_sessions()
    return {
        "active_sessions": len(sessions),
        "sessions": sessions
    }
