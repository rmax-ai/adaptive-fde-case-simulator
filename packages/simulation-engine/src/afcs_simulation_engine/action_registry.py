from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from typing import Any

from afcs_case_schema import CaseDefinition
from afcs_domain import SimulationSession

from .actions import ACTION_HANDLERS, ACTION_SCHEMAS

# ---------------------------------------------------------------------------
# Precondition type
# ---------------------------------------------------------------------------

PreconditionFn = Callable[[dict[str, Any], dict[str, Any], CaseDefinition], list[str]]


class ActionRegistry:
    """Registry of all available action types with their handlers and preconditions.

    An action handler is a pure function ``(state, params) -> new_state``.
    A precondition is a callable ``(state, params, case) -> list[str]`` that
    returns a list of failed precondition messages (empty = all pass).
    """

    def __init__(self) -> None:
        self._handlers: dict[str, Callable] = {}
        self._schemas: dict[str, dict] = {}
        self._preconditions: dict[str, list[PreconditionFn]] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        action_type: str,
        handler: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]],
        preconditions: list[PreconditionFn] | None = None,
        schema: dict | None = None,
    ) -> None:
        """Register an action type with its handler and optional preconditions."""
        self._handlers[action_type] = handler
        self._preconditions[action_type] = preconditions or []
        if schema is not None:
            self._schemas[action_type] = schema

    def register_from_builtins(self) -> None:
        """Register all built-in action handlers and their schemas."""
        for action_type, handler in ACTION_HANDLERS.items():
            schema = ACTION_SCHEMAS.get(action_type, {})
            self.register(action_type, handler, schema=schema)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def has_action(self, action_type: str) -> bool:
        return action_type in self._handlers

    def get_handler(self, action_type: str) -> Callable | None:
        return self._handlers.get(action_type)

    def get_schema(self, action_type: str) -> dict:
        """Return the JSON Schema for the action parameters."""
        schema = self._schemas.get(action_type, {})
        result: dict = {
            "action_type": action_type,
            "description": schema.get("description", ""),
            "parameters_schema": schema.get("parameters", {"type": "object", "properties": {}}),
            "preconditions": [],
            "time_cost": schema.get("time_cost", 10),
            "budget_cost": schema.get("budget_cost"),
        }
        return result

    def get_available_actions(
        self,
        session: SimulationSession,
        case: CaseDefinition,
    ) -> list[dict]:
        """Return the list of actions available in the current state.

        An action is available if:
        1. It is registered
        2. All its preconditions pass when evaluated against the current state
        """
        state = session.current_state
        available: list[dict] = []

        for action_type in self._handlers:
            preconditions = self._preconditions.get(action_type, [])
            failed = []
            for precondition_fn in preconditions:
                failed.extend(precondition_fn(state, {}, case))

            schema = self.get_schema(action_type)
            schema = deepcopy(schema)
            schema["preconditions"] = failed
            available.append(schema)

        return available

    def validate_preconditions(
        self,
        action_type: str,
        state: dict[str, Any],
        params: dict[str, Any],
        case: CaseDefinition,
    ) -> list[str]:
        """Return a list of failed precondition messages. Empty list = all pass."""
        preconditions = self._preconditions.get(action_type, [])
        failed: list[str] = []
        for precondition_fn in preconditions:
            failed.extend(precondition_fn(state, params, case))
        return failed

    def list_action_types(self) -> list[str]:
        return list(self._handlers.keys())
