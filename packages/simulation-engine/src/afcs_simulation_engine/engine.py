from __future__ import annotations

from typing import Any, ClassVar

from afcs_case_schema import CaseDefinition
from afcs_domain import (
    InvalidActionError,
    PreconditionError,
    SessionStatus,
    SimulationEvent,
    SimulationSession,
)

from .action_registry import ActionRegistry
from .state_hash import compute_state_hash


def _build_initial_state(case: CaseDefinition) -> dict[str, Any]:
    """Construct an initial simulation state dict from a case definition."""
    state: dict[str, Any] = {
        "phase": "discovery",
        "status": "active",
        "budget_remaining": 50000,
        "artifacts_inspected": [],
        "stakeholder_questions": [],
        "stakeholder_interviews": [],
        "access_requests": [],
        "approval_requests": [],
        "assumptions": [],
        "risks": [],
        "success_metrics": [],
        "analyses": [],
        "escalated_issues": [],
        "decisions": [],
        "custom_actions": [],
        "action_log": [],
    }

    # Extract budget from case business config if provided
    budget_data = case.business.budget if hasattr(case, "business") else {}
    if isinstance(budget_data, dict) and "amount" in budget_data:
        state["budget_remaining"] = float(budget_data["amount"])

    # Seed trust scores from stakeholder config
    if hasattr(case, "organization") and hasattr(case.organization, "stakeholders"):
        trust: dict[str, int] = {}
        for s in case.organization.stakeholders:
            trust[s.stakeholder_id] = s.trust_initial * 10  # 0-10 -> 0-100
        state["trust_scores"] = trust

    return state


