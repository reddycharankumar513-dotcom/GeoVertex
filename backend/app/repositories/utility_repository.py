"""Data access repository for underground infrastructure and subsurface utility intelligence."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import uuid
from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from shapely import wkt
from shapely.geometry import box

from app.models.utility import (
    SubsurfaceObservation,
    UtilityAsset,
    UtilityClash,
    UtilityCorridor,
    UtilityInspection,
    UtilityMaintenanceEvent,
    UtilityNetwork,
    UtilityNode,
    UtilitySegment,
    UtilitySeparationRule,
    UtilityStructure,
)


class UtilityRepository:
    """Repository handling CRUD, spatial querying, and analytics for subsurface utilities."""

    # 1. Networks
    async def create_network(self, db: AsyncSession, data: Dict[str, Any]) -> UtilityNetwork:
        network = UtilityNetwork(**data)
        db.add(network)
        await db.commit()
        await db.refresh(network)
        return network

    async def get_network(self, db: AsyncSession, network_id: uuid.UUID) -> Optional[UtilityNetwork]:
        stmt = select(UtilityNetwork).where(UtilityNetwork.id == network_id)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def list_networks(
        self,
        db: AsyncSession,
        jurisdiction_id: Optional[uuid.UUID] = None,
        utility_type: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[UtilityNetwork]:
        stmt = select(UtilityNetwork)
        if jurisdiction_id:
            stmt = stmt.where(UtilityNetwork.jurisdiction_id == jurisdiction_id)
        if utility_type:
            stmt = stmt.where(UtilityNetwork.utility_type == utility_type.upper())
        if status:
            stmt = stmt.where(UtilityNetwork.status == status.upper())
        stmt = stmt.order_by(desc(UtilityNetwork.created_at)).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # 2. Assets
    async def create_asset(self, db: AsyncSession, data: Dict[str, Any]) -> UtilityAsset:
        asset = UtilityAsset(**data)
        db.add(asset)
        await db.commit()
        await db.refresh(asset)
        return asset

    async def get_asset(self, db: AsyncSession, asset_id: uuid.UUID) -> Optional[UtilityAsset]:
        stmt = select(UtilityAsset).where(UtilityAsset.id == asset_id)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def get_asset_by_ref(
        self,
        db: AsyncSession,
        network_id: uuid.UUID,
        asset_reference: str,
    ) -> Optional[UtilityAsset]:
        stmt = select(UtilityAsset).where(
            UtilityAsset.network_id == network_id,
            UtilityAsset.asset_reference == asset_reference,
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    async def update_asset(
        self,
        db: AsyncSession,
        asset: UtilityAsset,
        updates: Dict[str, Any],
    ) -> UtilityAsset:
        for k, v in updates.items():
            setattr(asset, k, v)
        asset.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(asset)
        return asset

    async def list_assets(
        self,
        db: AsyncSession,
        network_id: Optional[uuid.UUID] = None,
        asset_type: Optional[str] = None,
        status: Optional[str] = None,
        review_status: Optional[str] = None,
        parcel_id: Optional[uuid.UUID] = None,
        building_id: Optional[uuid.UUID] = None,
        min_depth: Optional[float] = None,
        max_depth: Optional[float] = None,
        confidence: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[UtilityAsset]:
        stmt = select(UtilityAsset).options(selectinload(UtilityAsset.network))
        if network_id:
            stmt = stmt.where(UtilityAsset.network_id == network_id)
        if asset_type:
            stmt = stmt.where(UtilityAsset.asset_type == asset_type.upper())
        if status:
            stmt = stmt.where(UtilityAsset.status == status.upper())
        if review_status:
            stmt = stmt.where(UtilityAsset.review_status == review_status.upper())
        if parcel_id:
            stmt = stmt.where(UtilityAsset.parcel_id == parcel_id)
        if building_id:
            stmt = stmt.where(UtilityAsset.building_id == building_id)
        if min_depth is not None:
            stmt = stmt.where(UtilityAsset.depth >= min_depth)
        if max_depth is not None:
            stmt = stmt.where(UtilityAsset.depth <= max_depth)
        if confidence:
            stmt = stmt.where(UtilityAsset.confidence == confidence.upper())

        stmt = stmt.order_by(desc(UtilityAsset.created_at)).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def query_assets_by_bbox(
        self,
        db: AsyncSession,
        min_lon: float,
        min_lat: float,
        max_lon: float,
        max_lat: float,
        network_id: Optional[uuid.UUID] = None,
        utility_type: Optional[str] = None,
        limit: int = 200,
    ) -> List[UtilityAsset]:
        """Fetch assets intersecting a bounding box envelope."""
        stmt = select(UtilityAsset).options(selectinload(UtilityAsset.network))
        if network_id:
            stmt = stmt.where(UtilityAsset.network_id == network_id)
        if utility_type:
            stmt = stmt.join(UtilityNetwork).where(UtilityNetwork.utility_type == utility_type.upper())

        result = await db.execute(stmt.limit(1000))
        all_candidates = list(result.scalars().all())

        # Perform Shapely bounding box intersection filtering
        bbox_poly = box(min_lon, min_lat, max_lon, max_lat)
        filtered = []
        for asset in all_candidates:
            if not asset.geometry_wkt:
                continue
            try:
                g = wkt.loads(asset.geometry_wkt)
                if g.intersects(bbox_poly):
                    filtered.append(asset)
                    if len(filtered) >= limit:
                        break
            except Exception:
                continue
        return filtered

    # 3. Segments and Nodes
    async def create_segment(self, db: AsyncSession, data: Dict[str, Any]) -> UtilitySegment:
        segment = UtilitySegment(**data)
        db.add(segment)
        await db.commit()
        await db.refresh(segment)
        return segment

    async def get_segment_by_asset(
        self,
        db: AsyncSession,
        asset_id: uuid.UUID,
    ) -> Optional[UtilitySegment]:
        stmt = select(UtilitySegment).where(UtilitySegment.utility_asset_id == asset_id)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def list_segments_by_network(
        self,
        db: AsyncSession,
        network_id: uuid.UUID,
    ) -> List[UtilitySegment]:
        stmt = (
            select(UtilitySegment)
            .join(UtilityAsset, UtilitySegment.utility_asset_id == UtilityAsset.id)
            .where(UtilityAsset.network_id == network_id)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def create_node(self, db: AsyncSession, data: Dict[str, Any]) -> UtilityNode:
        node = UtilityNode(**data)
        db.add(node)
        await db.commit()
        await db.refresh(node)
        return node

    async def list_nodes_by_network(
        self,
        db: AsyncSession,
        network_id: uuid.UUID,
    ) -> List[UtilityNode]:
        stmt = select(UtilityNode).where(UtilityNode.network_id == network_id)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # 4. Structures & Corridors
    async def create_structure(self, db: AsyncSession, data: Dict[str, Any]) -> UtilityStructure:
        structure = UtilityStructure(**data)
        db.add(structure)
        await db.commit()
        await db.refresh(structure)
        return structure

    async def list_structures_by_asset(
        self,
        db: AsyncSession,
        asset_id: uuid.UUID,
    ) -> List[UtilityStructure]:
        stmt = select(UtilityStructure).where(UtilityStructure.utility_asset_id == asset_id)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def create_corridor(self, db: AsyncSession, data: Dict[str, Any]) -> UtilityCorridor:
        corridor = UtilityCorridor(**data)
        db.add(corridor)
        await db.commit()
        await db.refresh(corridor)
        return corridor

    async def list_corridors(
        self,
        db: AsyncSession,
        jurisdiction_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[UtilityCorridor]:
        stmt = select(UtilityCorridor)
        if jurisdiction_id:
            stmt = stmt.where(UtilityCorridor.jurisdiction_id == jurisdiction_id)
        stmt = stmt.order_by(desc(UtilityCorridor.created_at)).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # 5. Separation Rules
    async def create_separation_rule(
        self,
        db: AsyncSession,
        data: Dict[str, Any],
    ) -> UtilitySeparationRule:
        rule = UtilitySeparationRule(**data)
        db.add(rule)
        await db.commit()
        await db.refresh(rule)
        return rule

    async def get_separation_rule(
        self,
        db: AsyncSession,
        type_a: str,
        type_b: str,
        jurisdiction_id: Optional[uuid.UUID] = None,
    ) -> Optional[UtilitySeparationRule]:
        stmt = select(UtilitySeparationRule).where(
            or_(
                (UtilitySeparationRule.utility_type_a == type_a.upper()) & (UtilitySeparationRule.utility_type_b == type_b.upper()),
                (UtilitySeparationRule.utility_type_a == type_b.upper()) & (UtilitySeparationRule.utility_type_b == type_a.upper()),
            ),
            UtilitySeparationRule.status == "ACTIVE",
        )
        if jurisdiction_id:
            stmt = stmt.where(
                or_(
                    UtilitySeparationRule.jurisdiction_id == jurisdiction_id,
                    UtilitySeparationRule.jurisdiction_id == None,
                )
            )
        result = await db.execute(stmt)
        return result.scalars().first()

    async def list_separation_rules(
        self,
        db: AsyncSession,
        jurisdiction_id: Optional[uuid.UUID] = None,
        status: Optional[str] = "ACTIVE",
    ) -> List[UtilitySeparationRule]:
        stmt = select(UtilitySeparationRule)
        if status:
            stmt = stmt.where(UtilitySeparationRule.status == status.upper())
        if jurisdiction_id:
            stmt = stmt.where(
                or_(
                    UtilitySeparationRule.jurisdiction_id == jurisdiction_id,
                    UtilitySeparationRule.jurisdiction_id == None,
                )
            )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # 6. Clashes
    async def create_clash(self, db: AsyncSession, data: Dict[str, Any]) -> UtilityClash:
        clash = UtilityClash(**data)
        db.add(clash)
        await db.commit()
        await db.refresh(clash)
        return clash

    async def get_clash(self, db: AsyncSession, clash_id: uuid.UUID) -> Optional[UtilityClash]:
        stmt = select(UtilityClash).where(UtilityClash.id == clash_id)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def list_clashes(
        self,
        db: AsyncSession,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        asset_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[UtilityClash]:
        stmt = select(UtilityClash)
        if status:
            stmt = stmt.where(UtilityClash.status == status.upper())
        if severity:
            stmt = stmt.where(UtilityClash.severity == severity.upper())
        if asset_id:
            stmt = stmt.where(
                or_(
                    UtilityClash.asset_a_id == asset_id,
                    UtilityClash.asset_b_id == asset_id,
                )
            )
        stmt = stmt.order_by(desc(UtilityClash.created_at)).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def update_clash(
        self,
        db: AsyncSession,
        clash: UtilityClash,
        updates: Dict[str, Any],
    ) -> UtilityClash:
        for k, v in updates.items():
            setattr(clash, k, v)
        clash.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(clash)
        return clash

    # 7. Inspections & Maintenance
    async def create_inspection(self, db: AsyncSession, data: Dict[str, Any]) -> UtilityInspection:
        insp = UtilityInspection(**data)
        db.add(insp)
        await db.commit()
        await db.refresh(insp)
        return insp

    async def list_inspections_by_asset(
        self,
        db: AsyncSession,
        asset_id: uuid.UUID,
    ) -> List[UtilityInspection]:
        stmt = select(UtilityInspection).where(UtilityInspection.utility_asset_id == asset_id).order_by(desc(UtilityInspection.inspection_date))
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def create_maintenance_event(self, db: AsyncSession, data: Dict[str, Any]) -> UtilityMaintenanceEvent:
        event = UtilityMaintenanceEvent(**data)
        db.add(event)
        await db.commit()
        await db.refresh(event)
        return event

    async def list_maintenance_events_by_asset(
        self,
        db: AsyncSession,
        asset_id: uuid.UUID,
    ) -> List[UtilityMaintenanceEvent]:
        stmt = select(UtilityMaintenanceEvent).where(UtilityMaintenanceEvent.utility_asset_id == asset_id).order_by(desc(UtilityMaintenanceEvent.event_date))
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # 8. Subsurface Observations
    async def create_observation(self, db: AsyncSession, data: Dict[str, Any]) -> SubsurfaceObservation:
        obs = SubsurfaceObservation(**data)
        db.add(obs)
        await db.commit()
        await db.refresh(obs)
        return obs

    async def list_observations(self, db: AsyncSession, limit: int = 50) -> List[SubsurfaceObservation]:
        stmt = select(SubsurfaceObservation).order_by(desc(SubsurfaceObservation.created_at)).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # 9. KPI Dashboard Metrics
    async def get_metrics(self, db: AsyncSession, jurisdiction_id: Optional[uuid.UUID] = None) -> Dict[str, Any]:
        """Aggregate database-derived metrics for underground infrastructure."""
        # Networks count
        stmt_net = select(func.count(UtilityNetwork.id))
        if jurisdiction_id:
            stmt_net = stmt_net.where(UtilityNetwork.jurisdiction_id == jurisdiction_id)
        total_networks = (await db.execute(stmt_net)).scalar() or 0

        # Assets counts
        stmt_assets = select(func.count(UtilityAsset.id))
        stmt_active = select(func.count(UtilityAsset.id)).where(UtilityAsset.status == "ACTIVE")
        stmt_review = select(func.count(UtilityAsset.id)).where(UtilityAsset.review_status.in_(["CANDIDATE", "UNDER_REVIEW"]))
        stmt_verified = select(func.count(UtilityAsset.id)).where(UtilityAsset.review_status == "VERIFIED")
        stmt_unk_depth = select(func.count(UtilityAsset.id)).where(UtilityAsset.depth == None)
        stmt_low_conf = select(func.count(UtilityAsset.id)).where(UtilityAsset.confidence.in_(["LOW", "UNKNOWN"]))

        total_assets = (await db.execute(stmt_assets)).scalar() or 0
        active_assets = (await db.execute(stmt_active)).scalar() or 0
        requiring_review = (await db.execute(stmt_review)).scalar() or 0
        verified_assets = (await db.execute(stmt_verified)).scalar() or 0
        unknown_depth = (await db.execute(stmt_unk_depth)).scalar() or 0
        low_confidence = (await db.execute(stmt_low_conf)).scalar() or 0

        # Clashes counts
        stmt_clashes = select(func.count(UtilityClash.id))
        stmt_open_clashes = select(func.count(UtilityClash.id)).where(UtilityClash.status == "OPEN")
        total_clashes = (await db.execute(stmt_clashes)).scalar() or 0
        open_clashes = (await db.execute(stmt_open_clashes)).scalar() or 0

        return {
            "total_networks": total_networks,
            "total_assets": total_assets,
            "active_assets": active_assets,
            "candidates_requiring_review": requiring_review,
            "verified_assets": verified_assets,
            "total_clashes": total_clashes,
            "open_clashes": open_clashes,
            "unknown_depth_assets": unknown_depth,
            "low_confidence_assets": low_confidence,
        }
