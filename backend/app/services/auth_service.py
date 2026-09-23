import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.errors import (
    BadRequestException,
    ConflictException,
    InactiveUserException,
    UnauthorizedException,
)
from app.core.security import (
    create_access_token,
    generate_refresh_token_string,
    get_password_hash,
    hash_token,
    verify_password,
)
from app.models.user import User, UserRole
from app.repositories.user_repository import user_repository
from app.repositories.audit_repository import audit_repository
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import UserRegister, UserResponse


class AuthService:
    async def register_citizen(
        self,
        db: AsyncSession,
        data: UserRegister,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> User:
        # Check email uniqueness
        existing_email = await user_repository.get_by_email(db, data.email)
        if existing_email:
            raise ConflictException("An account with this email address already exists")

        # Check username uniqueness
        existing_username = await user_repository.get_by_username(db, data.username)
        if existing_username:
            raise ConflictException("This username is already taken")

        # Create user
        user = User(
            email=data.email.lower().strip(),
            username=data.username.strip(),
            full_name=data.full_name.strip(),
            phone=data.phone.strip() if data.phone else None,
            password_hash=get_password_hash(data.password),
            role=UserRole.CITIZEN.value,
            is_active=True,
            is_verified=False,
        )
        created_user = await user_repository.create(db, user)

        # Audit log event
        await audit_repository.log_event(
            db=db,
            action="USER_REGISTERED",
            entity_type="USER",
            entity_id=str(created_user.id),
            actor_user_id=created_user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"email": created_user.email, "role": created_user.role},
        )
        return created_user

    async def authenticate(
        self,
        db: AsyncSession,
        login_data: LoginRequest,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[str, str, User]:
        user = await user_repository.get_by_username_or_email(db, login_data.username_or_email)
        if not user or not verify_password(login_data.password, user.password_hash):
            if user:
                await audit_repository.log_event(
                    db=db,
                    action="LOGIN_FAILED",
                    entity_type="USER",
                    entity_id=str(user.id),
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={"reason": "INVALID_PASSWORD"},
                )
            raise UnauthorizedException("Invalid username, email, or password")

        if not user.is_active:
            await audit_repository.log_event(
                db=db,
                action="LOGIN_REJECTED_INACTIVE",
                entity_type="USER",
                entity_id=str(user.id),
                actor_user_id=user.id,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"reason": "ACCOUNT_DEACTIVATED"},
            )
            raise InactiveUserException("Your account is currently deactivated. Please contact an administrator.")

        # Update last login
        await user_repository.update_last_login(db, user.id)

        # Generate Access Token
        access_token = create_access_token(
            subject=str(user.id),
            role=user.role,
            email=user.email,
        )

        # Generate Refresh Token
        raw_refresh_token = generate_refresh_token_string()
        token_hash = hash_token(raw_refresh_token)
        refresh_expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        await user_repository.create_refresh_token(
            db=db,
            user_id=user.id,
            token_hash=token_hash,
            expires_at=refresh_expires_at,
        )

        # Audit log event
        await audit_repository.log_event(
            db=db,
            action="LOGIN_SUCCESS",
            entity_type="USER",
            entity_id=str(user.id),
            actor_user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"email": user.email, "role": user.role},
        )

        return access_token, raw_refresh_token, user

    async def refresh_tokens(
        self,
        db: AsyncSession,
        raw_refresh_token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[str, str, User]:
        token_hash = hash_token(raw_refresh_token)
        stored_token = await user_repository.get_refresh_token(db, token_hash)

        if not stored_token or not stored_token.is_valid:
            raise UnauthorizedException("Refresh token is invalid or has expired")

        user = await user_repository.get_by_id(db, stored_token.user_id)
        if not user or not user.is_active:
            raise InactiveUserException("Associated user account is deactivated or deleted")

        # Revoke old refresh token (Token Rotation)
        await user_repository.revoke_refresh_token(db, token_hash)

        # Issue new token pair
        new_access_token = create_access_token(
            subject=str(user.id),
            role=user.role,
            email=user.email,
        )
        new_raw_refresh = generate_refresh_token_string()
        new_token_hash = hash_token(new_raw_refresh)
        new_expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        await user_repository.create_refresh_token(
            db=db,
            user_id=user.id,
            token_hash=new_token_hash,
            expires_at=new_expires_at,
        )

        await audit_repository.log_event(
            db=db,
            action="TOKEN_REFRESHED",
            entity_type="USER",
            entity_id=str(user.id),
            actor_user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return new_access_token, new_raw_refresh, user

    async def logout(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        raw_refresh_token: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        if raw_refresh_token:
            token_hash = hash_token(raw_refresh_token)
            await user_repository.revoke_refresh_token(db, token_hash)
        else:
            await user_repository.revoke_all_user_tokens(db, user_id)

        await audit_repository.log_event(
            db=db,
            action="LOGOUT",
            entity_type="USER",
            entity_id=str(user_id),
            actor_user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )


auth_service = AuthService()
