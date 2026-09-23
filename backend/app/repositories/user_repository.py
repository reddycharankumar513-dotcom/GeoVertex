import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User, UserRole
from app.models.token import RefreshToken
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self):
        super().__init__(User)

    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        result = await db.execute(select(User).where(User.email == email.lower().strip()))
        return result.scalars().first()

    async def get_by_username(self, db: AsyncSession, username: str) -> Optional[User]:
        result = await db.execute(select(User).where(User.username == username.strip()))
        return result.scalars().first()

    async def get_by_username_or_email(self, db: AsyncSession, identifier: str) -> Optional[User]:
        clean_id = identifier.strip().lower()
        result = await db.execute(
            select(User).where(
                or_(
                    User.email == clean_id,
                    User.username == clean_id,
                )
            )
        )
        return result.scalars().first()

    async def get_users_filtered(
        self,
        db: AsyncSession,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[User], int]:
        query = select(User)
        if role:
            query = query.where(User.role == role)
        if is_active is not None:
            query = query.where(User.is_active == is_active)

        count_query = select(User.id)
        if role:
            count_query = count_query.where(User.role == role)
        if is_active is not None:
            count_query = count_query.where(User.is_active == is_active)

        count_res = await db.execute(count_query)
        total = len(count_res.scalars().all())

        result = await db.execute(query.order_by(User.created_at.desc()).offset(skip).limit(limit))
        return list(result.scalars().all()), total

    async def update_role(self, db: AsyncSession, user_id: uuid.UUID, new_role: UserRole) -> Optional[User]:
        user = await self.get_by_id(db, user_id)
        if not user:
            return None
        user.role = new_role.value
        await db.flush()
        await db.refresh(user)
        return user

    async def update_status(self, db: AsyncSession, user_id: uuid.UUID, is_active: bool) -> Optional[User]:
        user = await self.get_by_id(db, user_id)
        if not user:
            return None
        user.is_active = is_active
        await db.flush()
        await db.refresh(user)
        return user

    async def update_last_login(self, db: AsyncSession, user_id: uuid.UUID) -> None:
        await db.execute(
            update(User)
            .where(User.id == user_id)
            .values(last_login_at=datetime.now(timezone.utc))
        )
        await db.flush()

    # Refresh Token Management
    async def create_refresh_token(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> RefreshToken:
        token_record = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        db.add(token_record)
        await db.flush()
        return token_record

    async def get_refresh_token(self, db: AsyncSession, token_hash: str) -> Optional[RefreshToken]:
        result = await db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        return result.scalars().first()

    async def revoke_refresh_token(self, db: AsyncSession, token_hash: str) -> bool:
        result = await db.execute(
            update(RefreshToken)
            .where(RefreshToken.token_hash == token_hash)
            .values(revoked_at=datetime.now(timezone.utc))
        )
        await db.flush()
        return result.rowcount > 0

    async def revoke_all_user_tokens(self, db: AsyncSession, user_id: uuid.UUID) -> None:
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id)
            .values(revoked_at=datetime.now(timezone.utc))
        )
        await db.flush()


user_repository = UserRepository()
