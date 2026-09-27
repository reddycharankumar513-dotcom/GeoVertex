from datetime import datetime
from typing import Any, Dict, List, Optional


class TimelineEntry:
    def __init__(
        self,
        entry_id: str,
        entry_type: str,  # SNAPSHOT, SURVEY, DOCUMENT, CHANGE_CANDIDATE
        date: datetime,
        date_precision: str,
        source: str,
        title: str,
        description: str,
        attributes: Dict[str, Any],
        geometry_wkt: Optional[str] = None,
        status: Optional[str] = None,
    ):
        self.entry_id = entry_id
        self.entry_type = entry_type
        self.date = date
        self.date_precision = date_precision
        self.source = source
        self.title = title
        self.description = description
        self.attributes = attributes
        self.geometry_wkt = geometry_wkt
        self.status = status

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "entry_type": self.entry_type,
            "date": self.date.isoformat() if self.date else None,
            "date_precision": self.date_precision,
            "source": self.source,
            "title": self.title,
            "description": self.description,
            "attributes": self.attributes,
            "geometry_wkt": self.geometry_wkt,
            "status": self.status,
        }


class EntityTimelineBuilder:
    """Constructs a chronologically sorted temporal timeline from actual snapshots, surveys, and changes."""

    @classmethod
    def build_timeline(
        cls,
        snapshots: List[Any],
        changes: Optional[List[Any]] = None,
        surveys: Optional[List[Any]] = None,
        documents: Optional[List[Any]] = None,
    ) -> List[Dict[str, Any]]:
        entries: List[TimelineEntry] = []

        # 1. Snapshots
        for snap in snapshots:
            date = snap.observation_date or snap.effective_from or snap.created_at
            entries.append(
                TimelineEntry(
                    entry_id=str(snap.id),
                    entry_type="SNAPSHOT",
                    date=date,
                    date_precision=getattr(snap, "date_precision", "EXACT"),
                    source=snap.source_type,
                    title=f"Snapshot ({snap.snapshot_type})",
                    description=f"Version {snap.version_number} recorded via {snap.source_type}",
                    attributes=snap.attributes_json or {},
                    geometry_wkt=snap.geometry_wkt,
                    status="CURRENT" if snap.is_current else "HISTORICAL",
                )
            )

        # 2. Change Candidates
        if changes:
            for ch in changes:
                date = ch.comparison_date or ch.created_at
                entries.append(
                    TimelineEntry(
                        entry_id=str(ch.id),
                        entry_type="CHANGE_CANDIDATE",
                        date=date,
                        date_precision="EXACT",
                        source=f"Detection Run {str(ch.detection_run_id)[:8]}",
                        title=f"Detected Change: {ch.change_type}",
                        description=f"{ch.significance} significance change detected via run",
                        attributes=ch.magnitude or {},
                        geometry_wkt=ch.geometry_wkt,
                        status=ch.status,
                    )
                )

        # 3. Field Surveys
        if surveys:
            for s in surveys:
                date = getattr(s, "observation_timestamp", None) or getattr(s, "created_at", None)
                if date:
                    entries.append(
                        TimelineEntry(
                            entry_id=str(s.id),
                            entry_type="SURVEY",
                            date=date,
                            date_precision="EXACT",
                            source="FIELD_SURVEY",
                            title=f"Field Survey Observation",
                            description=f"Height: {getattr(s, 'height_m', 'N/A')}m, Floors: {getattr(s, 'floor_count', 'N/A')}",
                            attributes={
                                "height_m": getattr(s, "height_m", None),
                                "floor_count": getattr(s, "floor_count", None),
                                "gps_quality": getattr(s, "gps_quality", None),
                            },
                            geometry_wkt=getattr(s, "geometry_wkt", None),
                            status=getattr(s, "status", "RECORDED"),
                        )
                    )

        # 4. Documents
        if documents:
            for d in documents:
                date = getattr(d, "document_date", None) or getattr(d, "created_at", None)
                if date:
                    entries.append(
                        TimelineEntry(
                            entry_id=str(d.id),
                            entry_type="DOCUMENT",
                            date=date,
                            date_precision="EXACT",
                            source=getattr(d, "document_type", "LEGAL_RECORD"),
                            title=getattr(d, "title", "Property Document"),
                            description=f"Doc No: {getattr(d, 'document_number', 'N/A')}",
                            attributes=getattr(d, "metadata_json", {}) or {},
                            status=getattr(d, "status", "VERIFIED"),
                        )
                    )

        # Sort chronologically (oldest to newest)
        entries.sort(key=lambda e: e.date or datetime.min)
        return [e.to_dict() for e in entries]