class StateTransitionEngine:
    """Deterministic state machine for simulation sessions.

    Manages validation and execution of actions against a simulation session,
    producing append-only events and updated session state. All state transitions
    are deterministic: given the same (state, action) tuple, the same next state
    and event are always produced.
    """

    def __init__(self, case: CaseDefinition, action_registry: ActionRegistry) -> None:
        self._case = case
        self._registry = action_registry

    @property
    def case(self) -> CaseDefinition:
        return self._case

    @property
    def registry(self) -> ActionRegistry:
        return self._registry

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def initialise_session(self, session: SimulationSession) -> SimulationSession:
        """Seed the session with the case's initial state and set status to IN_PROGRESS."""
        session.current_state = _build_initial_state(self._case)
        session.current_sequence = 0
        session.status = SessionStatus.IN_PROGRESS
        return session

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_action(
        self,
        session: SimulationSession,
        action_type: str,
        params: dict[str, Any],
    ) -> list[str]:
        """Validate that an action can be executed in the current state.

        Returns a list of failed precondition messages. An empty list means
        the action is valid and can be executed.
        """
        # Check the action type is registered
        if not self._registry.has_action(action_type):
            return [f"Unknown action type: '{action_type}'"]

        # Check session is in progress
        if session.status != SessionStatus.IN_PROGRESS:
            return [f"Session is not in progress (status: {session.status.value})"]

        # Check phase constraints
        state = session.current_state
        phase = state.get("phase", "discovery")
        phase_errors = self._check_phase_gate(action_type, phase)
        if phase_errors:
            return phase_errors

        # Check budget
        budget = state.get("budget_remaining", 0)
        schema = self._registry.get_schema(action_type)
        budget_cost = schema.get("budget_cost")
        if budget_cost is not None and budget_cost > budget:
            return [f"Insufficient budget: need {budget_cost}, have {budget}"]

        # Run registered preconditions
        failed = self._registry.validate_preconditions(action_type, state, params, self._case)
        return failed

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute_action(
        self,
        session: SimulationSession,
        action_type: str,
        params: dict[str, Any],
    ) -> tuple[SimulationEvent, SimulationSession]:
        """Execute an action against the current session state.

        Steps:
        1. Validate the action (raises PreconditionError if invalid)
        2. Compute pre-state hash
        3. Apply the action handler
        4. Compute post-state hash
        5. Increment sequence number
        6. Emit event

        Returns (event, updated_session).
        """
        # Validate
        failed = self.validate_action(session, action_type, params)
        if failed:
            raise PreconditionError(f"Cannot execute '{action_type}': {'; '.join(failed)}")

        handler = self._registry.get_handler(action_type)
        if handler is None:
            raise InvalidActionError(f"No handler registered for '{action_type}'")

        state = session.current_state

        # Pre-state hash
        pre_hash = compute_state_hash(state)

        # Apply handler (pure function)
        new_state = handler(state, params)

        # Post-state hash
        post_hash = compute_state_hash(new_state)

        # Update session state
        session.current_state = new_state

        # Update session status to completed if final recommendation submitted
        if new_state.get("status") == "completed":
            session.status = SessionStatus.COMPLETED

        # Emit event with current sequence (0-based), then increment
        event = SimulationEvent(
            session_id=session.id,
            sequence=session.current_sequence,
            event_type="action_executed",
            actor_type="participant",
            actor_id=params.get("actor_id"),
            payload={"action_type": action_type, "params": params},
            pre_state_hash=pre_hash,
            post_state_hash=post_hash,
        )

        session.current_sequence += 1

        return event, session

    # ------------------------------------------------------------------
    # Replay
    # ------------------------------------------------------------------

    def replay_events(self, events: list[SimulationEvent]) -> SimulationSession:
        """Reconstruct session state from an append-only event stream.

        Starts from the case's initial state and replays every action event
        in sequence order, returning the final reconstructed session.

        Raises ``ValueError`` if events are out of order or have gaps.
        """
        # Validate monotonic sequence
        for i, event in enumerate(events):
            if event.sequence != i:
                raise ValueError(
                    f"Event sequence gap at index {i}: expected sequence {i}, got {event.sequence}"
                )

        # Start from initial state
        state = _build_initial_state(self._case)

        # Replay action events in order
        for event in events:
            if event.event_type != "action_executed":
                continue
            params = event.payload.get("params", {}) if isinstance(event.payload, dict) else {}
            action_type = (
                event.payload.get("action_type", "") if isinstance(event.payload, dict) else ""
            )
            if not action_type:
                continue
            handler = self._registry.get_handler(action_type)
            if handler is not None:
                state = handler(state, params)

        # Determine session status
        status = (
            SessionStatus.COMPLETED
            if state.get("status") == "completed"
            else SessionStatus.IN_PROGRESS
        )

        session = SimulationSession(
            case_id=self._case.metadata.case_id,
            case_version=self._case.metadata.version,
            current_state=state,
            current_sequence=len(events),
            status=status,
        )
        return session

    # ------------------------------------------------------------------
    # Phase gating
    # ------------------------------------------------------------------

    _PHASE_GATES: ClassVar[dict[str, str]] = {
        "inspect_artifact": "discovery",
        "ask_stakeholder": "discovery",
        "interview_stakeholder": "discovery",
        "request_access": "discovery",
        "register_assumption": "discovery",
        "update_assumption": "discovery",
        "register_risk": "discovery",
        "update_risk": "discovery",
        "define_baseline": "discovery",
        "define_success_metric": "evaluation",
        "propose_scope": "evaluation",
        "reject_scope": "evaluation",
        "select_architecture": "evaluation",
        "modify_architecture": "architecture",
        "define_evaluation": "architecture",
        "run_analysis": "architecture",
        "run_pilot": "delivery",
        "inspect_pilot_result": "delivery",
        "escalate_issue": "discovery",
        "communicate_decision": "discovery",
        "define_rollout": "delivery",
        "define_rollback": "delivery",
        "assign_owner": "delivery",
        "prepare_handoff": "reporting",
        "submit_final_recommendation": "reporting",
        "propose_custom_action": "discovery",
    }

    def _check_phase_gate(self, action_type: str, current_phase: str) -> list[str]:
        """Check if the action is allowed in the current phase.

        Returns a list of error messages (empty = allowed).
        """
        min_phase = self._PHASE_GATES.get(action_type)
        if min_phase is None:
            return []

        phase_order = [
            "discovery",
            "evaluation",
            "architecture",
            "delivery",
            "reporting",
            "completed",
        ]

        try:
            current_idx = phase_order.index(current_phase)
            min_idx = phase_order.index(min_phase)
        except ValueError:
            return []

        if current_idx < min_idx:
            return [
                f"Action '{action_type}' requires phase '{min_phase}', "
                f"but current phase is '{current_phase}'"
            ]

        if action_type == "submit_final_recommendation" and current_phase == "completed":
            return ["Final recommendation has already been submitted"]

        return []
