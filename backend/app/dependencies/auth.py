import uuid
from typing import Callable, List, Optional
from fastapi import Depends, Header, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import ForbiddenException, InactiveUserException, UnauthorizedException
from app.core.security import decode_access_token
from app.dependencies.db import get_db
from app.models.user import User, UserRole
from app.repositories.user_repository import user_repository

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,
)


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extracts and verifies JWT bearer token, fetching the authenticated active user."""
    raw_token = token
    if not raw_token and authorization and authorization.startswith("Bearer "):
        raw_token = authorization.split("Bearer ", 1)[1].strip()

    if not raw_token:
        raise UnauthorizedException("Authentication token is missing")

    try:
        payload = decode_access_token(raw_token)
    except ValueError as e:
        raise UnauthorizedException(f"Invalid authentication token: {str(e)}")

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise UnauthorizedException("Malformed token claims")

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise UnauthorizedException("Invalid user identity format in token")

    user = await user_repository.get_by_id(db, user_uuid)
    if not user:
        raise UnauthorizedException("User account does not exist")

    if not user.is_active:
        raise InactiveUserException("Your account is deactivated. Access denied.")

    return user


def require_role(*allowed_roles: UserRole) -> Callable:
    """Dependency factory enforcing server-side Role-Based Access Control (RBAC)."""
    allowed_role_values = [r.value if isinstance(r, UserRole) else str(r) for r in allowed_roles]

    async def role_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role not in allowed_role_values:
            raise ForbiddenException(
                f"Access denied. Requires one of roles: {', '.join(allowed_role_values)}"
            )
        return current_user

    return role_checker


# Specific role shorthand dependencies
require_admin = require_role(UserRole.ADMIN)
require_officer_or_admin = require_role(UserRole.ADMIN, UserRole.GOVERNMENT_OFFICER)
require_surveyor_or_admin = require_role(UserRole.ADMIN, UserRole.SURVEYOR)
require_editor = require_role(UserRole.ADMIN, UserRole.GOVERNMENT_OFFICER, UserRole.SURVEYOR)

