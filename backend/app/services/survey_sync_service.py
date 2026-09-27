import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.survey import SyncOperation
from app.repositories.survey_repository import (
    survey_session_repository,
    survey_observation_repository,
    sync_operation_repository,
)
from app.schemas.survey import (
    SyncOperationBatchRequest,
    SyncOperationBatchResponse,
    SyncOperationItemResult,
)


class SurveySyncService:
    """Processes offline synchronization operation queues idempotently with conflict detection."""

    async def process_batch(
        self,
        db: AsyncSession,
        batch_request: SyncOperationBatchRequest,
        surveyor_id: uuid.UUID,
    ) -> SyncOperationBatchResponse:
        results: List[SyncOperationItemResult] = []
        synced_count = 0
        conflict_count = 0
        failed_count = 0

        for item in batch_request.operations:
            # 1. Idempotency Check
            existing_op = await sync_operation_repository.get_by_client_id(db, item.client_operation_id)
            if existing_op:
                results.append(
                    SyncOperationItemResult(
                        client_operation_id=item.client_operation_id,
                        status=existing_op.status,
                        entity_id=existing_op.entity_id,
                        server_id=existing_op.entity_id if existing_op.status == "SYNCED" else None,
                        error=existing_op.error_message,
                    )
                )
                if existing_op.status == "SYNCED":
                    synced_count += 1
                elif existing_op.status == "CONFLICT":
                    conflict_count += 1
                else:
                    failed_count += 1
                continue

            # 2. Conflict & State Checks
            session = None
            if item.session_id:
                session = await survey_session_repository.get_by_id(db, item.session_id)
                if session:
                    # Check assignment status
                    if session.assignment and session.assignment.status in ["APPROVED", "REJECTED", "CANCELLED"]:
                        conflict_op = await sync_operation_repository.create(
                            db,
                            {
                                "client_operation_id": item.client_operation_id,
                                "session_id": item.session_id,
                                "operation_type": item.operation_type,
                                "entity_type": item.entity_type,
                                "entity_id": item.entity_id,
                                "payload": json.dumps(item.payload),
                                "status": "CONFLICT",
                                "attempt_count": 1,
                                "last_attempt_at": datetime.now(timezone.utc),
                                "error_message": f"Assignment is in terminal state '{session.assignment.status}'. Mutations rejected.",
                            },
                        )
                        results.append(
                            SyncOperationItemResult(
                                client_operation_id=item.client_operation_id,
                                status="CONFLICT",
                                entity_id=item.entity_id,
                                error=f"Assignment is in terminal state '{session.assignment.status}'. Mutations rejected.",
                            )
                        )
                        conflict_count += 1
                        continue

            # 3. Execute Operations
            try:
                if item.operation_type == "CREATE_OBSERVATION":
                    if not item.session_id:
                        raise ValueError("Missing session_id for CREATE_OBSERVATION")
                    obs_data = dict(item.payload)
                    obs_data["session_id"] = item.session_id
                    obs = await survey_observation_repository.create(
                        db,
                        obs_data,
                        captured_by=surveyor_id,
                    )
                    await sync_operation_repository.create(
                        db,
                        {
                            "client_operation_id": item.client_operation_id,
                            "session_id": item.session_id,
                            "operation_type": item.operation_type,
                            "entity_type": "survey_observation",
                            "entity_id": str(obs.id),
                            "payload": json.dumps(item.payload),
                            "status": "SYNCED",
                            "attempt_count": 1,
                            "last_attempt_at": datetime.now(timezone.utc),
                        },
                    )
                    results.append(
                        SyncOperationItemResult(
                            client_operation_id=item.client_operation_id,
                            status="SYNCED",
                            entity_id=item.entity_id,
                            server_id=str(obs.id),
                        )
                    )
                    synced_count += 1

                elif item.operation_type == "UPDATE_OBSERVATION":
                    target_uuid = uuid.UUID(item.entity_id)
                    updated = await survey_observation_repository.update(db, target_uuid, item.payload)
                    if not updated:
                        raise ValueError(f"Observation {item.entity_id} not found")
                    await sync_operation_repository.create(
                        db,
                        {
                            "client_operation_id": item.client_operation_id,
                            "session_id": item.session_id,
                            "operation_type": item.operation_type,
                            "entity_type": "survey_observation",
                            "entity_id": str(updated.id),
                            "payload": json.dumps(item.payload),
                            "status": "SYNCED",
                            "attempt_count": 1,
                            "last_attempt_at": datetime.now(timezone.utc),
                        },
                    )
                    results.append(
                        SyncOperationItemResult(
                            client_operation_id=item.client_operation_id,
                            status="SYNCED",
                            entity_id=item.entity_id,
                            server_id=str(updated.id),
                        )
                    )
                    synced_count += 1

                elif item.operation_type == "UPDATE_SESSION":
                    if not item.session_id:
                        raise ValueError("Missing session_id for UPDATE_SESSION")
                    updated_session = await survey_session_repository.update(db, item.session_id, item.payload)
                    await sync_operation_repository.create(
                        db,
                        {
                            "client_operation_id": item.client_operation_id,
                            "session_id": item.session_id,
                            "operation_type": item.operation_type,
                            "entity_type": "survey_session",
                            "entity_id": str(item.session_id),
                            "payload": json.dumps(item.payload),
                            "status": "SYNCED",
                            "attempt_count": 1,
                            "last_attempt_at": datetime.now(timezone.utc),
                        },
                    )
                    results.append(
                        SyncOperationItemResult(
                            client_operation_id=item.client_operation_id,
                            status="SYNCED",
                            entity_id=item.entity_id,
                            server_id=str(item.session_id),
                        )
                    )
                    synced_count += 1

                else:
                    raise ValueError(f"Unsupported sync operation_type: {item.operation_type}")

            except Exception as e:
                err_msg = str(e)
                await sync_operation_repository.create(
                    db,
                    {
                        "client_operation_id": item.client_operation_id,
                        "session_id": item.session_id,
                        "operation_type": item.operation_type,
                        "entity_type": item.entity_type,
                        "entity_id": item.entity_id,
                        "payload": json.dumps(item.payload),
                        "status": "FAILED",
                        "attempt_count": 1,
                        "last_attempt_at": datetime.now(timezone.utc),
                        "error_message": err_msg,
                    },
                )
                results.append(
                    SyncOperationItemResult(
                        client_operation_id=item.client_operation_id,
                        status="FAILED",
                        entity_id=item.entity_id,
                        error=err_msg,
                    )
                )
                failed_count += 1

        return SyncOperationBatchResponse(
            results=results,
            total_processed=len(batch_request.operations),
            synced_count=synced_count,
            conflict_count=conflict_count,
            failed_count=failed_count,
        )


survey_sync_service = SurveySyncService()
