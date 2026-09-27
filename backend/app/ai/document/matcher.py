from typing import Any, Dict, List, Optional
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.parcel import Parcel
from app.models.property import Property
from app.models.building import BuildingFootprint
from app.models.unit import PropertyUnit
from app.models.document import DocumentEntityLink, LinkMethod


class DocumentCadastralMatcher:
    """Matches extracted document identifiers against official GeoVertex cadastral entities."""

    async def find_candidate_links(
        self,
        db: AsyncSession,
        document_id: str,
        extracted_fields: Dict[str, str],
        jurisdiction_id: Optional[str] = None,
    ) -> List[DocumentEntityLink]:
        candidates: List[DocumentEntityLink] = []

        parcel_num = extracted_fields.get("parcel_number") or extracted_fields.get("survey_number")
        prop_ref = extracted_fields.get("property_reference")
        bld_ref = extracted_fields.get("building_number")
        unit_ref = extracted_fields.get("unit_number")

        # 1. Match against Parcels
        if parcel_num:
            clean_p = parcel_num.strip()
            stmt = select(Parcel).where(
                or_(
                    Parcel.parcel_number.ilike(f"%{clean_p}%"),
                    Parcel.parcel_code.ilike(f"%{clean_p}%"),
                )
            )
            if jurisdiction_id:
                stmt = stmt.where(Parcel.jurisdiction_id == jurisdiction_id)

            res = await db.execute(stmt.limit(5))
            matched_parcels = res.scalars().all()

            for p in matched_parcels:
                score = 1.0 if (p.parcel_number == clean_p or p.parcel_code == clean_p) else 0.80
                candidates.append(DocumentEntityLink(
                    document_id=document_id,
                    entity_type="PARCEL",
                    entity_id=str(p.id),
                    link_method=LinkMethod.RULE_BASED.value,
                    match_score=score,
                    match_reason=f"Matched parcel number '{parcel_num}' with cadastral parcel {p.parcel_number} ({p.parcel_code})",
                    status="CANDIDATE",
                ))

        # 2. Match against Properties
        if prop_ref:
            clean_pr = prop_ref.strip()
            stmt = select(Property).where(
                or_(
                    Property.property_number.ilike(f"%{clean_pr}%"),
                    Property.title_number.ilike(f"%{clean_pr}%"),
                )
            )
            res = await db.execute(stmt.limit(5))
            for pr in res.scalars().all():
                candidates.append(DocumentEntityLink(
                    document_id=document_id,
                    entity_type="PROPERTY",
                    entity_id=str(pr.id),
                    link_method=LinkMethod.RULE_BASED.value,
                    match_score=0.90,
                    match_reason=f"Matched property reference '{prop_ref}' with registered property {pr.property_number}",
                    status="CANDIDATE",
                ))

        # 3. Match against Buildings
        if bld_ref:
            clean_b = bld_ref.strip()
            stmt = select(BuildingFootprint).where(
                or_(
                    BuildingFootprint.building_reference.ilike(f"%{clean_b}%"),
                    BuildingFootprint.name.ilike(f"%{clean_b}%"),
                )
            )
            res = await db.execute(stmt.limit(5))
            for b in res.scalars().all():
                candidates.append(DocumentEntityLink(
                    document_id=document_id,
                    entity_type="BUILDING",
                    entity_id=str(b.id),
                    link_method=LinkMethod.RULE_BASED.value,
                    match_score=0.85,
                    match_reason=f"Matched building reference '{bld_ref}' with building {b.building_reference}",
                    status="CANDIDATE",
                ))

        # 4. Match against Property Units
        if unit_ref:
            clean_u = unit_ref.strip()
            stmt = select(PropertyUnit).where(PropertyUnit.unit_number.ilike(f"%{clean_u}%"))
            res = await db.execute(stmt.limit(5))
            for u in res.scalars().all():
                candidates.append(DocumentEntityLink(
                    document_id=document_id,
                    entity_type="UNIT",
                    entity_id=str(u.id),
                    link_method=LinkMethod.RULE_BASED.value,
                    match_score=0.85,
                    match_reason=f"Matched unit reference '{unit_ref}' with unit {u.unit_number}",
                    status="CANDIDATE",
                ))

        return candidates


document_cadastral_matcher = DocumentCadastralMatcher()
