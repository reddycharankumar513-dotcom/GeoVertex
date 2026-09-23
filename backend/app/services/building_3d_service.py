import json
import uuid
from typing import Any, Dict, List, Optional, Tuple
import shapely.geometry
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import BadRequestException, NotFoundException
from app.gis.geometry import GeometryEngine
from app.gis.geometry_3d import Geometry3DEngine
from app.models.building import BuildingFootprint
from app.models.threed import Building3DRepresentation, ThreeDAsset
from app.repositories.audit_repository import audit_repository
from app.repositories.building_repository import building_repository
from app.repositories.jurisdiction_repository import jurisdiction_repository
from app.repositories.parcel_repository import parcel_repository
from app.repositories.property_repository import property_repository
from app.repositories.threed_repository import threed_repository
from app.schemas.threed import (
    Building3DHeightUpdateRequest,
    CesiumExtrusionFeature,
    SceneMetadata,
    ThreeDIdentifyResponse,
    ThreeDSceneResponse,
)
from app.services.spatial_validation_service import spatial_validation_service


class Building3DService:
    """Core domain service for 3D digital twin scene management,
    2.5D building extrusion, vertical spatial metadata, and 3D identify queries.
    """

    async def get_or_create_representation(
        self,
        db: AsyncSession,
        building: BuildingFootprint,
    ) -> Building3DRepresentation:
        """Fetch 3D representation or synthesize authoritative default from building footprint metadata."""
        rep = await threed_repository.get_representation_by_building_id(db, building.id)
        if rep:
            return rep

        # Authoritative fallback derived from building metadata
        fallback_height = building.height_estimate if (building.height_estimate and building.height_estimate > 0) else 12.0
        fallback_source = "SURVEY" if building.height_estimate else "ESTIMATED"

        rep = await threed_repository.save_representation(
            db=db,
            building_id=building.id,
            height=fallback_height,
            height_source=fallback_source,
            height_confidence=0.85 if building.height_estimate else 0.50,
            height_unit="METERS",
            base_elevation=0.0,
            elevation_source="LOCAL_REFERENCE_PLANE",
            vertical_reference="METERS_ABOVE_GROUND",
            geometry_type="EXTRUSION",
            model_source="EXTRUDED_FOOTPRINT",
            status="ACTIVE",
        )
        return rep

    async def get_scene_data(
        self,
        db: AsyncSession,
        bbox_str: Optional[str] = None,
        jurisdiction_id: Optional[uuid.UUID] = None,
        limit: int = 150,
    ) -> ThreeDSceneResponse:
        """Construct a lightweight, CesiumJS-ready 3D scene payload containing
        extruded 3D buildings and 2D cadastral parcel ground wireframes.
        """
        # 1. Parse optional bbox
        parsed_bbox = None
        if bbox_str:
            try:
                coords = [float(x.strip()) for x in bbox_str.split(",")]
                if len(coords) == 4:
                    parsed_bbox = coords
            except Exception:
                pass

        # 2. Fetch buildings
        if parsed_bbox:
            buildings = await building_repository.get_by_bbox(
                db,
                min_lon=parsed_bbox[0],
                min_lat=parsed_bbox[1],
                max_lon=parsed_bbox[2],
                max_lat=parsed_bbox[3],
                limit=limit,
            )
        else:
            buildings, _ = await building_repository.list(
                db=db,
                skip=0,
                limit=limit,
            )

        # 3. Fetch parcels
        if parsed_bbox:
            parcels = await parcel_repository.get_by_bbox(
                db,
                min_lon=parsed_bbox[0],
                min_lat=parsed_bbox[1],
                max_lon=parsed_bbox[2],
                max_lat=parsed_bbox[3],
                jurisdiction_id=jurisdiction_id,
                limit=limit,
            )
        elif jurisdiction_id:
            parcels, _ = await parcel_repository.list(db=db, jurisdiction_id=jurisdiction_id, limit=limit)
        else:
            parcels, _ = await parcel_repository.list(db=db, limit=limit)

        # Map parcel IDs to codes for fast lookup
        parcel_map = {p.id: p for p in parcels}

        # 3. Build extruded building entities
        building_features: List[CesiumExtrusionFeature] = []
        min_lon, min_lat, max_lon, max_lat = 180.0, 90.0, -180.0, -90.0

        for bldg in buildings:
            if not bldg.geometry_wkt:
                continue

            rep = await self.get_or_create_representation(db, bldg)
            p_code = parcel_map[bldg.parcel_id].parcel_code if (bldg.parcel_id and bldg.parcel_id in parcel_map) else None

            extrusion = Geometry3DEngine.generate_cesium_extrusion(
                building_id=str(bldg.id),
                building_reference=bldg.building_reference,
                building_type=bldg.building_type,
                status=bldg.status,
                footprint_geom_input=bldg.geometry_wkt,
                height=rep.height,
                height_source=rep.height_source,
                height_confidence=rep.height_confidence,
                height_unit=rep.height_unit,
                base_elevation=rep.base_elevation,
                elevation_source=rep.elevation_source,
                vertical_reference=rep.vertical_reference,
                parcel_id=str(bldg.parcel_id) if bldg.parcel_id else None,
                parcel_code=p_code,
            )

            # Update scene bounds
            b_box = extrusion["bbox_3d"]
            min_lon = min(min_lon, b_box[0])
            min_lat = min(min_lat, b_box[1])
            max_lon = max(max_lon, b_box[3])
            max_lat = max(max_lat, b_box[4])

            building_features.append(CesiumExtrusionFeature(**extrusion))

        # 4. Build parcel 2D boundaries for 3D context
        parcel_features: List[Dict[str, Any]] = []
        for p in parcels:
            if not p.geometry_wkt:
                continue
            try:
                p_geom = GeometryEngine.parse_geometry(p.geometry_wkt)
                geojson_geom = GeometryEngine.to_geojson_dict(p_geom)
                parcel_features.append({
                    "type": "Feature",
                    "id": str(p.id),
                    "properties": {
                        "parcel_id": str(p.id),
                        "parcel_number": p.parcel_number,
                        "parcel_code": p.parcel_code,
                        "land_use": p.land_use,
                        "status": p.status,
                        "area_sq_m": p.area,
                        "centroid": [p.centroid_lon, p.centroid_lat, 0.0],
                    },
                    "geometry": geojson_geom,
                })
                p_bounds = p_geom.bounds
                min_lon = min(min_lon, p_bounds[0])
                min_lat = min(min_lat, p_bounds[1])
                max_lon = max(max_lon, p_bounds[2])
                max_lat = max(max_lat, p_bounds[3])
            except Exception:
                continue

        # Safe defaults if no features
        if min_lon > max_lon:
            min_lon, min_lat, max_lon, max_lat = 78.485, 17.380, 78.500, 17.395

        center_lon = round((min_lon + max_lon) / 2.0, 6)
        center_lat = round((min_lat + max_lat) / 2.0, 6)

        scene_meta = SceneMetadata(
            crs="EPSG:4326",
            vertical_reference="METERS_ABOVE_GROUND",
            center=[center_lon, center_lat, 0.0],
            bounds=[min_lon, min_lat, max_lon, max_lat],
            jurisdiction_id=str(jurisdiction_id) if jurisdiction_id else None,
            camera_preset={
                "destination": [center_lon, center_lat, 450.0],
                "orientation": {"heading": 0.0, "pitch": -45.0, "roll": 0.0},
            },
        )

        return ThreeDSceneResponse(
            scene=scene_meta,
            buildings=building_features,
            parcels=parcel_features,
            metadata={
                "total_buildings": len(building_features),
                "total_parcels": len(parcel_features),
                "representation_format": "CESIUM_EXTRUSION_LOD1",
                "lod": "LOD1",
            },
        )

    async def get_building_3d(self, db: AsyncSession, building_id: uuid.UUID) -> Dict[str, Any]:
        """Retrieve authoritative 3D representation and associated cadastral links for a building."""
        bldg = await building_repository.get_by_id(db, building_id)
        if not bldg:
            raise NotFoundException(f"Building with ID '{building_id}' not found")

        rep = await self.get_or_create_representation(db, bldg)

        # Linked parcel
        parcel = None
        properties = []
        if bldg.parcel_id:
            parcel = await parcel_repository.get_by_id(db, bldg.parcel_id)
            props, _ = await property_repository.list(db, parcel_id=bldg.parcel_id)
            properties = [
                {
                    "id": str(pr.id),
                    "property_reference": pr.property_reference,
                    "property_type": pr.property_type,
                    "address": pr.address,
                    "status": pr.status,
                }
                for pr in props
            ]

        extrusion = Geometry3DEngine.generate_cesium_extrusion(
            building_id=str(bldg.id),
            building_reference=bldg.building_reference,
            building_type=bldg.building_type,
            status=bldg.status,
            footprint_geom_input=bldg.geometry_wkt or "POLYGON EMPTY",
            height=rep.height,
            height_source=rep.height_source,
            height_confidence=rep.height_confidence,
            height_unit=rep.height_unit,
            base_elevation=rep.base_elevation,
            elevation_source=rep.elevation_source,
            vertical_reference=rep.vertical_reference,
            parcel_id=str(bldg.parcel_id) if bldg.parcel_id else None,
            parcel_code=parcel.parcel_code if parcel else None,
        )

        return {
            "building": {
                "id": str(bldg.id),
                "building_reference": bldg.building_reference,
                "building_type": bldg.building_type,
                "status": bldg.status,
                "area_sq_m": bldg.area,
                "source": bldg.source,
                "created_at": bldg.created_at.isoformat(),
                "updated_at": bldg.updated_at.isoformat(),
            },
            "representation_3d": {
                "id": str(rep.id),
                "geometry_type": rep.geometry_type,
                "height": rep.height,
                "height_source": rep.height_source,
                "height_confidence": rep.height_confidence,
                "height_unit": rep.height_unit,
                "base_elevation": rep.base_elevation,
                "elevation_source": rep.elevation_source,
                "vertical_reference": rep.vertical_reference,
                "model_source": rep.model_source,
                "model_version": rep.model_version,
                "status": rep.status,
            },
            "parcel": {
                "id": str(parcel.id),
                "parcel_number": parcel.parcel_number,
                "parcel_code": parcel.parcel_code,
                "land_use": parcel.land_use,
                "status": parcel.status,
                "area_sq_m": parcel.area,
            } if parcel else None,
            "properties": properties,
            "cesium_extrusion": extrusion,
        }

    async def update_building_height(
        self,
        db: AsyncSession,
        building_id: uuid.UUID,
        data: Building3DHeightUpdateRequest,
        actor_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Building3DRepresentation:
        """Update vertical height and base elevation with authoritative validation and audit logging."""
        bldg = await building_repository.get_by_id(db, building_id)
        if not bldg:
            raise NotFoundException(f"Building with ID '{building_id}' not found")

        # Validation
        validation = await spatial_validation_service.validate_building_3d_candidate(
            db=db,
            height=data.height,
            base_elevation=data.base_elevation or 0.0,
            height_confidence=data.height_confidence,
            geometry_input=bldg.geometry_wkt,
            parcel_id=bldg.parcel_id,
        )
        if not validation.valid:
            raise BadRequestException(
                message=validation.errors[0].message if validation.errors else "Invalid 3D parameters",
                details={"errors": [e.model_dump() for e in validation.errors]},
            )

        existing_rep = await self.get_or_create_representation(db, bldg)
        old_height = existing_rep.height
        old_base = existing_rep.base_elevation

        updated_rep = await threed_repository.save_representation(
            db=db,
            building_id=bldg.id,
            height=data.height,
            height_source=data.height_source or "MANUAL",
            height_confidence=data.height_confidence,
            base_elevation=data.base_elevation if data.base_elevation is not None else existing_rep.base_elevation,
            elevation_source=data.elevation_source or existing_rep.elevation_source,
            vertical_reference=data.vertical_reference or existing_rep.vertical_reference,
            user_id=actor_id,
        )

        # Sync building height_estimate field
        bldg.height_estimate = data.height
        bldg.updated_by = actor_id
        await db.flush()

        # Audit events
        await audit_repository.log_event(
            db=db,
            action="BUILDING_HEIGHT_UPDATED",
            entity_type="BUILDING_3D",
            entity_id=str(bldg.id),
            actor_user_id=actor_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={
                "building_reference": bldg.building_reference,
                "old_height": old_height,
                "new_height": updated_rep.height,
                "height_source": updated_rep.height_source,
            },
        )

        if data.base_elevation is not None and data.base_elevation != old_base:
            await audit_repository.log_event(
                db=db,
                action="BASE_ELEVATION_UPDATED",
                entity_type="BUILDING_3D",
                entity_id=str(bldg.id),
                actor_user_id=actor_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details={
                    "building_reference": bldg.building_reference,
                    "old_base_elevation": old_base,
                    "new_base_elevation": updated_rep.base_elevation,
                },
            )

        return updated_rep

    async def identify_3d(
        self,
        db: AsyncSession,
        longitude: float,
        latitude: float,
        height: Optional[float] = None,
        radius_meters: float = 30.0,
    ) -> ThreeDIdentifyResponse:
        """3D point identify query: locates building footprint, parent parcel,
        property record, and administrative jurisdiction under clicked coordinates.
        """
        # Query nearest/intersecting building
        buildings, _ = await building_repository.list(db=db, limit=200)
        found_building = None
        min_dist = float("inf")

        for bldg in buildings:
            if not bldg.geometry_wkt:
                continue
            try:
                b_geom = GeometryEngine.parse_geometry(bldg.geometry_wkt)
                pt = shapely.geometry.Point(longitude, latitude)
                if b_geom.contains(pt):
                    found_building = bldg
                    break
                dist = b_geom.distance(pt)
                if dist < min_dist and dist < (radius_meters / 111320.0):
                    min_dist = dist
                    found_building = bldg
            except Exception:
                continue

        if not found_building:
            return ThreeDIdentifyResponse()

        rep = await self.get_or_create_representation(db, found_building)

        # Linked parcel
        parcel_info = None
        jurisdiction_info = None
        property_info = None

        if found_building.parcel_id:
            parcel = await parcel_repository.get_by_id(db, found_building.parcel_id)
            if parcel:
                parcel_info = {
                    "id": str(parcel.id),
                    "parcel_number": parcel.parcel_number,
                    "parcel_code": parcel.parcel_code,
                    "land_use": parcel.land_use,
                    "status": parcel.status,
                    "area_sq_m": parcel.area,
                }
                # Jurisdiction
                jur = await jurisdiction_repository.get_by_id(db, parcel.jurisdiction_id)
                if jur:
                    jurisdiction_info = {
                        "id": str(jur.id),
                        "name": jur.name,
                        "code": jur.code,
                        "level": jur.level,
                    }

                # Primary property
                props, _ = await property_repository.list(db, parcel_id=parcel.id, limit=1)
                if props:
                    property_info = {
                        "id": str(props[0].id),
                        "property_reference": props[0].property_reference,
                        "property_type": props[0].property_type,
                        "address": props[0].address,
                        "status": props[0].status,
                    }

        building_info = {
            "id": str(found_building.id),
            "building_reference": found_building.building_reference,
            "building_type": found_building.building_type,
            "status": found_building.status,
            "footprint_area_sq_m": found_building.area,
            "height": rep.height,
            "height_source": rep.height_source,
            "height_unit": rep.height_unit,
            "base_elevation": rep.base_elevation,
            "elevation_source": rep.elevation_source,
            "vertical_reference": rep.vertical_reference,
            "extruded_height": rep.base_elevation + rep.height,
        }

        return ThreeDIdentifyResponse(
            building=building_info,
            parcel=parcel_info,
            property=property_info,
            jurisdiction=jurisdiction_info,
        )

    async def get_parcel_3d_context(self, db: AsyncSession, parcel_id: uuid.UUID) -> Dict[str, Any]:
        """Retrieve 3D context for a parcel including its ground boundary,
        all contained 3D building extrusions, and associated property records.
        """
        parcel = await parcel_repository.get_by_id(db, parcel_id)
        if not parcel:
            raise NotFoundException(f"Parcel with ID '{parcel_id}' not found")

        # Parcel geometry
        parcel_geojson = None
        if parcel.geometry_wkt:
            try:
                p_geom = GeometryEngine.parse_geometry(parcel.geometry_wkt)
                parcel_geojson = GeometryEngine.to_geojson_dict(p_geom)
            except Exception:
                pass

        # Buildings on this parcel
        buildings, _ = await building_repository.list(db=db, parcel_id=parcel.id, limit=50)
        building_extrusions = []
        for bldg in buildings:
            if not bldg.geometry_wkt:
                continue
            rep = await self.get_or_create_representation(db, bldg)
            ext = Geometry3DEngine.generate_cesium_extrusion(
                building_id=str(bldg.id),
                building_reference=bldg.building_reference,
                building_type=bldg.building_type,
                status=bldg.status,
                footprint_geom_input=bldg.geometry_wkt,
                height=rep.height,
                height_source=rep.height_source,
                height_confidence=rep.height_confidence,
                height_unit=rep.height_unit,
                base_elevation=rep.base_elevation,
                elevation_source=rep.elevation_source,
                vertical_reference=rep.vertical_reference,
                parcel_id=str(parcel.id),
                parcel_code=parcel.parcel_code,
            )
            building_extrusions.append(ext)

        # Properties
        properties, _ = await property_repository.list(db=db, parcel_id=parcel.id)
        prop_list = [
            {
                "id": str(pr.id),
                "property_reference": pr.property_reference,
                "property_type": pr.property_type,
                "address": pr.address,
                "status": pr.status,
            }
            for pr in properties
        ]

        center_lon = parcel.centroid_lon or 78.4867
        center_lat = parcel.centroid_lat or 17.3850

        return {
            "parcel": {
                "id": str(parcel.id),
                "parcel_number": parcel.parcel_number,
                "parcel_code": parcel.parcel_code,
                "land_use": parcel.land_use,
                "status": parcel.status,
                "area_sq_m": parcel.area,
                "centroid": [center_lon, center_lat, 0.0],
                "geometry": parcel_geojson,
            },
            "buildings": building_extrusions,
            "properties": prop_list,
            "camera_preset": {
                "destination": [center_lon, center_lat, 300.0],
                "orientation": {"heading": 0.0, "pitch": -45.0, "roll": 0.0},
            },
        }


building_3d_service = Building3DService()
