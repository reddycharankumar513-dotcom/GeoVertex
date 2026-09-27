"""Service orchestrating underground infrastructure, network topology, clash detection, and verification."""

from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional, Tuple
import uuid
from shapely import wkt
from shapely.geometry import mapping
from sqlalchemy.ext.asyncio import AsyncSession

from app.gis.utility.depth_elevation import DepthElevationCalculator
from app.gis.utility.spatial_relations import UtilitySpatialRelationshipAnalyzer
from app.gis.utility.network_topology import UtilityNetworkTopologyEngine
from app.gis.utility.clash_detector import UtilityClashDetector
from app.models.utility import (
    UtilityAsset,
    UtilityClash,
    UtilityCorridor,
    UtilityInspection,
    UtilityMaintenanceEvent,
    UtilityNetwork,
    UtilityNode,
    UtilitySegment,
    UtilitySeparationRule,
)
from app.repositories.audit_repository import AuditRepository
from app.repositories.utility_repository import UtilityRepository
from app.repositories.parcel_repository import ParcelRepository
from app.repositories.building_repository import BuildingRepository


class UtilityService:
    """Business logic and spatial intelligence for underground utility networks."""

    def __init__(self):
        self.repo = UtilityRepository()
        self.audit_repo = AuditRepository()
        self.parcel_repo = ParcelRepository()
        self.building_repo = BuildingRepository()

    # 1. Networks
    async def create_network(
        self,
        db: AsyncSession,
        data: Dict[str, Any],
        actor_id: Optional[uuid.UUID] = None,
    ) -> UtilityNetwork:
        network = await self.repo.create_network(db, data)
        await self.audit_repo.log_event(
            db=db,
            action="UTILITY_NETWORK_CREATED",
            entity_type="UTILITY_NETWORK",
            entity_id=str(network.id),
            actor_user_id=actor_id,
            details={"name": network.name, "utility_type": network.utility_type},
        )
        return network

    async def get_network(self, db: AsyncSession, network_id: uuid.UUID) -> Optional[UtilityNetwork]:
        return await self.repo.get_network(db, network_id)

    async def list_networks(
        self,
        db: AsyncSession,
        jurisdiction_id: Optional[uuid.UUID] = None,
        utility_type: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[UtilityNetwork]:
        return await self.repo.list_networks(db, jurisdiction_id, utility_type, status, skip, limit)

    # 2. Assets
    async def create_asset(
        self,
        db: AsyncSession,
        data: Dict[str, Any],
        actor_id: Optional[uuid.UUID] = None,
    ) -> UtilityAsset:
        # Validate vertical bounds & calculate derived elevation/depth
        depth = data.get("depth")
        ground_elev = data.get("ground_elevation")
        centerline_elev = data.get("centerline_elevation")

        if depth is None and ground_elev is not None and centerline_elev is not None:
            depth = DepthElevationCalculator.compute_depth(ground_elev, centerline_elev)
            data["depth"] = depth
        elif centerline_elev is None and ground_elev is not None and depth is not None:
            centerline_elev = DepthElevationCalculator.compute_centerline_elevation(ground_elev, depth)
            data["centerline_elevation"] = centerline_elev

        # Vertical validation checks
        vertical_issues = DepthElevationCalculator.validate_vertical_bounds(
            depth=depth,
            ground_elevation=ground_elev,
            centerline_elevation=centerline_elev,
        )
        if vertical_issues:
            data.setdefault("metadata_json", {})["vertical_validation_issues"] = vertical_issues

        asset = await self.repo.create_asset(db, data)

        await self.audit_repo.log_event(
            db=db,
            action="UTILITY_ASSET_CREATED",
            entity_type="UTILITY_ASSET",
            entity_id=str(asset.id),
            actor_user_id=actor_id,
            details={
                "asset_reference": asset.asset_reference,
                "asset_type": asset.asset_type,
                "network_id": str(asset.network_id),
                "review_status": asset.review_status,
                "depth": asset.depth,
            },
        )
        return asset

    async def get_asset(self, db: AsyncSession, asset_id: uuid.UUID) -> Optional[UtilityAsset]:
        return await self.repo.get_asset(db, asset_id)

    async def get_asset_details(
        self,
        db: AsyncSession,
        asset_id: uuid.UUID,
    ) -> Optional[Dict[str, Any]]:
        asset = await self.repo.get_asset(db, asset_id)
        if not asset:
            return None

        network = await self.repo.get_network(db, asset.network_id)
        segment = await self.repo.get_segment_by_asset(db, asset.id)
        structures = await self.repo.list_structures_by_asset(db, asset.id)
        inspections = await self.repo.list_inspections_by_asset(db, asset.id)
        maintenance = await self.repo.list_maintenance_events_by_asset(db, asset.id)
        clashes = await self.repo.list_clashes(db, asset_id=asset.id)

        # Spatial relations
        parcel_relation = None
        building_relation = None

        if asset.geometry_wkt:
            if asset.parcel_id:
                parcel = await self.parcel_repo.get_by_id(db, asset.parcel_id)
                if parcel and parcel.geometry_wkt:
                    parcel_rel_res = UtilitySpatialRelationshipAnalyzer.analyze_parcel_relationship(
                        utility_wkt=asset.geometry_wkt,
                        parcel_wkt=parcel.geometry_wkt,
                        parcel_id=str(parcel.id),
                        parcel_number=parcel.parcel_number,
                    )
                    parcel_relation = parcel_rel_res.to_dict()

            if asset.building_id:
                building = await self.building_repo.get_by_id(db, asset.building_id)
                if building and building.geometry_wkt:
                    bld_rel_res = UtilitySpatialRelationshipAnalyzer.analyze_building_relationship(
                        utility_wkt=asset.geometry_wkt,
                        building_wkt=building.geometry_wkt,
                        building_id=str(building.id),
                        building_reference=building.building_reference,
                        utility_centerline_elev=asset.centerline_elevation,
                        utility_depth=asset.depth,
                    )
                    building_relation = bld_rel_res.to_dict()

        return {
            "asset": asset,
            "network": network,
            "segment": segment,
            "structures": structures,
            "inspections": inspections,
            "maintenance_events": maintenance,
            "clashes": clashes,
            "parcel_relation": parcel_relation,
            "building_relation": building_relation,
        }

    async def update_asset(
        self,
        db: AsyncSession,
        asset_id: uuid.UUID,
        updates: Dict[str, Any],
        actor_id: Optional[uuid.UUID] = None,
    ) -> Optional[UtilityAsset]:
        asset = await self.repo.get_asset(db, asset_id)
        if not asset:
            return None

        prev_status = asset.status
        updated = await self.repo.update_asset(db, asset, updates)

        await self.audit_repo.log_event(
            db=db,
            action="UTILITY_ASSET_MODIFIED",
            entity_type="UTILITY_ASSET",
            entity_id=str(asset.id),
            actor_user_id=actor_id,
            details={"previous_status": prev_status, "updated_fields": list(updates.keys())},
        )
        return updated

    # 3. Human Review & Controlled Official Update
    async def review_candidate(
        self,
        db: AsyncSession,
        asset_id: uuid.UUID,
        action: str,  # VERIFY, REJECT, REVISION_REQUIRED
        review_notes: str,
        actor_id: Optional[uuid.UUID] = None,
    ) -> Optional[UtilityAsset]:
        asset = await self.repo.get_asset(db, asset_id)
        if not asset:
            return None

        previous_status = asset.review_status
        new_status = "VERIFIED" if action == "VERIFY" else ("REJECTED" if action == "REJECT" else "REVISION_REQUIRED")

        meta = dict(asset.metadata_json or {})
        reviews = meta.setdefault("review_history", [])
        reviews.append({
            "action": action,
            "previous_status": previous_status,
            "new_status": new_status,
            "reviewed_by": str(actor_id) if actor_id else None,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "notes": review_notes,
        })

        updates = {
            "review_status": new_status,
            "metadata_json": meta,
        }
        updated = await self.repo.update_asset(db, asset, updates)

        await self.audit_repo.log_event(
            db=db,
            action=f"UTILITY_ASSET_{action}",
            entity_type="UTILITY_ASSET",
            entity_id=str(asset.id),
            actor_user_id=actor_id,
            details={
                "action": action,
                "previous_status": previous_status,
                "new_status": new_status,
                "notes": review_notes,
            },
        )
        return updated

    async def controlled_official_update(
        self,
        db: AsyncSession,
        asset_id: uuid.UUID,
        reason: str,
        source_reference: str,
        updates: Dict[str, Any],
        actor_id: Optional[uuid.UUID] = None,
    ) -> Optional[UtilityAsset]:
        asset = await self.repo.get_asset(db, asset_id)
        if not asset:
            return None

        meta = dict(asset.metadata_json or {})
        history = meta.setdefault("controlled_updates", [])
        history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor_id": str(actor_id) if actor_id else None,
            "reason": reason,
            "source_reference": source_reference,
            "modified_keys": list(updates.keys()),
        })

        updates["metadata_json"] = meta
        updates["source_reference"] = source_reference
        updated = await self.repo.update_asset(db, asset, updates)

        await self.audit_repo.log_event(
            db=db,
            action="CONTROLLED_OFFICIAL_UPDATE",
            entity_type="UTILITY_ASSET",
            entity_id=str(asset.id),
            actor_user_id=actor_id,
            details={
                "reason": reason,
                "source_reference": source_reference,
                "modified_fields": list(updates.keys()),
            },
        )
        return updated

    # 4. Topology and Network Analysis
    async def get_network_topology(
        self,
        db: AsyncSession,
        network_id: uuid.UUID,
    ) -> Dict[str, Any]:
        network = await self.repo.get_network(db, network_id)
        if not network:
            return {"error": "Network not found"}

        nodes = await self.repo.list_nodes_by_network(db, network_id)
        segments = await self.repo.list_segments_by_network(db, network_id)

        nodes_data = [
            {
                "id": str(n.id),
                "node_type": n.node_type,
                "asset_reference": n.asset_reference,
                "geometry_wkt": n.geometry_wkt,
            }
            for n in nodes
        ]
        segments_data = [
            {
                "id": str(s.id),
                "utility_asset_id": str(s.utility_asset_id),
                "start_node_id": str(s.start_node_id) if s.start_node_id else None,
                "end_node_id": str(s.end_node_id) if s.end_node_id else None,
                "geometry_wkt": s.geometry_wkt,
            }
            for s in segments
        ]

        result = UtilityNetworkTopologyEngine.validate_network(nodes_data, segments_data)
        return result

    # 5. Clash Detection
    async def run_clash_detection(
        self,
        db: AsyncSession,
        jurisdiction_id: Optional[uuid.UUID] = None,
        network_id: Optional[uuid.UUID] = None,
        actor_id: Optional[uuid.UUID] = None,
    ) -> List[UtilityClash]:
        assets = await self.repo.list_assets(db, network_id=network_id, limit=500)
        rules = await self.repo.list_separation_rules(db, jurisdiction_id=jurisdiction_id)

        assets_data = []
        for a in assets:
            if not a.geometry_wkt:
                continue
            assets_data.append({
                "id": str(a.id),
                "asset_reference": a.asset_reference,
                "utility_type": a.network.utility_type if a.network else "WATER",
                "asset_type": a.asset_type,
                "geometry_wkt": a.geometry_wkt,
                "depth": a.depth,
                "centerline_elevation": a.centerline_elevation,
            })

        rules_data = [
            {
                "utility_type_a": r.utility_type_a,
                "utility_type_b": r.utility_type_b,
                "required_horizontal_separation_m": r.required_horizontal_separation_m,
                "required_vertical_separation_m": r.required_vertical_separation_m,
            }
            for r in rules
        ]

        detected = UtilityClashDetector.scan_asset_collection(assets_data, rules_data)
        created_clashes = []

        for c in detected:
            clash_record = await self.repo.create_clash(
                db,
                {
                    "asset_a_id": uuid.UUID(c.asset_a_id),
                    "asset_b_id": uuid.UUID(c.asset_b_id),
                    "horizontal_relationship": c.horizontal_relationship,
                    "vertical_relationship": c.vertical_relationship,
                    "measured_horizontal_separation_m": c.measured_horizontal_separation_m,
                    "measured_vertical_separation_m": c.measured_vertical_separation_m,
                    "required_horizontal_separation_m": c.required_horizontal_separation_m or 1.0,
                    "required_vertical_separation_m": c.required_vertical_separation_m or 0.3,
                    "clash_geometry_wkt": c.clash_geometry_wkt,
                    "severity": c.severity,
                    "status": "OPEN",
                    "resolution_notes": c.notes,
                },
            )
            created_clashes.append(clash_record)

        if created_clashes:
            await self.audit_repo.log_event(
                db=db,
                action="UTILITY_CLASHES_DETECTED",
                entity_type="UTILITY_CLASH",
                entity_id=str(created_clashes[0].id),
                actor_user_id=actor_id,
                details={"clashes_found": len(created_clashes)},
            )

        return created_clashes

    async def review_clash(
        self,
        db: AsyncSession,
        clash_id: uuid.UUID,
        action: str,  # ACKNOWLEDGE, RESOLVE, WAIVE
        resolution_notes: str,
        actor_id: Optional[uuid.UUID] = None,
    ) -> Optional[UtilityClash]:
        clash = await self.repo.get_clash(db, clash_id)
        if not clash:
            return None

        new_status = "ACKNOWLEDGED" if action == "ACKNOWLEDGE" else ("RESOLVED" if action == "RESOLVE" else "WAIVED")
        updates = {
            "status": new_status,
            "resolution_notes": resolution_notes,
            "resolved_by": actor_id,
            "resolved_at": datetime.now(timezone.utc),
        }
        updated = await self.repo.update_clash(db, clash, updates)

        await self.audit_repo.log_event(
            db=db,
            action=f"UTILITY_CLASH_{action}",
            entity_type="UTILITY_CLASH",
            entity_id=str(clash.id),
            actor_user_id=actor_id,
            details={"action": action, "notes": resolution_notes},
        )
        return updated

    # 6. 2D Map GeoJSON & 3D Underground Scene
    async def get_map_geojson(
        self,
        db: AsyncSession,
        min_lon: float,
        min_lat: float,
        max_lon: float,
        max_lat: float,
        network_id: Optional[uuid.UUID] = None,
        utility_type: Optional[str] = None,
        limit: int = 200,
    ) -> Dict[str, Any]:
        assets = await self.repo.query_assets_by_bbox(
            db, min_lon, min_lat, max_lon, max_lat, network_id, utility_type, limit
        )

        features = []
        for a in assets:
            if not a.geometry_wkt:
                continue
            try:
                geom = wkt.loads(a.geometry_wkt)
                features.append({
                    "type": "Feature",
                    "id": str(a.id),
                    "geometry": mapping(geom),
                    "properties": {
                        "id": str(a.id),
                        "asset_reference": a.asset_reference,
                        "asset_type": a.asset_type,
                        "utility_type": a.network.utility_type if a.network else "WATER",
                        "status": a.status,
                        "review_status": a.review_status,
                        "depth": a.depth,
                        "ground_elevation": a.ground_elevation,
                        "centerline_elevation": a.centerline_elevation,
                        "diameter": a.diameter,
                        "material": a.material,
                        "confidence": a.confidence,
                    },
                })
            except Exception:
                continue

        return {
            "type": "FeatureCollection",
            "features": features,
        }

    async def get_3d_scene(
        self,
        db: AsyncSession,
        network_id: Optional[uuid.UUID] = None,
        utility_type: Optional[str] = None,
        limit: int = 500,
    ) -> Dict[str, Any]:
        assets = await self.repo.list_assets(
            db, network_id=network_id, limit=limit
        )

        type_colors = {
            "WATER": "#0284c7",       # Sky blue
            "SEWER": "#84cc16",       # Lime green
            "STORMWATER": "#06b6d4",   # Cyan
            "GAS": "#eab308",         # Yellow
            "ELECTRICITY": "#ef4444", # Red
            "TELECOM": "#f97316",     # Orange
            "FIBER": "#a855f7",       # Purple
            "DRAINAGE": "#14b8a6",    # Teal
            "OTHER": "#94a3b8",       # Slate
        }

        features = []
        for a in assets:
            if not a.geometry_wkt:
                continue
            try:
                geom = wkt.loads(a.geometry_wkt)
                u_type = a.network.utility_type if a.network else "WATER"
                color = type_colors.get(u_type.upper(), "#94a3b8")

                # Extract coordinates
                coords = []
                if hasattr(geom, "coords"):
                    coords = list(geom.coords)
                elif hasattr(geom, "geoms"):
                    for sub in geom.geoms:
                        if hasattr(sub, "coords"):
                            coords.extend(list(sub.coords))

                features.append({
                    "asset_id": str(a.id),
                    "asset_reference": a.asset_reference,
                    "network_id": str(a.network_id),
                    "utility_type": u_type,
                    "asset_type": a.asset_type,
                    "geometry_type": geom.geom_type,
                    "coordinates": coords,
                    "depth": a.depth,
                    "ground_elevation": a.ground_elevation,
                    "centerline_elevation": a.centerline_elevation,
                    "diameter_m": a.diameter or 0.3,
                    "material": a.material,
                    "status": a.status,
                    "color_hex": color,
                })
            except Exception:
                continue

        return {
            "total_features": len(features),
            "features": features,
        }
