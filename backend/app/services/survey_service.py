import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from fastapi import Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BadRequestException, ConflictException, ForbiddenException, NotFoundException
from app.gis.geometry import GeometryEngine
from app.models.survey import (
    SurveyProject,
    SurveyAssignment,
    SurveySession,
    SurveyObservation,
    SurveyEvidence,
    SurveySubmission,
)
from app.models.user import User, UserRole
from app.repositories.audit_repository import audit_repository
from app.repositories.survey_repository import (
    survey_project_repository,
    survey_assignment_repository,
    survey_session_repository,
    survey_observation_repository,
    survey_evidence_repository,
    survey_submission_repository,
)
from app.repositories.building_repository import building_repository
from app.repositories.parcel_repository import parcel_repository
from app.repositories.property_repository import property_repository
from app.repositories.floor_repository import floor_repository
from app.repositories.unit_repository import unit_repository
from app.repositories.organization_repository import jurisdiction_repository
from app.schemas.survey import (
    SurveyProjectCreate,
    SurveyProjectResponse,
    SurveyProjectDetailResponse,
    SurveyAssignmentCreate,
    SurveyAssignmentResponse,
    SurveyAssignmentDetailResponse,
    SurveySessionResponse,
    SurveySessionDetailResponse,
    SurveyObservationCreate,
    SurveyObservationResponse,
    SurveyEvidenceResponse,
    SurveySubmissionResponse,
    SurveyValidationSummary,
    SurveyExportData,
)
from app.services.storage_service import storage_service
from app.services.survey_state_machine import survey_state_machine
from app.services.survey_validation_service import survey_validation_service


