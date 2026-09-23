import uuid
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import BadRequestException, ConflictException, NotFoundException
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.repositories.user_repository import user_repository
from app.repositories.audit_repository import audit_repository
from app.schemas.user import UserCreate, UserRoleUpdate, UserStatusUpdate


class UserService:
    async def create_user(
        self,
        db: AsyncSession,
        data: UserCreate,
        actor_id: uuid.UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> User:
        if await user_repository.get_by_email(db, data.email):
            raise ConflictException("A user with this email address already exists")
        if await user_repository.get_by_username(db, data.username):
            raise ConflictException("A user with this username already exists")

        user = User(
            email=data.email.lower().strip(),
            username=data.username.strip(),
            full_name=data.full_name.strip(),
            phone=data.phone.strip() if data.phone else None,
            password_hash=get_password_hash(data.password),
            role=data.role.value,
            organization_id=data.organization_id,
            jurisdiction_id=data.jurisdiction_id,
            is_active=True,
            is_verified=True,
        )
        created = await user_repository.create(db, user)

        await audit_repository.log_event(
            db=db,
            action="USER_CREATED",
            entity_type="USER",
            entity_id=str(created.id),
            actor_user_id=actor_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"email": created.email, "role": created.role},
        )
        return created

    async def get_user_by_id(self, db: AsyncSession, user_id: uuid.UUID) -> User:
        user = await user_repository.get_by_id(db, user_id)
        if not user:
            raise NotFoundException("User not found")
        return user

    async def list_users(
        self,
        db: AsyncSession,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[User], int]:
        return await user_repository.get_users_filtered(
            db=db,
            role=role,
            is_active=is_active,
            skip=skip,
            limit=limit,
        )

    async def update_role(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        data: UserRoleUpdate,
        actor_id: uuid.UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> User:
        user = await self.get_user_by_id(db, user_id)
        old_role = user.role

        updated_user = await user_repository.update_role(db, user_id, data.role)

        await audit_repository.log_event(
            db=db,
            action="ROLE_CHANGED",
            entity_type="USER",
            entity_id=str(user_id),
            actor_user_id=actor_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"old_role": old_role, "new_role": data.role.value},
        )
        return updated_user

    async def update_status(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        data: UserStatusUpdate,
        actor_id: uuid.UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> User:
        if user_id == actor_id and not data.is_active:
            raise BadRequestException("Administrators cannot deactivate their own active account")

        user = await self.get_user_by_id(db, user_id)
        old_status = user.is_active

        updated_user = await user_repository.update_status(db, user_id, data.is_active)

        action = "USER_ACTIVATED" if data.is_active else "USER_DEACTIVATED"
        await audit_repository.log_event(
            db=db,
            action=action,
            entity_type="USER",
            entity_id=str(user_id),
            actor_user_id=actor_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"old_status": old_status, "new_status": data.is_active},
        )

        # If deactivated, revoke all active refresh tokens immediately
        if not data.is_active:
            await user_repository.revoke_all_user_tokens(db, user_id)

        return updated_user


user_service = UserService()
