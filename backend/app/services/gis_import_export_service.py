import json
import uuid
from typing import Any, Dict, List, Optional, Tuple, Union
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import BadRequestException, NotFoundException
from app.gis.geometry import GeometryEngine
from app.models.jurisdiction import Jurisdiction
from app.models.parcel import Parcel
from app.repositories.audit_repository import audit_repository
from app.repositories.jurisdiction_repository import jurisdiction_repository
from app.repositories.parcel_repository import parcel_repository
from app.schemas.gis import GISImportErrorItem, GISImportSummary, GeoJSONFeature, GeoJSONFeatureCollection
from app.services.spatial_validation_service import spatial_validation_service


class GISImportExportService:
    """Service handling cadastral GeoJSON ingestion, CRS transformation,
    batch validation, and spatial feature exports.
    """

    async def import_geojson(
        self,
        db: AsyncSession,
        geojson_data: Union[Dict[str, Any], str],
        jurisdiction_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> GISImportSummary:
        # Parse root payload
        if isinstance(geojson_data, str):
            try:
                data = json.loads(geojson_data)
            except Exception as e:
                raise BadRequestException(f"Invalid GeoJSON JSON payload: {str(e)}")
        else:
            data = geojson_data

        if not isinstance(data, dict) or data.get("type") != "FeatureCollection":
            raise BadRequestException("GeoJSON payload must be a valid 'FeatureCollection'")

        # Verify jurisdiction
        jur = await jurisdiction_repository.get_by_id(db, jurisdiction_id)
        if not jur:
            raise NotFoundException(f"Target jurisdiction with ID '{jurisdiction_id}' not found")

        # Inspect CRS
        source_srid = 4326
        crs_info = data.get("crs")
        if crs_info and isinstance(crs_info, dict):
            props = crs_info.get("properties", {})
            name = props.get("name", "")
            if "EPSG:" in name:
                try:
                    source_srid = int(name.split("EPSG:")[-1].split(":")[-1])
                except Exception:
                    source_srid = 4326

        features = data.get("features", [])
        total_records = len(features)

        # Audit import started
        await audit_repository.log_event(
            db=db,
            action="GIS_IMPORT_STARTED",
            entity_type="GIS_IMPORT",
            entity_id=str(jurisdiction_id),
            actor_user_id=actor_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"total_records": total_records, "source_srid": source_srid},
        )

        records_accepted = 0
        records_rejected = 0
        errors: List[GISImportErrorItem] = []
        warnings: List[str] = []

        seen_parcel_numbers = set()
        seen_parcel_codes = set()
        accepted_parcels: List[Parcel] = []

        for idx, feat in enumerate(features):
            if not isinstance(feat, dict) or feat.get("type") != "Feature":
                records_rejected += 1
                errors.append(
                    GISImportErrorItem(
                        feature_index=idx,
                        code="INVALID_FEATURE_FORMAT",
                        message="Item is not a valid GeoJSON Feature object",
                    )
                )
                continue

            geom_data = feat.get("geometry")
            if not geom_data:
                records_rejected += 1
                errors.append(
                    GISImportErrorItem(
                        feature_index=idx,
                        code="MISSING_GEOMETRY",
                        message="Feature contains no geometry",
                    )
                )
                continue

            props = feat.get("properties", {}) or {}

            # Attributes
            parcel_number = str(props.get("parcel_number") or props.get("number") or "").strip()
            if not parcel_number:
                # Fallback to feature id or index
                feat_id = feat.get("id")
                if feat_id:
                    parcel_number = str(feat_id).strip()
                else:
                    records_rejected += 1
                    errors.append(
                        GISImportErrorItem(
                            feature_index=idx,
                            code="MISSING_PARCEL_NUMBER",
                            message="Feature properties missing required 'parcel_number'",
                        )
                    )
                    continue

            parcel_code = str(props.get("parcel_code") or f"GV-{jur.code}-{parcel_number}").strip()

            # Batch duplicate check
            if parcel_number in seen_parcel_numbers:
                records_rejected += 1
                errors.append(
                    GISImportErrorItem(
                        feature_index=idx,
                        code="DUPLICATE_IN_BATCH",
                        message=f"Duplicate parcel number '{parcel_number}' within import batch",
                    )
                )
                continue

            if parcel_code in seen_parcel_codes:
                records_rejected += 1
                errors.append(
                    GISImportErrorItem(
                        feature_index=idx,
                        code="DUPLICATE_CODE_IN_BATCH",
                        message=f"Duplicate parcel code '{parcel_code}' within import batch",
                    )
                )
                continue

            # Database duplicate check
            existing_code = await parcel_repository.get_by_code(db, parcel_code)
            if existing_code:
                records_rejected += 1
                errors.append(
                    GISImportErrorItem(
                        feature_index=idx,
                        code="DUPLICATE_PARCEL_CODE",
                        message=f"Parcel code '{parcel_code}' already exists in database",
                    )
                )
                continue

            existing_number = await parcel_repository.get_by_number_and_jurisdiction(db, jur.id, parcel_number)
            if existing_number:
                records_rejected += 1
                errors.append(
                    GISImportErrorItem(
                        feature_index=idx,
                        code="DUPLICATE_PARCEL_NUMBER",
                        message=f"Parcel number '{parcel_number}' already exists in jurisdiction",
                    )
                )
                continue

            # Geometry validation
            validation = await spatial_validation_service.validate_parcel_candidate(
                db=db,
                geometry_input=geom_data,
                jurisdiction_id=jur.id,
                source_srid=source_srid,
            )
            if not validation.valid:
                records_rejected += 1
                first_err = validation.errors[0]
                errors.append(
                    GISImportErrorItem(
                        feature_index=idx,
                        code=first_err.code,
                        message=first_err.message,
                        details={"errors": [e.model_dump() for e in validation.errors]},
                    )
                )
                continue

            # Parse and transform
            try:
                parsed_geom = GeometryEngine.parse_geometry(geom_data, source_srid=source_srid)
                area_m2 = GeometryEngine.calculate_geodesic_area(parsed_geom)
                centroid_lon, centroid_lat = GeometryEngine.calculate_centroid(parsed_geom)
                geom_wkt = GeometryEngine.to_wkt(parsed_geom)
            except Exception as e:
                records_rejected += 1
                errors.append(
                    GISImportErrorItem(
                        feature_index=idx,
                        code="GEOMETRY_CONVERSION_ERROR",
                        message=f"Failed to normalize geometry: {str(e)}",
                    )
                )
                continue

            parcel = Parcel(
                jurisdiction_id=jur.id,
                parcel_number=parcel_number,
                parcel_code=parcel_code,
                survey_number=str(props.get("survey_number", "")).strip() or None,
                subdivision_number=str(props.get("subdivision_number", "")).strip() or None,
                land_use=str(props.get("land_use", "RESIDENTIAL")).upper(),
                area=area_m2,
                area_unit=str(props.get("area_unit", "SQ_METER")),
                status=str(props.get("status", "ACTIVE")).upper(),
                ownership_status=str(props.get("ownership_status", "RECORDED")).upper(),
                geometry=geom_wkt,
                geometry_wkt=geom_wkt,
                centroid_lon=centroid_lon,
                centroid_lat=centroid_lat,
                source="IMPORT",
                source_reference=f"BATCH-IMPORT-{jur.code}",
                created_by=actor_id,
                updated_by=actor_id,
            )
            db.add(parcel)
            accepted_parcels.append(parcel)
            seen_parcel_numbers.add(parcel_number)
            seen_parcel_codes.add(parcel_code)
            records_accepted += 1

        await db.flush()

        summary = GISImportSummary(
            records_received=total_records,
            records_accepted=records_accepted,
            records_rejected=records_rejected,
            entity_type="PARCEL",
            errors=errors,
            warnings=warnings,
            jurisdiction_id=str(jurisdiction_id),
        )

        # Audit completed
        audit_action = "GIS_IMPORT_COMPLETED" if records_accepted > 0 else "GIS_IMPORT_FAILED"
        await audit_repository.log_event(
            db=db,
            action=audit_action,
            entity_type="GIS_IMPORT",
            entity_id=str(jurisdiction_id),
            actor_user_id=actor_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={
                "received": total_records,
                "accepted": records_accepted,
                "rejected": records_rejected,
            },
        )
        return summary

    async def export_parcels_geojson(
        self,
        db: AsyncSession,
        jurisdiction_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        actor_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> GeoJSONFeatureCollection:
        if bbox:
            min_lon, min_lat, max_lon, max_lat = bbox
            parcels = await parcel_repository.get_by_bbox(
                db=db,
                min_lon=min_lon,
                min_lat=min_lat,
                max_lon=max_lon,
                max_lat=max_lat,
                jurisdiction_id=jurisdiction_id,
                status=status,
                limit=1000,
            )
        else:
            parcels, _ = await parcel_repository.search_and_filter(
                db=db,
                jurisdiction_id=jurisdiction_id,
                status=status,
                skip=0,
                limit=1000,
            )

        features: List[GeoJSONFeature] = []
        for p in parcels:
            if not p.geometry_wkt:
                continue
            try:
                geom = GeometryEngine.parse_geometry(p.geometry_wkt)
                geojson_geom = GeometryEngine.to_geojson(geom)
                features.append(
                    GeoJSONFeature(
                        type="Feature",
                        id=str(p.id),
                        geometry=geojson_geom,
                        properties={
                            "id": str(p.id),
                            "parcel_number": p.parcel_number,
                            "parcel_code": p.parcel_code,
                            "survey_number": p.survey_number,
                            "land_use": p.land_use,
                            "area_sq_m": p.area,
                            "status": p.status,
                            "ownership_status": p.ownership_status,
                            "jurisdiction_id": str(p.jurisdiction_id),
                        },
                    )
                )
            except Exception:
                continue

        # Audit export
        await audit_repository.log_event(
            db=db,
            action="GIS_EXPORT_CREATED",
            entity_type="GIS_EXPORT",
            entity_id=str(jurisdiction_id) if jurisdiction_id else "GLOBAL",
            actor_user_id=actor_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"features_exported": len(features), "entity_type": "PARCEL"},
        )

        return GeoJSONFeatureCollection(
            type="FeatureCollection",
            features=features,
            total_features=len(features),
            crs={"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::4326"}},
        )


gis_import_export_service = GISImportExportService()
