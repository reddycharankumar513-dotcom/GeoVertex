from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.dependencies.auth import get_current_user
from app.dependencies.db import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshTokenRequest, TokenResponse
from app.schemas.common import MessageResponse
from app.schemas.user import UserRegister, UserResponse
from app.services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication & Session"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new citizen account",
)
async def register(
    data: UserRegister,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    user = await auth_service.register_citizen(
        db=db,
        data=data,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate and receive JWT access/refresh token pair",
)
async def login(
    data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    access_token, refresh_token, user = await auth_service.authenticate(
        db=db,
        login_data=data,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh an expired access token using a valid refresh token",
)
async def refresh(
    data: RefreshTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    access_token, refresh_token, user = await auth_service.refresh_tokens(
        db=db,
        raw_refresh_token=data.refresh_token,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Invalidate user session and revoke refresh token",
)
async def logout(
    request: Request,
    data: RefreshTokenRequest = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    raw_token = data.refresh_token if data else None

    await auth_service.logout(
        db=db,
        user_id=current_user.id,
        raw_refresh_token=raw_token,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return MessageResponse(message="Successfully logged out")


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get profile and role details of current authenticated user",
)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
