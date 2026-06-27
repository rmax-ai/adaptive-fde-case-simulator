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
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate_session(self, session: SessionRecord) -> dict:
        """Run evaluation over a completed session and return structured results.

        Examines the session's current state against the case's evaluation config:
        dimension scoring, hard constraint checking, evidence tracking.
        """
        case = _load_case(session.case_id)
        ev_config = case.evaluation
        state = session.current_state

        # Score each dimension
        dimensions: list[dict] = []
        all_findings: list[str] = []
        all_missed: list[str] = []

        for dim in ev_config.dimensions:
            score = 50.0  # default mid-point
            findings: list[str] = []
            missed: list[str] = []

            # Automated indicators: check state for evidence of each
            for indicator in dim.automated_indicators:
                if self._check_indicator(indicator, state):
                    score += 5.0
                    findings.append(f"Met indicator: {indicator}")
                else:
                    missed.append(indicator)

            # Ensure score is clamped
            score = max(0.0, min(100.0, score))

            dimensions.append({
                "name": dim.name,
                "score": round(score, 1),
                "max_score": 100.0,
                "weight": dim.weight,
                "findings": findings[:10],
                "missed_evidence": missed[:10],
            })
            all_findings.extend(findings)
            all_missed.extend(missed)

        # Check hard constraints
        constraint_outcomes: list[dict] = []
        for hc in ev_config.hard_constraints:
            passed = self._check_hard_constraint(hc, state)
            constraint_outcomes.append({
                "constraint_type": hc.constraint_type,
                "severity": hc.severity,
                "passed": passed,
                "description": hc.description,
                "details": "Passed" if passed else f"Failed: {hc.condition}",
            })

        # Overall score: weighted average of dimension scores
        overall = 0.0
        total_weight = 0.0
        for d in dimensions:
            overall += d["score"] * d["weight"]
            total_weight += d["weight"]

        # Deduct for hard constraint failures
        violations = [c for c in constraint_outcomes if not c["passed"]]
        for v in violations:
            deduction = 15.0 if v["severity"] == "critical" else 5.0
            overall -= deduction

        overall = max(
            0.0,
            min(100.0, overall / max(total_weight, 0.01) if total_weight > 0 else overall),
        )

        # Strongest / weakest behaviors
        sorted_dims = sorted(dimensions, key=lambda d: d["score"], reverse=True)
        strongest = [d["name"] for d in sorted_dims[:3] if d["score"] >= 50]
        weakest = [d["name"] for d in sorted_dims[-3:] if d["score"] < 50]

        # Mark session as evaluated
        domain_session = _record_to_domain(session)
        if domain_session.status == SessionStatus.COMPLETED:
            session.status = SessionStatus.EVALUATED.value
            domain_session.status = SessionStatus.EVALUATED

        result = {
            "session_id": str(session.id),
            "overall_score": round(overall, 1),
            "dimensions": dimensions,
            "hard_constraint_violations": constraint_outcomes,
            "strongest_behaviors": strongest,
            "weakest_behaviors": weakest,
            "missed_evidence": list(set(all_missed))[:20],
            "status": session.status,
        }

        return result

    @staticmethod
    def _check_indicator(indicator: str, state: dict) -> bool:
        """Check a single automated indicator against the session state."""
        indicator_lower = indicator.lower()

        # Check for evidence in various state fields
        state_str = str(state).lower()

        # Simple keyword matching
        if indicator_lower in state_str:
            return True

        # Check specific state paths
        if "action_log" in state:
            for entry in state["action_log"]:
                if isinstance(entry, dict):
                    entry_str = str(entry).lower()
                    if indicator_lower in entry_str:
                        return True

        # Check artifact inspections
        artifacts_inspected = state.get("artifacts_inspected", [])
        for art_id in artifacts_inspected:
            if indicator_lower in str(art_id).lower():
                return True

        # Check analyses
        analyses = state.get("analyses", [])
        for analysis in analyses:
            if isinstance(analysis, dict):
                analysis_str = str(analysis).lower()
                if indicator_lower in analysis_str:
                    return True

        return False

    @staticmethod
    def _check_hard_constraint(hc: object, state: dict) -> bool:
        """Check whether a hard constraint has been violated."""
        # Support both dict and Pydantic model hard constraints
        if isinstance(hc, dict):
            condition = hc.get("condition", "").lower()
        else:
            condition = getattr(hc, "condition", "").lower()
        state_str = str(state).lower()

        # Check for violation patterns
        violation_phrases = [
            "violated", "failed", "breached", "not_met", "over_budget",
        ]
        for phrase in violation_phrases:
            if phrase in condition and phrase in state_str:
                return False

        # Check budget
        if "budget" in condition:
            budget_remaining = state.get("budget_remaining", 0)
            if "exceeded" in condition or "over" in condition:
                return budget_remaining >= 0
            return budget_remaining >= 0

        # Check artifact disclosure
        if "disclosure" in condition or "forbidden" in condition:
            flags = state.get("flags", {})
            if flags.get("forbidden_disclosure_occurred", False):
                return False

        # Default: pass if we can't determine violation
        return True

    def get_evaluation(self, session: SessionRecord) -> dict | None:
        """Return stored evaluation results if session is completed/evaluated."""
        if session.status not in ("completed", "evaluated"):
            return None
        evaluation = session.current_state.get("evaluation", {})
        if evaluation:
            return evaluation
        # If no stored evaluation, run one
        return self.evaluate_session(session)

    def get_report(self, session: SessionRecord) -> dict | None:
        """Build a full participant report for a completed session."""
        if session.status not in ("completed", "evaluated"):
            return None

        evaluation = self.get_evaluation(session)
        state = session.current_state

        # Build timeline from events
        events = self.get_events(session.id)
        timeline = [
            {
                "sequence": e.sequence,
                "event_type": e.event_type,
                "actor_type": e.actor_type,
                "timestamp": e.created_at.isoformat() if e.created_at else "",
                "summary": str(e.payload)[:200] if e.payload else "",
            }
            for e in events
        ]

        # Artifacts inspected
        artifacts_inspected = state.get("artifacts_inspected", [])

        # Stakeholder interactions
        interactions = state.get("stakeholder_questions", []) + state.get(
            "stakeholder_interviews", []
        )

        # Final recommendation
        recommendation = state.get("final_recommendation", {})

        return {
            "session_id": str(session.id),
            "case_id": session.case_id,
            "case_version": session.case_version,
            "participant_id": session.participant_id,
            "status": session.status,
            "evaluation": evaluation,
            "timeline": timeline,
            "artifacts_inspected": artifacts_inspected,
            "stakeholder_interactions": interactions,
            "recommendation": recommendation,
        }

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
        event_record, updated_session = self.execute_action(
            session, "submit_final_recommendation", params
        )

        # Auto-trigger evaluation when session is completed
        domain_session = _record_to_domain(updated_session)
        if domain_session.status == SessionStatus.COMPLETED:
            evaluation = self.evaluate_session(updated_session)
            # Store evaluation results on session state
            updated_session.current_state["evaluation"] = evaluation
            self._db.flush()

        return event_record, updated_session

    # ------------------------------------------------------------------
    # Stakeholders
    # ------------------------------------------------------------------

    def get_stakeholders(self, session: SessionRecord) -> list[dict]:
        """Return stakeholders with roles and qualitative trust signals.

        Trust signals are derived from numeric trust scores and are
        always qualitative — never expose raw numeric trust.
        """
        case = _load_case(session.case_id)
        state = session.current_state
        trust_scores: dict = state.get("trust_scores", {})

        def _to_signal(score: int | float) -> str:
            if score >= 80:
                return "cooperative"
            elif score >= 60:
                return "hesitant"
            elif score >= 40:
                return "awaiting_evidence"
            elif score >= 20:
                return "blocked"
            else:
                return "escalating"

        stakeholders: list[dict] = []
        for s in case.organization.stakeholders:
            numeric = trust_scores.get(s.stakeholder_id, s.trust_initial * 10)
            stakeholders.append({
                "id": s.stakeholder_id,
                "role": s.role,
                "trust_signal": _to_signal(numeric),
            })

        return stakeholders

    def send_stakeholder_message(
        self,
        session: SessionRecord,
        stakeholder_id: str,
        message: str,
    ) -> dict:
        """Send a message to a stakeholder and return the response.

        Uses the policy engine to determine the response tone, persists the
        interaction as an event, and updates the trust state.
        """
        case = _load_case(session.case_id)

        # Find the stakeholder config
        stakeholder = None
        for s in case.organization.stakeholders:
            if s.stakeholder_id == stakeholder_id:
                stakeholder = s
                break
        if stakeholder is None:
            raise ValueError(f"Stakeholder '{stakeholder_id}' not found")

        # Determine tone and trust effect based on stakeholder's rules
        state = session.current_state
        trust_scores: dict = state.get("trust_scores", {})
        current_trust = trust_scores.get(stakeholder_id, stakeholder.trust_initial * 10)

        # Simple policy: trust level drives the tone
        tone = "neutral"
        trust_delta = 0
        disclosed: list[str] = []

        if current_trust >= 80:
            tone = "helpful"
            trust_delta = 0
            # Cooperative stakeholders may share facts
            if stakeholder.knowledge:
                disclosed = [stakeholder.knowledge[0]]
        elif current_trust >= 60:
            tone = "cautious"
            trust_delta = 2
        elif current_trust >= 40:
            tone = "hesitant"
            trust_delta = -3
        elif current_trust >= 20:
            tone = "frustrated"
            trust_delta = -5
        else:
            tone = "hostile"
            trust_delta = -2

        # Update trust state
        new_trust = max(0, min(100, current_trust + trust_delta))
        trust_scores[stakeholder_id] = new_trust
        state["trust_scores"] = trust_scores

        # Build simulated response text
        response_text = self._render_stakeholder_message(stakeholder, message, tone)

        # Persist as an event
        event = SimulationEvent(
            session_id=session.id,
            sequence=session.current_sequence,
            event_type="stakeholder.responded",
            actor_type="stakeholder",
            actor_id=stakeholder_id,
            payload={
                "stakeholder_id": stakeholder_id,
                "participant_message": message,
                "response": response_text,
                "tone": tone,
                "disclosed_fact_ids": disclosed,
                "trust_signal": self._trust_to_signal(new_trust),
            },
        )
        self._persist_event(event, session.id)
        session.current_sequence += 1
        self._db.flush()

        return {
            "stakeholder_id": stakeholder_id,
            "message": response_text,
            "tone": tone,
            "disclosed_fact_ids": disclosed,
        }

    @staticmethod
    def _trust_to_signal(score: int | float) -> str:
        """Map numeric trust score to qualitative signal."""
        if score >= 80:
            return "cooperative"
        elif score >= 60:
            return "hesitant"
        elif score >= 40:
            return "awaiting_evidence"
        elif score >= 20:
            return "blocked"
        else:
            return "escalating"

    @staticmethod
    def _render_stakeholder_message(
        stakeholder: object,
        participant_message: str,
        tone: str,
    ) -> str:
        """Render a stakeholder response message based on tone and config.

        This is a template-based renderer (can be replaced with an LLM
        language renderer later).
        """
        role = getattr(stakeholder, "role", "Stakeholder")

        responses = {
            "helpful": (
                f"({role}) Thank you for reaching out. I'm happy to help with your query. "
                f"Regarding '{participant_message[:80]}...' — "
                f"here's what I can share based on what we know."
            ),
            "neutral": (
                f"({role}) I received your message about '{participant_message[:60]}...'. "
                f"Let me think about this and get back to you with more details."
            ),
            "cautious": (
                f"({role}) I'm not entirely sure I can share everything on "
                f"'{participant_message[:60]}...'. Let me check what's appropriate."
            ),
            "hesitant": (
                f"({role}) I'm not comfortable discussing "
                f"'{participant_message[:60]}...' at this point. "
                f"We may need to build more trust first."
            ),
            "frustrated": (
                f"({role}) I've already addressed similar questions about "
                f"'{participant_message[:60]}...'. Please review the documentation provided."
            ),
            "hostile": (
                f"({role}) I don't have time for this. If you need information, "
                f"please go through the proper escalation channels."
            ),
        }

        return responses.get(tone, responses["neutral"])
