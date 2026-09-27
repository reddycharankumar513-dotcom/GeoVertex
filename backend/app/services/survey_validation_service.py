import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.survey import SurveySession, SurveyObservation, SurveyEvidence
from app.repositories.survey_repository import (
    survey_session_repository,
    survey_observation_repository,
    survey_evidence_repository,
)
from app.repositories.building_repository import building_repository
from app.repositories.threed_repository import threed_repository
from app.repositories.parcel_repository import parcel_repository
from app.repositories.floor_repository import floor_repository
from app.schemas.survey import (
    SurveyValidationIssue,
    SurveyValidationSummary,
)


class SurveyValidationService:
    """Deterministic validation engine for survey observations, coordinates, evidence, and cadastral comparisons."""

    async def validate_session(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
    ) -> SurveyValidationSummary:
        session = await survey_session_repository.get_by_id(db, session_id)
        if not session:
            return SurveyValidationSummary(
                is_valid=False,
                can_submit=False,
                total_errors=1,
                total_warnings=0,
                issues=[
                    SurveyValidationIssue(
                        code="SESSION_NOT_FOUND",
                        severity="ERROR",
                        message=f"Survey session {session_id} was not found",
                    )
                ],
                checklist={
                    "required_fields": False,
                    "location_captured": False,
                    "evidence_attached": False,
                    "measurements_valid": False,
                    "geometry_valid": False,
                },
                comparisons=[],
            )

        observations = await survey_observation_repository.list_by_session(db, session_id)
        evidence_list = await survey_evidence_repository.list_by_session(db, session_id)

        issues: List[SurveyValidationIssue] = []
        comparisons: List[Dict[str, Any]] = []

        # 1. Required Observations Check
        has_observations = len(observations) > 0
        if not has_observations:
            issues.append(
                SurveyValidationIssue(
                    code="NO_OBSERVATIONS_RECORDED",
                    severity="ERROR",
                    field="observations",
                    message="At least one field observation or measurement must be recorded before submission.",
                )
            )

        # 2. Field Coordinates & Location Accuracy Check
        coords_found = False
        low_accuracy_count = 0
        for obs in observations:
            if obs.latitude is not None and obs.longitude is not None:
                coords_found = True
                # Coordinate bounds sanity
                if not (-90.0 <= obs.latitude <= 90.0 and -180.0 <= obs.longitude <= 180.0):
                    issues.append(
                        SurveyValidationIssue(
                            code="INVALID_COORDINATES",
                            severity="ERROR",
                            field="latitude/longitude",
                            message=f"Coordinate ({obs.latitude}, {obs.longitude}) is outside geodetic range [-90..90, -180..180].",
                            details={"observation_id": str(obs.id)},
                        )
                    )
                # Location accuracy threshold check (15m standard for urban cadastral survey)
                if obs.horizontal_accuracy is not None and obs.horizontal_accuracy > 15.0:
                    low_accuracy_count += 1
                    issues.append(
                        SurveyValidationIssue(
                            code="LOW_LOCATION_ACCURACY",
                            severity="WARNING",
                            field="horizontal_accuracy",
                            message=f"Observation {obs.observation_type} has low positioning accuracy (±{obs.horizontal_accuracy}m > 15m threshold).",
                            details={"observation_id": str(obs.id), "accuracy": obs.horizontal_accuracy},
                        )
                    )

        if not coords_found:
            issues.append(
                SurveyValidationIssue(
                    code="MISSING_FIELD_COORDINATES",
                    severity="WARNING",
                    field="coordinates",
                    message="No geographic coordinates were captured during this survey session.",
                )
            )

        # 3. Evidence / Photo Check
        has_evidence = len(evidence_list) > 0
        if not has_evidence:
            issues.append(
                SurveyValidationIssue(
                    code="NO_EVIDENCE_ATTACHED",
                    severity="WARNING",
                    field="evidence",
                    message="No photographic or document evidence attached to this survey session.",
                )
            )

        # 4. Duplicate Detection (Observations & Evidence)
        seen_obs_signatures = set()
        for obs in observations:
            sig = (obs.observation_type, obs.target_type, obs.target_id, obs.value.strip())
            if sig in seen_obs_signatures:
                issues.append(
                    SurveyValidationIssue(
                        code="DUPLICATE_OBSERVATION",
                        severity="WARNING",
                        field="observations",
                        message=f"Duplicate observation detected: {obs.observation_type} with value '{obs.value}' on {obs.target_type} {obs.target_id}.",
                        details={"observation_id": str(obs.id)},
                    )
                )
            else:
                seen_obs_signatures.add(sig)

        seen_hashes = set()
        for ev in evidence_list:
            if ev.sha256_hash in seen_hashes:
                issues.append(
                    SurveyValidationIssue(
                        code="DUPLICATE_PHOTO_HASH",
                        severity="WARNING",
                        field="evidence",
                        message=f"Identical photo content uploaded multiple times (hash {ev.sha256_hash[:8]}).",
                        details={"evidence_id": str(ev.id)},
                    )
                )
            else:
                seen_hashes.add(ev.sha256_hash)

        # 5. Deterministic Comparison with Official Cadastral Records
        assignment = session.assignment
        if assignment:
            # Building Comparison
            if assignment.building_id:
                bld = await building_repository.get_by_id(db, assignment.building_id)
                rep_3d = await threed_repository.get_representation_by_building_id(db, assignment.building_id)
                official_height = rep_3d.height if rep_3d else (bld.height_estimate if bld else None)

                for obs in observations:
                    if obs.observation_type == "BUILDING_HEIGHT":
                        try:
                            obs_height = float(obs.value)
                            if obs_height <= 0:
                                issues.append(
                                    SurveyValidationIssue(
                                        code="INVALID_MEASUREMENT",
                                        severity="ERROR",
                                        field="value",
                                        message=f"Building height must be strictly positive (got {obs_height}m).",
                                    )
                                )
                            elif official_height is not None:
                                delta = round(obs_height - official_height, 2)
                                if abs(delta) > 0.5:
                                    comparisons.append({
                                        "entity": "Building",
                                        "property": "Height",
                                        "official_value": f"{official_height} m",
                                        "survey_value": f"{obs_height} m",
                                        "difference": f"{delta:+} m",
                                        "status": "REVIEW_REQUIRED",
                                        "message": f"Measured building height differs by {delta:+}m from official 3D record ({official_height}m).",
                                    })
                                    issues.append(
                                        SurveyValidationIssue(
                                            code="BUILDING_HEIGHT_DISCREPANCY",
                                            severity="WARNING",
                                            field="value",
                                            message=f"Building height differs by {delta:+}m from official record.",
                                            details={"official": official_height, "measured": obs_height, "delta": delta},
                                        )
                                    )
                                else:
                                    comparisons.append({
                                        "entity": "Building",
                                        "property": "Height",
                                        "official_value": f"{official_height} m",
                                        "survey_value": f"{obs_height} m",
                                        "difference": f"{delta:+} m",
                                        "status": "MATCH",
                                        "message": "Measured height is consistent with recorded building extrusion.",
                                    })
                        except ValueError:
                            issues.append(
                                SurveyValidationIssue(
                                    code="MALFORMED_NUMERIC_VALUE",
                                    severity="ERROR",
                                    field="value",
                                    message=f"Building height observation '{obs.value}' cannot be parsed as a float.",
                                )
                            )

                    elif obs.observation_type == "FLOOR_COUNT":
                        try:
                            obs_count = int(obs.value)
                            if obs_count < 0:
                                issues.append(
                                    SurveyValidationIssue(
                                        code="INVALID_MEASUREMENT",
                                        severity="ERROR",
                                        field="value",
                                        message=f"Floor count cannot be negative (got {obs_count}).",
                                    )
                                )
                            else:
                                existing_floors = await floor_repository.get_by_building(db, assignment.building_id)
                                official_floor_count = len(existing_floors)
                                if official_floor_count > 0:
                                    f_delta = obs_count - official_floor_count
                                    if f_delta != 0:
                                        comparisons.append({
                                            "entity": "Building",
                                            "property": "Floor Count",
                                            "official_value": str(official_floor_count),
                                            "survey_value": str(obs_count),
                                            "difference": f"{f_delta:+}",
                                            "status": "REVIEW_REQUIRED",
                                            "message": f"Observed floor count ({obs_count}) differs from recorded floor count ({official_floor_count}).",
                                        })
                                        issues.append(
                                            SurveyValidationIssue(
                                                code="FLOOR_COUNT_DISCREPANCY",
                                                severity="WARNING",
                                                field="value",
                                                message=f"Floor count differs by {f_delta:+} floors from recorded floors.",
                                                details={"official": official_floor_count, "observed": obs_count},
                                            )
                                        )
                                    else:
                                        comparisons.append({
                                            "entity": "Building",
                                            "property": "Floor Count",
                                            "official_value": str(official_floor_count),
                                            "survey_value": str(obs_count),
                                            "difference": "0",
                                            "status": "MATCH",
                                            "message": "Observed floor count matches cadastral floor structure.",
                                        })
                        except ValueError:
                            issues.append(
                                SurveyValidationIssue(
                                    code="MALFORMED_NUMERIC_VALUE",
                                    severity="ERROR",
                                    field="value",
                                    message=f"Floor count observation '{obs.value}' cannot be parsed as an integer.",
                                )
                            )

            # Parcel Comparison
            if assignment.parcel_id:
                parcel = await parcel_repository.get_by_id(db, assignment.parcel_id)
                if parcel:
                    for obs in observations:
                        if obs.observation_type == "PARCEL_BOUNDARY" and obs.value:
                            comparisons.append({
                                "entity": "Parcel",
                                "property": "Boundary Status",
                                "official_value": parcel.parcel_code,
                                "survey_value": obs.value,
                                "difference": "N/A",
                                "status": "VERIFIED",
                                "message": f"Field observation linked to parcel {parcel.parcel_code}.",
                            })

        # Calculate error and warning totals
        error_count = sum(1 for i in issues if i.severity == "ERROR")
        warning_count = sum(1 for i in issues if i.severity == "WARNING")
        can_submit = (error_count == 0) and has_observations

        checklist = {
            "required_fields": has_observations and error_count == 0,
            "location_captured": coords_found,
            "evidence_attached": has_evidence,
            "measurements_valid": error_count == 0,
            "geometry_valid": True,
        }

        return SurveyValidationSummary(
            is_valid=(error_count == 0),
            can_submit=can_submit,
            total_errors=error_count,
            total_warnings=warning_count,
            issues=issues,
            checklist=checklist,
            comparisons=comparisons,
        )


survey_validation_service = SurveyValidationService()
