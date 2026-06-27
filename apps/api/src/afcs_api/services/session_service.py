"""Service layer for simulation session operations."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

from afcs_case_schema import CaseDefinition
from afcs_case_schema.loader import load_case_dir
from afcs_domain import (
    SessionStatus,
    SimulationEvent,
    SimulationSession,
)
from afcs_simulation_engine import ActionRegistry, StateTransitionEngine
from sqlalchemy import select
from sqlalchemy.orm import Session as SASession

from afcs_api.models import CaseRecord, EventRecord, SessionRecord

# ---------------------------------------------------------------------------
# Case cache (simple in-memory for now)
# ---------------------------------------------------------------------------

_DEFAULT_CASE_DIR = Path(__file__).resolve().parents[5] / "cases"
_case_cache: dict[str, CaseDefinition] = {}


def _is_uuid(value: str) -> bool:
    """Check if a string is a valid UUID."""
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError):
        return False


def _load_case(case_id: str) -> CaseDefinition:
    """Load and cache a case definition by its case_id."""
    if case_id in _case_cache:
        return _case_cache[case_id]

    if not _DEFAULT_CASE_DIR.is_dir():
        raise FileNotFoundError(f"Cases directory not found: {_DEFAULT_CASE_DIR}")

    # Search all subdirectories for the matching case_id
    found = None
    for subdir in sorted(_DEFAULT_CASE_DIR.iterdir()):
        if not subdir.is_dir():
            continue
        try:
            cases_in_dir = load_case_dir(subdir)
        except (FileNotFoundError, ValueError, NotADirectoryError):
            continue
        for c in cases_in_dir:
            _case_cache[c.metadata.case_id] = c
            if c.metadata.case_id == case_id:
                found = c

    if found is None:
        raise ValueError(f"Case '{case_id}' not found. Available: {list(_case_cache.keys())}")

    return found


def _get_engine(case_id: str) -> StateTransitionEngine:
    """Get or create a StateTransitionEngine for the given case."""
    case = _load_case(case_id)
    registry = ActionRegistry()
    registry.register_from_builtins()
    return StateTransitionEngine(case=case, action_registry=registry)


# ---------------------------------------------------------------------------
# Canonical <-> SQL helpers
# ---------------------------------------------------------------------------


def _record_to_domain(record: SessionRecord) -> SimulationSession:
    """Convert a SessionRecord ORM row to a domain SimulationSession."""
    return SimulationSession(
        id=record.id,
        case_id=record.case_id,
        case_version=record.case_version,
        participant_id=record.participant_id,
        status=SessionStatus(record.status) if record.status else SessionStatus.CREATED,
        current_state=record.current_state or {},
        current_sequence=record.current_sequence,
        started_at=record.started_at or datetime.now(UTC),
        completed_at=record.completed_at,
    )


def _domain_to_record(session: SimulationSession) -> dict:
    """Convert domain fields back to a dict for ORM update."""
    return {
        "status": session.status.value,
        "current_state": session.current_state,
        "current_sequence": session.current_sequence,
        "completed_at": session.completed_at,
    }


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class SessionService:
    """Business logic for simulation session lifecycle."""

    def __init__(self, db: SASession) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create_session(
        self, case_id: str, participant_id: str | None = None
    ) -> tuple[SessionRecord, dict]:
        """Create a new session for the given case, returning (record, visible_state)."""
        engine = _get_engine(case_id)
        case = engine.case

        # Build domain session and initialise it
        participant_uuid = (
            uuid.UUID(participant_id)
            if participant_id and _is_uuid(participant_id)
            else uuid.uuid4()
        )
        domain_session = SimulationSession(
            case_id=case_id,
            case_version=case.metadata.version,
            participant_id=participant_uuid,
        )
        engine.initialise_session(domain_session)

        # Persist as SessionRecord
        record = SessionRecord(
            id=domain_session.id,
            case_id=case_id,
            case_version=case.metadata.version,
            participant_id=str(domain_session.participant_id)
            if domain_session.participant_id
            else None,
            status=domain_session.status.value,
            current_state=domain_session.current_state,
            current_sequence=domain_session.current_sequence,
            started_at=domain_session.started_at,
            completed_at=domain_session.completed_at,
        )
        self._db.add(record)
        self._db.flush()

        # Also persist the case record if not already present
        existing = self._db.execute(
            select(CaseRecord).where(
                CaseRecord.case_id == case_id,
                CaseRecord.version == case.metadata.version,
            )
        ).scalar_one_or_none()

        if existing is None:
            case_record = CaseRecord(
                case_id=case_id,
                version=case.metadata.version,
                title=case.metadata.title,
                domain=case.metadata.domain,
                difficulty=case.metadata.difficulty.value,
                schema_json=case.model_dump(mode="json"),
            )
            self._db.add(case_record)
            self._db.flush()

        # Project visible state
        visible_state = self.get_visible_state(record)

        return record, visible_state

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_session(self, session_id: uuid.UUID) -> SessionRecord | None:
        """Fetch a session record by ID."""
        return self._db.get(SessionRecord, session_id)

    def get_visible_state(self, session: SessionRecord) -> dict:
        """Project canonical state to participant-visible state."""
        # CanonicalState has extra='forbid', so we extract only known visible fields
        state = session.current_state
        visible = {
            "phase": state.get("phase", "unknown"),
            "budget_remaining": state.get("budget_remaining", 0.0),
            "artifacts": state.get("artifacts", []),
            "stakeholder_relationships": state.get("stakeholder_relationships", {}),
            "flags": state.get("flags", {}),
            "metadata": state.get("metadata", {}),
        }
        return visible

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def execute_action(
        self,
        session: SessionRecord,
        action_type: str,
        params: dict,
    ) -> tuple[EventRecord, SessionRecord]:
        """Validate and execute an action, returning (event_record, updated_session)."""
        engine = _get_engine(session.case_id)
        domain_session = _record_to_domain(session)

        # Execute — raises PreconditionError/InvalidActionError on failure
        event, updated_domain = engine.execute_action(domain_session, action_type, params)

        # Persist the event
        event_record = self._persist_event(event, session.id)

        # Update the session record
        update_data = _domain_to_record(updated_domain)
        for key, value in update_data.items():
            setattr(session, key, value)
        self._db.flush()

        return event_record, session

    def _persist_event(self, event: SimulationEvent, session_id: uuid.UUID) -> EventRecord:
        """Convert a domain SimulationEvent to an EventRecord and persist it."""
        record = EventRecord(
            id=event.event_id,
            session_id=session_id,
            sequence=event.sequence,
            event_type=event.event_type,
            actor_type=event.actor_type,
            actor_id=event.actor_id,
            payload=event.payload,
            pre_state_hash=event.pre_state_hash,
            post_state_hash=event.post_state_hash,
            created_at=event.timestamp,
        )
        self._db.add(record)
        self._db.flush()
        return record

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def get_events(
        self, session_id: uuid.UUID, from_sequence: int = 0, limit: int = 50
    ) -> list[EventRecord]:
        """Retrieve events for a session from a given sequence offset."""
        stmt = (
            select(EventRecord)
            .where(
                EventRecord.session_id == session_id,
                EventRecord.sequence >= from_sequence,
            )
            .order_by(EventRecord.sequence)
            .limit(limit)
        )
        result = self._db.execute(stmt)
        return list(result.scalars().all())

    def count_events(self, session_id: uuid.UUID) -> int:
        """Count total events for a session."""
        stmt = select(EventRecord).where(EventRecord.session_id == session_id)
        result = self._db.execute(stmt)
        return len(list(result.scalars().all()))

    # ------------------------------------------------------------------
    # Action schemas
    # ------------------------------------------------------------------

    def get_available_actions(self, session: SessionRecord) -> list[dict]:
        """Return available actions with schemas for the session's current state."""
        engine = _get_engine(session.case_id)
        case = engine.case
        registry = engine.registry
        domain_session = _record_to_domain(session)
        return registry.get_available_actions(domain_session, case)

    # ------------------------------------------------------------------
    # Artifacts
    # ------------------------------------------------------------------

    def get_visible_artifacts(self, session: SessionRecord) -> list[dict]:
        """Return artifacts visible to the participant."""
        state = session.current_state
        artifacts_raw = state.get("artifacts", [])
        if not artifacts_raw:
            # Pull from case definition
            engine = _get_engine(session.case_id)
            case = engine.case
            artifacts_raw = [
                {
                    "id": a.artifact_id,
                    "type": a.type.value if hasattr(a.type, "value") else str(a.type),
                    "name": a.path.split("/")[-1] if "/" in a.path else a.path,
                    "metadata": {
                        "visible_initially": a.visible_initially,
                        "classification": a.classification,
                    },
                }
                for a in case.evidence.artifacts
                if a.visible_initially
            ]

        return [
            {
                "id": a.get("id", str(i)),
                "type": a.get("type", "unknown"),
                "name": a.get("name", "Unnamed"),
                "metadata": a.get("metadata", {}),
            }
            for i, a in enumerate(artifacts_raw)
        ]

    def get_artifact(self, session: SessionRecord, artifact_id: str) -> dict | None:
        """Get a specific artifact by ID."""
        for artifact in self.get_visible_artifacts(session):
            if artifact["id"] == artifact_id:
                return artifact
        return None

    # ------------------------------------------------------------------
    # Final recommendation
    # ------------------------------------------------------------------

    def submit_final_recommendation(
        self,
        session: SessionRecord,
        summary: str,
        recommendation: str,
        justification: str = "",
        next_steps: list[str] | None = None,
    ) -> tuple[EventRecord, SessionRecord]:
        """Submit the final recommendation, completing the session."""
        params = {
            "summary": summary,
            "recommendation": recommendation,
            "justification": justification,
            "next_steps": next_steps or [],
            "actor_id": session.participant_id,
        }
        return self.execute_action(session, "submit_final_recommendation", params)
