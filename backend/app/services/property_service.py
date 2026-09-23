import uuid
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import ConflictException, NotFoundException
from app.models.property import Property
from app.repositories.audit_repository import audit_repository
from app.repositories.parcel_repository import parcel_repository
from app.repositories.property_repository import property_repository
from app.schemas.property import PropertyCreate, PropertyUpdate


class PropertyService:
    """Service layer orchestrating Property records and parcel relationships."""

    async def create_property(
        self,
        db: AsyncSession,
        data: PropertyCreate,
        actor_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Property:
        # Verify parcel exists
        parcel = await parcel_repository.get_by_id(db, data.parcel_id)
        if not parcel:
            raise NotFoundException(f"Associated parcel with ID '{data.parcel_id}' does not exist")

        # Check unique reference
        existing = await property_repository.get_by_reference(db, data.property_reference)
        if existing:
            raise ConflictException(f"Property with reference '{data.property_reference}' already exists")

        prop = Property(
            parcel_id=data.parcel_id,
            property_reference=data.property_reference.strip(),
            property_type=data.property_type.upper(),
            status=data.status.upper(),
            address=data.address.strip(),
            locality=data.locality.strip() if data.locality else None,
            postal_code=data.postal_code.strip() if data.postal_code else None,
            description=data.description,
            created_by=actor_id,
            updated_by=actor_id,
        )
        created = await property_repository.create(db, prop)

        await audit_repository.log_event(
            db=db,
            action="PROPERTY_CREATED",
            entity_type="PROPERTY",
            entity_id=str(created.id),
            actor_user_id=actor_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={
                "property_reference": created.property_reference,
                "parcel_id": str(created.parcel_id),
                "property_type": created.property_type,
                "address": created.address,
            },
        )
        return created

    async def get_property(self, db: AsyncSession, id: uuid.UUID) -> Property:
        prop = await property_repository.get_with_parcel(db, id)
        if not prop:
            raise NotFoundException(f"Property with ID '{id}' not found")
        return prop

    async def update_property(
        self,
        db: AsyncSession,
        id: uuid.UUID,
        data: PropertyUpdate,
        actor_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Property:
        prop = await property_repository.get_by_id(db, id)
        if not prop:
            raise NotFoundException(f"Property with ID '{id}' not found")

        old_details: Dict[str, Any] = {
            "property_reference": prop.property_reference,
            "status": prop.status,
            "address": prop.address,
        }

        if data.property_reference and data.property_reference.strip() != prop.property_reference:
            existing = await property_repository.get_by_reference(db, data.property_reference)
            if existing and existing.id != id:
                raise ConflictException(f"Property with reference '{data.property_reference}' already exists")
            prop.property_reference = data.property_reference.strip()

        if data.parcel_id and data.parcel_id != prop.parcel_id:
            parcel = await parcel_repository.get_by_id(db, data.parcel_id)
            if not parcel:
                raise NotFoundException(f"Associated parcel with ID '{data.parcel_id}' does not exist")
            prop.parcel_id = data.parcel_id

        if data.property_type:
            prop.property_type = data.property_type.upper()
        if data.status:
            prop.status = data.status.upper()
        if data.address:
            prop.address = data.address.strip()
        if data.locality is not None:
            prop.locality = data.locality.strip() if data.locality else None
        if data.postal_code is not None:
            prop.postal_code = data.postal_code.strip() if data.postal_code else None
        if data.description is not None:
            prop.description = data.description

        prop.updated_by = actor_id
        await db.flush()
        await db.refresh(prop)

        await audit_repository.log_event(
            db=db,
            action="PROPERTY_UPDATED",
            entity_type="PROPERTY",
            entity_id=str(prop.id),
            actor_user_id=actor_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"old": old_details, "new": {"property_reference": prop.property_reference, "status": prop.status}},
        )
        return prop

    async def delete_property(
        self,
        db: AsyncSession,
        id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> bool:
        prop = await property_repository.get_by_id(db, id)
        if not prop:
            raise NotFoundException(f"Property with ID '{id}' not found")

        ref = prop.property_reference
        success = await property_repository.delete_by_id(db, id)
        if success:
            await audit_repository.log_event(
                db=db,
                action="PROPERTY_DELETED",
                entity_type="PROPERTY",
                entity_id=str(id),
                actor_user_id=actor_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"property_reference": ref},
            )
        return success

    async def list_properties(
        self,
        db: AsyncSession,
        parcel_id: Optional[uuid.UUID] = None,
        property_type: Optional[str] = None,
        status: Optional[str] = None,
        query: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Property], int]:
        return await property_repository.search_and_filter(
            db=db,
            parcel_id=parcel_id,
            property_type=property_type,
            status=status,
            query=query,
            skip=skip,
            limit=limit,
        )


property_service = PropertyService()
