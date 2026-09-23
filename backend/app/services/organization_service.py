import uuid
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import ConflictException, NotFoundException
from app.models.organization import Organization
from app.models.jurisdiction import Jurisdiction
from app.repositories.organization_repository import (
    organization_repository,
    jurisdiction_repository,
)
from app.repositories.audit_repository import audit_repository
from app.schemas.organization import OrganizationCreate, OrganizationUpdate
from app.schemas.jurisdiction import JurisdictionCreate, JurisdictionUpdate


class OrganizationService:
    async def create_organization(
        self,
        db: AsyncSession,
        data: OrganizationCreate,
        actor_id: uuid.UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Organization:
        if await organization_repository.get_by_name(db, data.name):
            raise ConflictException("An organization with this name already exists")
        if await organization_repository.get_by_code(db, data.code):
            raise ConflictException("An organization with this code already exists")

        org = Organization(
            name=data.name.strip(),
            code=data.code.upper().strip(),
            type=data.type.strip(),
            is_active=True,
        )
        created = await organization_repository.create(db, org)

        await audit_repository.log_event(
            db=db,
            action="ORGANIZATION_CREATED",
            entity_type="ORGANIZATION",
            entity_id=str(created.id),
            actor_user_id=actor_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"name": created.name, "code": created.code},
        )
        return created

    async def list_organizations(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Organization], int]:
        total = await organization_repository.count(db)
        items = await organization_repository.get_all(db, skip=skip, limit=limit)
        return items, total

    async def create_jurisdiction(
        self,
        db: AsyncSession,
        data: JurisdictionCreate,
        actor_id: uuid.UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Jurisdiction:
        # Check organization exists
        org = await organization_repository.get_by_id(db, data.organization_id)
        if not org:
            raise NotFoundException("Parent organization not found")

        # Check code uniqueness
        if await jurisdiction_repository.get_by_code(db, data.code):
            raise ConflictException("A jurisdiction with this code already exists")

        # Convert boundary_geojson to boundary_wkt if provided
        boundary_wkt = data.boundary_wkt
        if data.boundary_geojson:
            try:
                geom = GeometryEngine.parse_geometry(data.boundary_geojson, source_srid=data.srid)
                boundary_wkt = GeometryEngine.to_wkt(geom)
            except Exception as e:
                raise BadRequestException(f"Invalid boundary GeoJSON: {str(e)}")

        jurisdiction = Jurisdiction(
            organization_id=data.organization_id,
            parent_jurisdiction_id=data.parent_jurisdiction_id,
            name=data.name.strip(),
            code=data.code.upper().strip(),
            level=data.level.upper().strip(),
            description=data.description,
            srid=data.srid,
            boundary=boundary_wkt,
            boundary_wkt=boundary_wkt,
            is_active=True,
        )
        created = await jurisdiction_repository.create(db, jurisdiction)

        await audit_repository.log_event(
            db=db,
            action="JURISDICTION_CREATED",
            entity_type="JURISDICTION",
            entity_id=str(created.id),
            actor_user_id=actor_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"name": created.name, "code": created.code, "level": created.level},
        )
        return created

    async def get_jurisdiction(self, db: AsyncSession, id: uuid.UUID) -> Jurisdiction:
        jur = await jurisdiction_repository.get_by_id(db, id)
        if not jur:
            raise NotFoundException(f"Jurisdiction with ID '{id}' not found")
        return jur

    async def update_jurisdiction(
        self,
        db: AsyncSession,
        id: uuid.UUID,
        data: JurisdictionUpdate,
        actor_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Jurisdiction:
        jur = await jurisdiction_repository.get_by_id(db, id)
        if not jur:
            raise NotFoundException(f"Jurisdiction with ID '{id}' not found")

        old_details = {"name": jur.name, "code": jur.code, "is_active": jur.is_active}

        if data.code and data.code.strip() != jur.code:
            existing = await jurisdiction_repository.get_by_code(db, data.code)
            if existing and existing.id != id:
                raise ConflictException("A jurisdiction with this code already exists")
            jur.code = data.code.upper().strip()

        if data.name:
            jur.name = data.name.strip()
        if data.level:
            jur.level = data.level.upper().strip()
        if data.description is not None:
            jur.description = data.description
        if data.parent_jurisdiction_id is not None:
            jur.parent_jurisdiction_id = data.parent_jurisdiction_id
        if data.srid is not None:
            jur.srid = data.srid
        if data.is_active is not None:
            jur.is_active = data.is_active

        if data.boundary_geojson:
            try:
                geom = GeometryEngine.parse_geometry(data.boundary_geojson, source_srid=jur.srid)
                wkt_str = GeometryEngine.to_wkt(geom)
                jur.boundary = wkt_str
                jur.boundary_wkt = wkt_str
            except Exception as e:
                raise BadRequestException(f"Invalid boundary GeoJSON: {str(e)}")
        elif data.boundary_wkt is not None:
            jur.boundary = data.boundary_wkt
            jur.boundary_wkt = data.boundary_wkt

        await db.flush()
        await db.refresh(jur)

        await audit_repository.log_event(
            db=db,
            action="JURISDICTION_UPDATED",
            entity_type="JURISDICTION",
            entity_id=str(jur.id),
            actor_user_id=actor_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"old": old_details, "new": {"name": jur.name, "code": jur.code, "is_active": jur.is_active}},
        )
        return jur

    async def list_jurisdictions(
        self,
        db: AsyncSession,
        organization_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Jurisdiction], int]:
        if organization_id:
            items = await jurisdiction_repository.get_by_organization(db, organization_id)
            return items, len(items)
        total = await jurisdiction_repository.count(db)
        items = await jurisdiction_repository.get_all(db, skip=skip, limit=limit)
        return items, total


organization_service = OrganizationService()