class SurveyService:
    """Service layer orchestrating survey projects, assignments, field sessions, observations, evidence, and officer review."""

    # ------------------------------------------------------------------------
    # Survey Projects
    # ------------------------------------------------------------------------

    async def create_project(
        self,
        db: AsyncSession,
        data: SurveyProjectCreate,
        current_user: User,
        request: Optional[Request] = None,
    ) -> SurveyProjectResponse:
        existing = await survey_project_repository.get_by_code(db, data.code)
        if existing:
            raise ConflictException(f"Survey project with code '{data.code}' already exists")

        project = await survey_project_repository.create(
            db=db,
            data=data.model_dump(),
            created_by=current_user.id,
        )

        await audit_repository.log_event(
            db=db,
            actor_user_id=current_user.id,
            action="SURVEY_PROJECT_CREATED",
            entity_type="SURVEY_PROJECT",
            entity_id=str(project.id),
            details={"code": project.code, "name": project.name, "jurisdiction_id": str(project.jurisdiction_id)},
            ip_address=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
        )

        return SurveyProjectResponse.model_validate(project)

    async def list_projects(
        self,
        db: AsyncSession,
        jurisdiction_id: Optional[uuid.UUID] = None,
        organization_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[SurveyProjectDetailResponse], int]:
        items, total = await survey_project_repository.list(
            db=db,
            jurisdiction_id=jurisdiction_id,
            organization_id=organization_id,
            status=status,
            skip=skip,
            limit=limit,
        )

        details = []
        for p in items:
            resp = SurveyProjectDetailResponse.model_validate(p)
            resp.organization_name = p.organization.name if p.organization else None
            resp.jurisdiction_name = p.jurisdiction.name if p.jurisdiction else None
            resp.assignments_count = len(p.assignments)
            resp.active_assignments_count = sum(1 for a in p.assignments if a.status in ["ASSIGNED", "ACCEPTED", "IN_PROGRESS", "SUBMITTED", "UNDER_REVIEW"])
            resp.completed_assignments_count = sum(1 for a in p.assignments if a.status == "APPROVED")
            details.append(resp)

        return details, total

    async def get_project(self, db: AsyncSession, project_id: uuid.UUID) -> SurveyProjectDetailResponse:
        project = await survey_project_repository.get_by_id(db, project_id, include_assignments=True)
        if not project:
            raise NotFoundException(f"Survey project with ID '{project_id}' not found")

        resp = SurveyProjectDetailResponse.model_validate(project)
        resp.organization_name = project.organization.name if project.organization else None
        resp.jurisdiction_name = project.jurisdiction.name if project.jurisdiction else None
        resp.assignments_count = len(project.assignments)
        resp.active_assignments_count = sum(1 for a in project.assignments if a.status in ["ASSIGNED", "ACCEPTED", "IN_PROGRESS", "SUBMITTED", "UNDER_REVIEW"])
        resp.completed_assignments_count = sum(1 for a in project.assignments if a.status == "APPROVED")
        return resp

    # ------------------------------------------------------------------------
    # Survey Assignments
    # ------------------------------------------------------------------------

    async def create_assignment(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        data: SurveyAssignmentCreate,
        current_user: User,
        request: Optional[Request] = None,
    ) -> SurveyAssignmentDetailResponse:
        project = await survey_project_repository.get_by_id(db, project_id)
        if not project:
            raise NotFoundException(f"Survey project with ID '{project_id}' not found")

        assign_data = data.model_dump()
        assign_data["survey_project_id"] = project_id

        # Verify targets if provided
        if data.parcel_id:
            parcel = await parcel_repository.get_by_id(db, data.parcel_id)
            if not parcel:
                raise NotFoundException(f"Target parcel with ID '{data.parcel_id}' not found")
        if data.building_id:
            bld = await building_repository.get_by_id(db, data.building_id)
            if not bld:
                raise NotFoundException(f"Target building with ID '{data.building_id}' not found")
        if data.floor_id:
            flr = await floor_repository.get_by_id(db, data.floor_id)
            if not flr:
                raise NotFoundException(f"Target floor with ID '{data.floor_id}' not found")
        if data.unit_id:
            unt = await unit_repository.get_by_id(db, data.unit_id)
            if not unt:
                raise NotFoundException(f"Target unit with ID '{data.unit_id}' not found")

        assignment = await survey_assignment_repository.create(
            db=db,
            data=assign_data,
            created_by=current_user.id,
        )

        await audit_repository.log_event(
            db=db,
            actor_user_id=current_user.id,
            action="SURVEY_ASSIGNED",
            entity_type="SURVEY_ASSIGNMENT",
            entity_id=str(assignment.id),
            details={
                "project_id": str(project_id),
                "surveyor_id": str(assignment.surveyor_id),
                "priority": assignment.priority,
            },
            ip_address=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
        )

        return await self.get_assignment(db, assignment.id, current_user)

    async def list_assignments(
        self,
        db: AsyncSession,
        current_user: User,
        surveyor_id: Optional[uuid.UUID] = None,
        survey_project_id: Optional[uuid.UUID] = None,
        jurisdiction_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[SurveyAssignmentDetailResponse], int]:
        # Surveyors can only see assignments assigned to them
        actual_surveyor_id = surveyor_id
        if current_user.role == UserRole.SURVEYOR.value:
            actual_surveyor_id = current_user.id

        items, total = await survey_assignment_repository.list(
            db=db,
            surveyor_id=actual_surveyor_id,
            survey_project_id=survey_project_id,
            jurisdiction_id=jurisdiction_id,
            status=status,
            priority=priority,
            skip=skip,
            limit=limit,
        )

        details = [self._format_assignment_detail(a) for a in items]
        return details, total

    async def get_assignment(
        self,
        db: AsyncSession,
        assignment_id: uuid.UUID,
        current_user: User,
    ) -> SurveyAssignmentDetailResponse:
        assignment = await survey_assignment_repository.get_by_id(db, assignment_id)
        if not assignment:
            raise NotFoundException(f"Survey assignment with ID '{assignment_id}' not found")

        # Authorization check: surveyors only access their own assignments
        if current_user.role == UserRole.SURVEYOR.value and assignment.surveyor_id != current_user.id:
            raise ForbiddenException("You are not authorized to access this survey assignment")

        return self._format_assignment_detail(assignment)

    def _format_assignment_detail(self, assignment: SurveyAssignment) -> SurveyAssignmentDetailResponse:
        resp = SurveyAssignmentDetailResponse.model_validate(assignment)
        if assignment.project:
            resp.project_name = assignment.project.name
            resp.project_code = assignment.project.code
        if assignment.surveyor:
            resp.surveyor_name = assignment.surveyor.full_name
            resp.surveyor_email = assignment.surveyor.email
        if assignment.jurisdiction:
            resp.jurisdiction_name = assignment.jurisdiction.name
        if assignment.parcel:
            resp.parcel_code = assignment.parcel.parcel_code
        if assignment.property:
            resp.property_reference = assignment.property.property_reference
        if assignment.building:
            resp.building_reference = assignment.building.building_reference
        if assignment.floor:
            resp.floor_code = assignment.floor.floor_code
        from sqlalchemy import inspect
        ins = inspect(assignment)
        resp.sessions_count = len(assignment.sessions) if "sessions" not in ins.unloaded and assignment.sessions else 0
        resp.submissions_count = len(assignment.submissions) if "submissions" not in ins.unloaded and assignment.submissions else 0
        return resp

    async def accept_assignment(
        self,
        db: AsyncSession,
        assignment_id: uuid.UUID,
        current_user: User,
        request: Optional[Request] = None,
    ) -> SurveyAssignmentDetailResponse:
        assignment = await survey_assignment_repository.get_by_id(db, assignment_id)
        if not assignment:
            raise NotFoundException(f"Survey assignment '{assignment_id}' not found")

        if current_user.role == UserRole.SURVEYOR.value and assignment.surveyor_id != current_user.id:
            raise ForbiddenException("You cannot accept an assignment assigned to another surveyor")

        survey_state_machine.validate_assignment_transition(assignment.status, "ACCEPTED")

        updated = await survey_assignment_repository.update(db, assignment.id, {"status": "ACCEPTED"})

        await audit_repository.log_event(
            db=db,
            actor_user_id=current_user.id,
            action="SURVEY_ACCEPTED",
            entity_type="SURVEY_ASSIGNMENT",
            entity_id=str(assignment.id),
            details={"previous_status": assignment.status, "new_status": "ACCEPTED"},
            ip_address=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
        )

        return await self.get_assignment(db, updated.id, current_user)

    async def start_survey(
        self,
        db: AsyncSession,
        assignment_id: uuid.UUID,
        current_user: User,
        request: Optional[Request] = None,
    ) -> SurveySessionDetailResponse:
        assignment = await survey_assignment_repository.get_by_id(db, assignment_id)
        if not assignment:
            raise NotFoundException(f"Survey assignment '{assignment_id}' not found")

        if current_user.role == UserRole.SURVEYOR.value and assignment.surveyor_id != current_user.id:
            raise ForbiddenException("You cannot start a survey assigned to another surveyor")

        # Check existing active session
        existing_session = await survey_session_repository.get_active_session_for_assignment(db, assignment_id)
        if existing_session:
            return await self.get_session(db, existing_session.id, current_user)

        # Transition assignment if ACCEPTED or REVISION_REQUIRED
        if assignment.status in ["ACCEPTED", "REVISION_REQUIRED", "ASSIGNED"]:
            survey_state_machine.validate_assignment_transition(assignment.status, "IN_PROGRESS")
            await survey_assignment_repository.update(
                db,
                assignment.id,
                {"status": "IN_PROGRESS", "started_at": datetime.now(timezone.utc)},
            )

        # Create new active survey session
        session = await survey_session_repository.create(
            db=db,
            data={
                "assignment_id": assignment.id,
                "surveyor_id": current_user.id,
                "status": "ACTIVE",
                "sync_status": "SYNCED",
                "app_version": "1.0.0",
            },
        )

        await audit_repository.log_event(
            db=db,
            actor_user_id=current_user.id,
            action="SURVEY_STARTED",
            entity_type="SURVEY_SESSION",
            entity_id=str(session.id),
            details={"assignment_id": str(assignment.id)},
            ip_address=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
        )

        return await self.get_session(db, session.id, current_user)

    # ------------------------------------------------------------------------
    # Survey Sessions & Observations
    # ------------------------------------------------------------------------

    async def get_session(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        current_user: User,
    ) -> SurveySessionDetailResponse:
        session = await survey_session_repository.get_by_id(db, session_id)
        if not session:
            raise NotFoundException(f"Survey session '{session_id}' not found")

        if current_user.role == UserRole.SURVEYOR.value and session.surveyor_id != current_user.id:
            raise ForbiddenException("You are not authorized to view this survey session")

        resp = SurveySessionDetailResponse.model_validate(session)
        if session.assignment:
            resp.assignment = self._format_assignment_detail(session.assignment)
        resp.observations_count = len(session.observations)
        resp.evidence_count = len(session.evidence)
        return resp

    async def pause_session(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        current_user: User,
        request: Optional[Request] = None,
    ) -> SurveySessionDetailResponse:
        session = await survey_session_repository.get_by_id(db, session_id)
        if not session:
            raise NotFoundException(f"Survey session '{session_id}' not found")
        if current_user.role == UserRole.SURVEYOR.value and session.surveyor_id != current_user.id:
            raise ForbiddenException("Unauthorized")

        survey_state_machine.validate_session_transition(session.status, "PAUSED")
        updated = await survey_session_repository.update(db, session.id, {"status": "PAUSED"})

        await audit_repository.log_event(
            db=db,
            actor_user_id=current_user.id,
            action="SURVEY_PAUSED",
            entity_type="SURVEY_SESSION",
            entity_id=str(session.id),
            details={"assignment_id": str(session.assignment_id)},
            ip_address=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
        )

        return await self.get_session(db, updated.id, current_user)

    async def resume_session(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        current_user: User,
        request: Optional[Request] = None,
    ) -> SurveySessionDetailResponse:
        session = await survey_session_repository.get_by_id(db, session_id)
        if not session:
            raise NotFoundException(f"Survey session '{session_id}' not found")
        if current_user.role == UserRole.SURVEYOR.value and session.surveyor_id != current_user.id:
            raise ForbiddenException("Unauthorized")

        survey_state_machine.validate_session_transition(session.status, "ACTIVE")
        updated = await survey_session_repository.update(db, session.id, {"status": "ACTIVE"})

        await audit_repository.log_event(
            db=db,
            actor_user_id=current_user.id,
            action="SURVEY_RESUMED",
            entity_type="SURVEY_SESSION",
            entity_id=str(session.id),
            details={"assignment_id": str(session.assignment_id)},
            ip_address=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
        )

        return await self.get_session(db, updated.id, current_user)

    async def create_observation(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        data: SurveyObservationCreate,
        current_user: User,
        request: Optional[Request] = None,
    ) -> SurveyObservationResponse:
        session = await survey_session_repository.get_by_id(db, session_id)
        if not session:
            raise NotFoundException(f"Survey session '{session_id}' not found")
        if current_user.role == UserRole.SURVEYOR.value and session.surveyor_id != current_user.id:
            raise ForbiddenException("Unauthorized")

        obs_dict = data.model_dump()
        obs_dict["session_id"] = session_id

        # Parse geometry if present
        geom_wkt = None
        if data.geometry:
            parsed = GeometryEngine.parse_geometry(data.geometry)
            geom_wkt = GeometryEngine.to_wkt(parsed)
            obs_dict["geometry"] = geom_wkt
            obs_dict["geometry_wkt"] = geom_wkt
        else:
            obs_dict["geometry"] = None
            obs_dict["geometry_wkt"] = None

        obs = await survey_observation_repository.create(
            db=db,
            data=obs_dict,
            captured_by=current_user.id,
        )

        await audit_repository.log_event(
            db=db,
            actor_user_id=current_user.id,
            action="OBSERVATION_CREATED",
            entity_type="SURVEY_OBSERVATION",
            entity_id=str(obs.id),
            details={"type": obs.observation_type, "value": obs.value, "target_type": obs.target_type},
            ip_address=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
        )

        return SurveyObservationResponse.model_validate(obs)

    async def list_observations(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        current_user: User,
    ) -> List[SurveyObservationResponse]:
        session = await survey_session_repository.get_by_id(db, session_id)
        if not session:
            raise NotFoundException(f"Survey session '{session_id}' not found")
        if current_user.role == UserRole.SURVEYOR.value and session.surveyor_id != current_user.id:
            raise ForbiddenException("Unauthorized")

        items = await survey_observation_repository.list_by_session(db, session_id)
        return [SurveyObservationResponse.model_validate(o) for o in items]

    # ------------------------------------------------------------------------
    # Evidence & Protected Storage
    # ------------------------------------------------------------------------

    async def upload_evidence(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        file: UploadFile,
        evidence_type: str,
        target_type: str,
        target_id: str,
        description: Optional[str],
        latitude: Optional[float],
        longitude: Optional[float],
        accuracy: Optional[float],
        observation_id: Optional[uuid.UUID],
        current_user: User,
        request: Optional[Request] = None,
    ) -> SurveyEvidenceResponse:
        session = await survey_session_repository.get_by_id(db, session_id)
        if not session:
            raise NotFoundException(f"Survey session '{session_id}' not found")
        if current_user.role == UserRole.SURVEYOR.value and session.surveyor_id != current_user.id:
            raise ForbiddenException("Unauthorized")

        storage_key, filename, file_size, sha256_hash = await storage_service.save_evidence_file(
            session_id=session_id,
            file=file,
        )

        evidence = await survey_evidence_repository.create(
            db=db,
            data={
                "session_id": session_id,
                "observation_id": observation_id,
                "target_type": target_type,
                "target_id": target_id,
                "storage_key": storage_key,
                "filename": filename,
                "mime_type": file.content_type or "image/jpeg",
                "file_size": file_size,
                "evidence_type": evidence_type,
                "latitude": latitude,
                "longitude": longitude,
                "accuracy": accuracy,
                "description": description,
                "sha256_hash": sha256_hash,
            },
            uploaded_by=current_user.id,
        )

        await audit_repository.log_event(
            db=db,
            actor_user_id=current_user.id,
            action="EVIDENCE_UPLOADED",
            entity_type="SURVEY_EVIDENCE",
            entity_id=str(evidence.id),
            details={
                "filename": filename,
                "size_bytes": file_size,
                "sha256": sha256_hash,
                "evidence_type": evidence_type,
            },
            ip_address=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
        )

        return SurveyEvidenceResponse.model_validate(evidence)

    async def list_evidence(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        current_user: User,
    ) -> List[SurveyEvidenceResponse]:
        session = await survey_session_repository.get_by_id(db, session_id)
        if not session:
            raise NotFoundException(f"Survey session '{session_id}' not found")
        if current_user.role == UserRole.SURVEYOR.value and session.surveyor_id != current_user.id:
            raise ForbiddenException("Unauthorized")

        items = await survey_evidence_repository.list_by_session(db, session_id)
        return [SurveyEvidenceResponse.model_validate(e) for e in items]

    async def get_evidence_file_info(
        self,
        db: AsyncSession,
        evidence_id: uuid.UUID,
        current_user: User,
    ) -> Tuple[Any, str, str]:
        evidence = await survey_evidence_repository.get_by_id(db, evidence_id)
        if not evidence:
            raise NotFoundException(f"Survey evidence '{evidence_id}' not found")

        path = storage_service.get_file_path(evidence.storage_key)
        return path, evidence.mime_type, evidence.filename

    # ------------------------------------------------------------------------
    # Validation & Submission
    # ------------------------------------------------------------------------

    async def validate_session(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        current_user: User,
    ) -> SurveyValidationSummary:
        session = await survey_session_repository.get_by_id(db, session_id)
        if not session:
            raise NotFoundException(f"Survey session '{session_id}' not found")
        if current_user.role == UserRole.SURVEYOR.value and session.surveyor_id != current_user.id:
            raise ForbiddenException("Unauthorized")

        return await survey_validation_service.validate_session(db, session_id)

    async def submit_survey(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        current_user: User,
        request: Optional[Request] = None,
    ) -> SurveySubmissionResponse:
        session = await survey_session_repository.get_by_id(db, session_id)
        if not session:
            raise NotFoundException(f"Survey session '{session_id}' not found")
        if current_user.role == UserRole.SURVEYOR.value and session.surveyor_id != current_user.id:
            raise ForbiddenException("You cannot submit a survey session collected by another surveyor")

        assignment = session.assignment
        if not assignment:
            raise NotFoundException(f"Assignment for session '{session_id}' not found")

        # Run validation check
        validation = await survey_validation_service.validate_session(db, session_id)
        if not validation.can_submit:
            error_msgs = [i.message for i in validation.issues if i.severity == "ERROR"]
            raise BadRequestException(f"Survey cannot be submitted due to blocking errors: {'; '.join(error_msgs)}")

        # Determine version number (increment if revision)
        latest_sub = await survey_submission_repository.get_latest_by_assignment(db, assignment.id)
        version_number = (latest_sub.version_number + 1) if latest_sub else 1

        # Freeze immutable snapshot of all field observations, coordinates, and evidence
        observations = await survey_observation_repository.list_by_session(db, session_id)
        evidence_items = await survey_evidence_repository.list_by_session(db, session_id)

        snapshot = {
            "version_number": version_number,
            "session_id": str(session.id),
            "assignment_id": str(assignment.id),
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "submitted_by": str(current_user.id),
            "observations": [
                {
                    "id": str(o.id),
                    "type": o.observation_type,
                    "target_type": o.target_type,
                    "target_id": o.target_id,
                    "value": o.value,
                    "unit": o.unit,
                    "latitude": o.latitude,
                    "longitude": o.longitude,
                    "accuracy": o.horizontal_accuracy,
                    "source": o.source,
                }
                for o in observations
            ],
            "evidence": [
                {
                    "id": str(e.id),
                    "filename": e.filename,
                    "type": e.evidence_type,
                    "sha256": e.sha256_hash,
                    "latitude": e.latitude,
                    "longitude": e.longitude,
                }
                for e in evidence_items
            ],
            "validation_summary": validation.model_dump(),
        }

        # Transition assignment & session state
        survey_state_machine.validate_assignment_transition(assignment.status, "SUBMITTED")
        survey_state_machine.validate_session_transition(session.status, "SUBMITTED")

        await survey_assignment_repository.update(db, assignment.id, {"status": "SUBMITTED"})
        await survey_session_repository.update(db, session.id, {"status": "SUBMITTED", "ended_at": datetime.now(timezone.utc)})

        submission = await survey_submission_repository.create(
            db=db,
            data={
                "assignment_id": assignment.id,
                "survey_session_id": session.id,
                "version_number": version_number,
                "status": "SUBMITTED",
                "snapshot_data": json.dumps(snapshot),
                "submitted_by": current_user.id,
                "submitted_at": datetime.now(timezone.utc),
            },
        )

        await audit_repository.log_event(
            db=db,
            actor_user_id=current_user.id,
            action="SURVEY_SUBMITTED",
            entity_type="SURVEY_SUBMISSION",
            entity_id=str(submission.id),
            details={
                "version_number": version_number,
                "assignment_id": str(assignment.id),
                "observations_count": len(observations),
                "evidence_count": len(evidence_items),
            },
            ip_address=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
        )

        return SurveySubmissionResponse.model_validate(submission)

    # ------------------------------------------------------------------------
    # Officer Review & Adjudication
    # ------------------------------------------------------------------------

    async def list_submissions(
        self,
        db: AsyncSession,
        current_user: User,
        assignment_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[SurveySubmissionResponse], int]:
        items, total = await survey_submission_repository.list(
            db=db,
            assignment_id=assignment_id,
            status=status,
            skip=skip,
            limit=limit,
        )
        return [SurveySubmissionResponse.model_validate(s) for s in items], total

    async def get_submission(
        self,
        db: AsyncSession,
        submission_id: uuid.UUID,
        current_user: User,
    ) -> SurveySubmissionResponse:
        sub = await survey_submission_repository.get_by_id(db, submission_id)
        if not sub:
            raise NotFoundException(f"Survey submission '{submission_id}' not found")
        return SurveySubmissionResponse.model_validate(sub)

    async def review_submission(
        self,
        db: AsyncSession,
        submission_id: uuid.UUID,
        action: str,  # approve, request-revision, reject
        review_notes: Optional[str],
        current_user: User,
        request: Optional[Request] = None,
    ) -> SurveySubmissionResponse:
        sub = await survey_submission_repository.get_by_id(db, submission_id)
        if not sub:
            raise NotFoundException(f"Survey submission '{submission_id}' not found")

        assignment = sub.assignment
        if not assignment:
            raise NotFoundException("Associated survey assignment not found")

        # Capture scalar attributes before any repository commit
        sub_id = sub.id
        sub_version = sub.version_number
        assignment_id = assignment.id
        assignment_status = assignment.status

        # Target statuses mapping
        status_map = {
            "approve": "APPROVED",
            "request-revision": "REVISION_REQUIRED",
            "reject": "REJECTED",
        }
        next_status = status_map.get(action.lower())
        if not next_status:
            raise BadRequestException(f"Invalid review action '{action}'. Must be approve, request-revision, or reject.")

        if next_status in ["REVISION_REQUIRED", "REJECTED"] and (not review_notes or not review_notes.strip()):
            raise BadRequestException(f"Review notes are mandatory when action is '{action}'.")

        # Verify legal transitions
        survey_state_machine.validate_assignment_transition(assignment_status, next_status)

        # Update assignment
        completed_at = datetime.now(timezone.utc) if next_status == "APPROVED" else None
        asgn_update: Dict[str, Any] = {"status": next_status, "completed_at": completed_at}
        if next_status == "REVISION_REQUIRED" and review_notes:
            asgn_update["notes"] = f"Revision requested: {review_notes}"
        await survey_assignment_repository.update(
            db,
            assignment_id,
            asgn_update,
        )

        # Update submission record
        updated_sub = await survey_submission_repository.update(
            db,
            sub_id,
            {
                "status": next_status,
                "reviewed_by": current_user.id,
                "reviewed_at": datetime.now(timezone.utc),
                "review_notes": review_notes,
            },
        )

        # Audit event
        audit_action_map = {
            "APPROVED": "SURVEY_APPROVED",
            "REVISION_REQUIRED": "SURVEY_REVISION_REQUESTED",
            "REJECTED": "SURVEY_REJECTED",
        }
        await audit_repository.log_event(
            db=db,
            actor_user_id=current_user.id,
            action=audit_action_map[next_status],
            entity_type="SURVEY_SUBMISSION",
            entity_id=str(sub_id),
            details={
                "assignment_id": str(assignment_id),
                "version_number": sub_version,
                "review_notes": review_notes,
            },
            ip_address=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
        )

        return SurveySubmissionResponse.model_validate(updated_sub)

    # ------------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------------

    async def export_assignment(
        self,
        db: AsyncSession,
        assignment_id: uuid.UUID,
        current_user: User,
    ) -> SurveyExportData:
        assignment_detail = await self.get_assignment(db, assignment_id, current_user)
        sessions = await survey_session_repository.list_by_assignment(db, assignment_id)

        all_observations: List[SurveyObservationResponse] = []
        all_evidence: List[SurveyEvidenceResponse] = []
        for s in sessions:
            obs = await survey_observation_repository.list_by_session(db, s.id)
            all_observations.extend([SurveyObservationResponse.model_validate(o) for o in obs])
            ev = await survey_evidence_repository.list_by_session(db, s.id)
            all_evidence.extend([SurveyEvidenceResponse.model_validate(e) for e in ev])

        submissions = assignment_detail.submissions_count
        latest_session_id = sessions[0].id if sessions else None
        validation = None
        if latest_session_id:
            validation = await survey_validation_service.validate_session(db, latest_session_id)

        items_sub, _ = await survey_submission_repository.list(db, assignment_id=assignment_id)

        return SurveyExportData(
            assignment=assignment_detail,
            sessions=[SurveySessionResponse.model_validate(s) for s in sessions],
            observations=all_observations,
            evidence_metadata=all_evidence,
            submissions=[SurveySubmissionResponse.model_validate(s) for s in items_sub],
            validation_summary=validation,
        )


survey_service = SurveyService()
