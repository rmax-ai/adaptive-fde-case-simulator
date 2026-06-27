"""Replay service for session timeline reconstruction with state diffs."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from afcs_domain import SimulationEvent


def _compute_state_diff(
    pre_state: dict[str, Any],
    post_state: dict[str, Any],
) -> list[dict[str, Any]]:
    """Compute a list of atomic diffs between pre and post state dicts.

    Each diff entry has:
      - path: dot-separated key path
      - operation: "set" | "unset" | "append" | "increment" | "changed"
      - old_value: value before (None if new key)
      - new_value: value after (None if key removed)
    """
    diffs: list[dict[str, Any]] = []

    all_keys = set(pre_state.keys()) | set(post_state.keys())

    for key in sorted(all_keys):
        pre_val = pre_state.get(key)
        post_val = post_state.get(key)

        if key not in pre_state:
            diffs.append(
                {
                    "path": key,
                    "operation": "set",
                    "old_value": None,
                    "new_value": _summarise(post_val),
                }
            )
        elif key not in post_state:
            diffs.append(
                {
                    "path": key,
                    "operation": "unset",
                    "old_value": _summarise(pre_val),
                    "new_value": None,
                }
            )
        elif pre_val != post_val:
            if isinstance(pre_val, (int, float)) and isinstance(post_val, (int, float)):
                delta = post_val - pre_val
                if delta > 0:
                    op = "increment"
                elif delta < 0:
                    op = "decrement"
                else:
                    op = "changed"
                diffs.append(
                    {
                        "path": key,
                        "operation": op,
                        "old_value": pre_val,
                        "new_value": post_val,
                    }
                )
            elif isinstance(pre_val, list) and isinstance(post_val, list):
                added = [item for item in post_val if item not in pre_val]
                removed = [item for item in pre_val if item not in post_val]
                if added:
                    diffs.append(
                        {
                            "path": key,
                            "operation": "append",
                            "old_value": _summarise(pre_val),
                            "new_value": _summarise(post_val),
                            "added_items": len(added),
                            "removed_items": len(removed),
                        }
                    )
                else:
                    diffs.append(
                        {
                            "path": key,
                            "operation": "changed",
                            "old_value": _summarise(pre_val),
                            "new_value": _summarise(post_val),
                        }
                    )
            else:
                diffs.append(
                    {
                        "path": key,
                        "operation": "changed",
                        "old_value": _summarise(pre_val),
                        "new_value": _summarise(post_val),
                    }
                )

    return diffs


def _summarise(value: Any, max_len: int = 120) -> Any:
    """Summarise complex values for diff output (truncate long strings/lists)."""
    if isinstance(value, str) and len(value) > max_len:
        return value[:120] + "..."
    if isinstance(value, list) and len(value) > 20:
        return [*value[:20], f"... ({len(value) - 20} more)"]
    if isinstance(value, dict) and len(value) > 20:
        keys_sample = list(value.keys())[:10]
        return {k: value[k] for k in keys_sample}
    return value


def _extract_dimension_tags(event: SimulationEvent) -> list[str]:
    """Attempt to infer relevant evaluation dimensions from an event."""
    action_type = ""
    if isinstance(event.payload, dict):
        action_type = event.payload.get("action_type", "")

    # Mapping of action types to evaluation dimensions
    dimension_map: dict[str, list[str]] = {
        "inspect_artifact": ["discovery", "technical"],
        "ask_stakeholder": ["discovery"],
        "interview_stakeholder": ["discovery"],
        "request_access": ["discovery"],
        "register_assumption": ["discovery"],
        "update_assumption": ["discovery"],
        "register_risk": ["governance", "discovery"],
        "update_risk": ["governance"],
        "define_baseline": ["discovery", "technical"],
        "define_success_metric": ["evaluation_quality"],
        "propose_scope": ["evaluation_quality"],
        "reject_scope": ["evaluation_quality"],
        "select_architecture": ["technical"],
        "modify_architecture": ["technical"],
        "define_evaluation": ["evaluation_quality"],
        "run_analysis": ["technical"],
        "run_pilot": ["delivery"],
        "inspect_pilot_result": ["delivery", "evaluation_quality"],
        "escalate_issue": ["governance"],
        "communicate_decision": ["governance", "delivery"],
        "define_rollout": ["delivery"],
        "define_rollback": ["operational_sustainability"],
        "assign_owner": ["delivery"],
        "prepare_handoff": ["delivery", "operational_sustainability"],
        "submit_final_recommendation": ["delivery", "governance"],
        "request_approval": ["governance"],
        "propose_custom_action": ["discovery"],
    }

    return dimension_map.get(action_type, [])


class ReplayService:
    """Reconstructs a session timeline with state diffs between events.

    Provides chronological event lists annotated with computed state
    transitions, dimension tags, and related metadata for display
    in the replay UI.
    """

    def build_timeline(
        self,
        events: list[SimulationEvent],
        dimension_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """Build a chronological timeline from a list of events.

        Each timeline entry includes:
        - event: the raw event data
        - state_diff: computed diffs (pre → post)
        - dimensions: relevant evaluation dimensions
        - pre_state_snapshot: truncated before state
        - post_state_snapshot: truncated after state

        Args:
            events: Chronological list of SimulationEvents.
            dimension_filter: Optional dimension name to filter by.

        Returns:
            List of timeline entry dicts, sorted by sequence.
        """
        sorted_events = sorted(events, key=lambda e: e.sequence)
        timeline: list[dict[str, Any]] = []

        # Track cumulative state to compute diffs
        cumulative_state: dict[str, Any] = {}

        for event in sorted_events:
            pre_state = deepcopy(cumulative_state)
            payload = event.payload if isinstance(event.payload, dict) else {}

            # Update cumulative state for action_executed events
            if event.event_type == "action_executed":
                params = payload.get("params", {})
                if isinstance(params, dict):
                    # Merge params into cumulative state for diff computation
                    for k, v in params.items():
                        cumulative_state[k] = v

            post_state = deepcopy(cumulative_state)
            diff = _compute_state_diff(pre_state, post_state)
            tags = _extract_dimension_tags(event)

            if dimension_filter and dimension_filter not in tags:
                continue

            timeline.append(
                {
                    "event": {
                        "event_id": str(event.event_id),
                        "session_id": str(event.session_id),
                        "sequence": event.sequence,
                        "event_type": event.event_type,
                        "actor_type": event.actor_type,
                        "actor_id": event.actor_id,
                        "payload": payload,
                        "pre_state_hash": event.pre_state_hash,
                        "post_state_hash": event.post_state_hash,
                        "timestamp": event.timestamp.isoformat()
                        if hasattr(event.timestamp, "isoformat")
                        else str(event.timestamp),
                    },
                    "state_diff": diff,
                    "dimensions": tags,
                    "pre_state_snapshot": _summarise(pre_state),
                    "post_state_snapshot": _summarise(post_state),
                    "summary": self._generate_summary(event),
                }
            )

        return timeline

    def get_available_dimensions(self) -> list[str]:
        """Return the list of known evaluation dimensions for filtering."""
        return [
            "discovery",
            "technical",
            "evaluation_quality",
            "delivery",
            "governance",
            "operational_sustainability",
        ]

    @staticmethod
    def _generate_summary(event: SimulationEvent) -> str:
        """Generate a human-readable summary for an event."""
        payload = event.payload if isinstance(event.payload, dict) else {}

        if event.event_type == "session.created":
            return "Session created"

        if event.event_type == "action_executed":
            action_type = payload.get("action_type", "unknown")
            params = payload.get("params", {})
            if isinstance(params, dict):
                desc = params.get("description") or params.get("question") or ""
                artifact = params.get("artifact_id") or ""
                if desc:
                    return f"{action_type}: {desc}"
                if artifact:
                    return f"{action_type}: {artifact}"
            return f"Executed {action_type}"
        elif event.event_type == "stakeholder.responded":
            return f"Stakeholder {event.actor_id} responded"
        else:
            return f"{event.event_type} (seq {event.sequence})"
