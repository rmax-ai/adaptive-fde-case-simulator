from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from typing import Any

# ---------------------------------------------------------------------------
# Phase constants
# ---------------------------------------------------------------------------

PHASE_DISCOVERY = "discovery"
PHASE_EVALUATION = "evaluation"
PHASE_ARCHITECTURE = "architecture"
PHASE_DELIVERY = "delivery"
PHASE_REPORTING = "reporting"
PHASE_COMPLETED = "completed"

PHASE_ORDER = [
    PHASE_DISCOVERY,
    PHASE_EVALUATION,
    PHASE_ARCHITECTURE,
    PHASE_DELIVERY,
    PHASE_REPORTING,
    PHASE_COMPLETED,
]

DEFAULT_PHASE = PHASE_DISCOVERY

# ---------------------------------------------------------------------------
# Action handler type
# ---------------------------------------------------------------------------

ActionHandler = Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]

# ---------------------------------------------------------------------------
# Helper: deep-copy state and apply modifications
# ---------------------------------------------------------------------------


def _ensure_list(state: dict[str, Any], key: str) -> list:
    if key not in state or not isinstance(state[key], list):
        state[key] = []
    return state[key]


def _ensure_dict(state: dict[str, Any], key: str) -> dict:
    if key not in state or not isinstance(state[key], dict):
        state[key] = {}
    return state[key]


def _advance_phase(state: dict[str, Any], target_phase: str) -> dict[str, Any]:
    """Advance the simulation phase forward (never backwards)."""
    current = state.get("phase", DEFAULT_PHASE)
    try:
        current_idx = PHASE_ORDER.index(current)
        target_idx = PHASE_ORDER.index(target_phase)
    except ValueError:
        return state
    if target_idx > current_idx:
        state = deepcopy(state)
        state["phase"] = target_phase
    return state


def _log_action(state: dict[str, Any], action_type: str, params: dict[str, Any]) -> dict[str, Any]:
    """Append to the action log for traceability."""
    state = deepcopy(state)
    log = _ensure_list(state, "action_log")
    entry = {"action_type": action_type}
    entry.update(params)
    log.append(entry)
    state["action_log"] = log
    return state


# ---------------------------------------------------------------------------
# 1. inspect_artifact
# ---------------------------------------------------------------------------


def handle_inspect_artifact(state: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    s = deepcopy(state)
    inspected = _ensure_list(s, "artifacts_inspected")
    artifact_id = params.get("artifact_id", params.get("artifact", str(len(inspected))))
    if artifact_id not in inspected:
        inspected.append(artifact_id)
    s["artifacts_inspected"] = inspected
    return s


# ---------------------------------------------------------------------------
# 2. ask_stakeholder
# ---------------------------------------------------------------------------


def handle_ask_stakeholder(state: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    s = deepcopy(state)
    questions = _ensure_list(s, "stakeholder_questions")
    questions.append(
        {
            "stakeholder_id": params.get("stakeholder_id", ""),
            "question": params.get("question", ""),
        }
    )
    s["stakeholder_questions"] = questions
    return s


# ---------------------------------------------------------------------------
# 3. interview_stakeholder
# ---------------------------------------------------------------------------


def handle_interview_stakeholder(state: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    s = deepcopy(state)
    interviews = _ensure_list(s, "stakeholder_interviews")
    interviews.append(
        {
            "stakeholder_id": params.get("stakeholder_id", ""),
            "topics": params.get("topics", []),
            "notes": params.get("notes", ""),
        }
    )
    s["stakeholder_interviews"] = interviews
    # Interviews tend to build trust
    trust = _ensure_dict(s, "trust_scores")
    sid = params.get("stakeholder_id", "")
    if sid and sid in trust:
        trust[sid] = min(100, trust.get(sid, 50) + 5)
    s["trust_scores"] = trust
    return s


# ---------------------------------------------------------------------------
# 4. request_access
# ---------------------------------------------------------------------------


def handle_request_access(state: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    s = deepcopy(state)
    requests = _ensure_list(s, "access_requests")
    requests.append(
        {
            "target": params.get("target", ""),
            "justification": params.get("justification", ""),
            "status": "pending",
        }
    )
    s["access_requests"] = requests
    return s


# ---------------------------------------------------------------------------
# 5. request_approval
# ---------------------------------------------------------------------------


def handle_request_approval(state: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    s = deepcopy(state)
    approvals = _ensure_list(s, "approval_requests")
    approvals.append(
        {
            "scope": params.get("scope", ""),
            "justification": params.get("justification", ""),
            "status": "pending",
        }
    )
    s["approval_requests"] = approvals
    return s


# ---------------------------------------------------------------------------
# 6. register_assumption
# ---------------------------------------------------------------------------


def handle_register_assumption(state: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    s = deepcopy(state)
    assumptions = _ensure_list(s, "assumptions")
    assumptions.append(
        {
            "id": params.get("id", str(len(assumptions))),
            "description": params.get("description", ""),
            "category": params.get("category", "general"),
        }
    )
    s["assumptions"] = assumptions
    return s


# ---------------------------------------------------------------------------
# 7. update_assumption
# ---------------------------------------------------------------------------


def handle_update_assumption(state: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    s = deepcopy(state)
    assumptions = _ensure_list(s, "assumptions")
    target_id = params.get("id", "")
    for a in assumptions:
        if a.get("id") == target_id:
            if "description" in params:
                a["description"] = params["description"]
            if "category" in params:
                a["category"] = params["category"]
            if "status" in params:
                a["status"] = params["status"]
            break
    s["assumptions"] = assumptions
    return s


# ---------------------------------------------------------------------------
# 8. register_risk
# ---------------------------------------------------------------------------


def handle_register_risk(state: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    s = deepcopy(state)
    risks = _ensure_list(s, "risks")
    risks.append(
        {
            "id": params.get("id", str(len(risks))),
            "description": params.get("description", ""),
            "impact": params.get("impact", "medium"),
            "likelihood": params.get("likelihood", "medium"),
            "mitigation": params.get("mitigation", ""),
        }
    )
    s["risks"] = risks
    return s


# ---------------------------------------------------------------------------
# 9. update_risk
# ---------------------------------------------------------------------------


def handle_update_risk(state: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    s = deepcopy(state)
    risks = _ensure_list(s, "risks")
    target_id = params.get("id", "")
    for r in risks:
        if r.get("id") == target_id:
            for key in ("description", "impact", "likelihood", "mitigation", "status"):
                if key in params:
                    r[key] = params[key]
            break
    s["risks"] = risks
    return s


# ---------------------------------------------------------------------------
# 10. define_baseline
# ---------------------------------------------------------------------------


def handle_define_baseline(state: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    s = deepcopy(state)
    s["baseline"] = {
        "description": params.get("description", ""),
        "metrics": params.get("metrics", []),
        "timestamp": params.get("timestamp", ""),
    }
    s = _advance_phase(s, PHASE_EVALUATION)
    return s


# ---------------------------------------------------------------------------
# 11. define_success_metric
# ---------------------------------------------------------------------------


def handle_define_success_metric(state: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    s = deepcopy(state)
    metrics = _ensure_list(s, "success_metrics")
    metrics.append(
        {
            "name": params.get("name", ""),
            "target": params.get("target", ""),
            "measurement": params.get("measurement", ""),
        }
    )
    s["success_metrics"] = metrics
    return s


# ---------------------------------------------------------------------------
# 12. propose_scope
# ---------------------------------------------------------------------------


def handle_propose_scope(state: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    s = deepcopy(state)
    s["proposed_scope"] = {
        "description": params.get("description", ""),
        "included": params.get("included", []),
        "excluded": params.get("excluded", []),
        "status": "proposed",
    }
    return s


# ---------------------------------------------------------------------------
# 13. reject_scope
# ---------------------------------------------------------------------------


def handle_reject_scope(state: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    s = deepcopy(state)
    if "proposed_scope" in s:
        s["proposed_scope"]["status"] = "rejected"
        s["proposed_scope"]["reason"] = params.get("reason", "")
        s["proposed_scope"]["rejected_by"] = params.get("rejected_by", "stakeholder")
    return s


# ---------------------------------------------------------------------------
# 14. select_architecture
# ---------------------------------------------------------------------------


def handle_select_architecture(state: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    s = deepcopy(state)
    s["selected_architecture"] = {
        "name": params.get("name", ""),
        "description": params.get("description", ""),
        "components": params.get("components", []),
        "rationale": params.get("rationale", ""),
    }
    s = _advance_phase(s, PHASE_ARCHITECTURE)
    return s


# ---------------------------------------------------------------------------
# 15. modify_architecture
# ---------------------------------------------------------------------------


def handle_modify_architecture(state: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    s = deepcopy(state)
    if "selected_architecture" not in s:
        s["selected_architecture"] = {}
    arch = s["selected_architecture"]
    for key in ("name", "description", "components", "rationale"):
        if key in params:
            arch[key] = params[key]
    if "modifications" not in arch:
        arch["modifications"] = []
    arch["modifications"].append(
        {
            "change": params.get("change", ""),
            "reason": params.get("reason", ""),
        }
    )
    s["selected_architecture"] = arch
    return s


# ---------------------------------------------------------------------------
# 16. define_evaluation
# ---------------------------------------------------------------------------


def handle_define_evaluation(state: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    s = deepcopy(state)
    s["evaluation_plan"] = {
        "baseline": params.get("baseline", ""),
        "metrics": params.get("metrics", []),
        "failure_classes": params.get("failure_classes", []),
        "thresholds": params.get("thresholds", {}),
    }
    return s


# ---------------------------------------------------------------------------
# 17. run_analysis
# ---------------------------------------------------------------------------


def handle_run_analysis(state: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    s = deepcopy(state)
    analyses = _ensure_list(s, "analyses")
    analyses.append(
        {
            "type": params.get("type", "general"),
            "findings": params.get("findings", ""),
            "conclusion": params.get("conclusion", ""),
        }
    )
    s["analyses"] = analyses
    s["budget_remaining"] = s.get("budget_remaining", 50000) - params.get("cost", 0)
    return s


# ---------------------------------------------------------------------------
# 18. run_pilot
# ---------------------------------------------------------------------------


def handle_run_pilot(state: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    s = deepcopy(state)
    s["pilot"] = {
        "scope": params.get("scope", ""),
        "duration": params.get("duration", ""),
        "metrics": params.get("metrics", []),
        "status": "running",
    }
    s["budget_remaining"] = s.get("budget_remaining", 50000) - params.get("cost", 0)
    s = _advance_phase(s, PHASE_DELIVERY)
    return s


# ---------------------------------------------------------------------------
# 19. inspect_pilot_result
# ---------------------------------------------------------------------------


def handle_inspect_pilot_result(state: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    s = deepcopy(state)
    if "pilot" not in s:
        s["pilot"] = {}
    s["pilot"]["status"] = "completed"
    s["pilot"]["results"] = {
        "summary": params.get("summary", ""),
        "metrics_achieved": params.get("metrics_achieved", {}),
        "issues_found": params.get("issues_found", []),
    }
    return s


# ---------------------------------------------------------------------------
# 20. escalate_issue
# ---------------------------------------------------------------------------


def handle_escalate_issue(state: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    s = deepcopy(state)
    escalated = _ensure_list(s, "escalated_issues")
    escalated.append(
        {
            "issue": params.get("issue", ""),
            "impact": params.get("impact", ""),
            "recommended_action": params.get("recommended_action", ""),
            "escalated_to": params.get("escalated_to", "management"),
        }
    )
    s["escalated_issues"] = escalated
    return s


# ---------------------------------------------------------------------------
# 21. communicate_decision
# ---------------------------------------------------------------------------


def handle_communicate_decision(state: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    s = deepcopy(state)
    decisions = _ensure_list(s, "decisions")
    decisions.append(
        {
            "decision": params.get("decision", ""),
            "rationale": params.get("rationale", ""),
            "audience": params.get("audience", ""),
        }
    )
    s["decisions"] = decisions
    return s


# ---------------------------------------------------------------------------
# 22. define_rollout
# ---------------------------------------------------------------------------


def handle_define_rollout(state: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    s = deepcopy(state)
    s["rollout_plan"] = {
        "strategy": params.get("strategy", ""),
        "phases": params.get("phases", []),
        "timeline": params.get("timeline", ""),
        "rollout_metrics": params.get("rollout_metrics", []),
    }
    return s


# ---------------------------------------------------------------------------
# 23. define_rollback
# ---------------------------------------------------------------------------


def handle_define_rollback(state: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    s = deepcopy(state)
    s["rollback_plan"] = {
        "trigger_conditions": params.get("trigger_conditions", []),
        "rollback_steps": params.get("rollback_steps", []),
        "verification": params.get("verification", ""),
    }
    return s


# ---------------------------------------------------------------------------
# 24. assign_owner
# ---------------------------------------------------------------------------


def handle_assign_owner(state: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    s = deepcopy(state)
    s["owner"] = params.get("owner", "")
    s["owner_role"] = params.get("role", "")
    return s


# ---------------------------------------------------------------------------
# 25. prepare_handoff
# ---------------------------------------------------------------------------


def handle_prepare_handoff(state: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    s = deepcopy(state)
    s["handoff"] = {
        "recipient": params.get("recipient", ""),
        "documentation": params.get("documentation", ""),
        "outstanding_items": params.get("outstanding_items", []),
        "status": "prepared",
    }
    return s


# ---------------------------------------------------------------------------
# 26. submit_final_recommendation
# ---------------------------------------------------------------------------


def handle_submit_final_recommendation(
    state: dict[str, Any], params: dict[str, Any]
) -> dict[str, Any]:
    s = deepcopy(state)
    s["final_recommendation"] = {
        "summary": params.get("summary", ""),
        "recommendation": params.get("recommendation", ""),
        "justification": params.get("justification", ""),
        "next_steps": params.get("next_steps", []),
    }
    s["status"] = "completed"
    s = _advance_phase(s, PHASE_COMPLETED)
    return s


# ---------------------------------------------------------------------------
# 27. propose_custom_action (user-defined)
# ---------------------------------------------------------------------------


def handle_propose_custom_action(state: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    s = deepcopy(state)
    custom = _ensure_list(s, "custom_actions")
    custom.append(
        {
            "action_name": params.get("action_name", "custom"),
            "description": params.get("description", ""),
            "payload": params.get("payload", {}),
        }
    )
    s["custom_actions"] = custom
    return s


# ---------------------------------------------------------------------------
# Registry table: action_type -> handler
# ---------------------------------------------------------------------------

ACTION_HANDLERS: dict[str, ActionHandler] = {
    "inspect_artifact": handle_inspect_artifact,
    "ask_stakeholder": handle_ask_stakeholder,
    "interview_stakeholder": handle_interview_stakeholder,
    "request_access": handle_request_access,
    "request_approval": handle_request_approval,
    "register_assumption": handle_register_assumption,
    "update_assumption": handle_update_assumption,
    "register_risk": handle_register_risk,
    "update_risk": handle_update_risk,
    "define_baseline": handle_define_baseline,
    "define_success_metric": handle_define_success_metric,
    "propose_scope": handle_propose_scope,
    "reject_scope": handle_reject_scope,
    "select_architecture": handle_select_architecture,
    "modify_architecture": handle_modify_architecture,
    "define_evaluation": handle_define_evaluation,
    "run_analysis": handle_run_analysis,
    "run_pilot": handle_run_pilot,
    "inspect_pilot_result": handle_inspect_pilot_result,
    "escalate_issue": handle_escalate_issue,
    "communicate_decision": handle_communicate_decision,
    "define_rollout": handle_define_rollout,
    "define_rollback": handle_define_rollback,
    "assign_owner": handle_assign_owner,
    "prepare_handoff": handle_prepare_handoff,
    "submit_final_recommendation": handle_submit_final_recommendation,
    "propose_custom_action": handle_propose_custom_action,
}

# ---------------------------------------------------------------------------
# Action schemas (for discovery / validation)
# ---------------------------------------------------------------------------

ACTION_SCHEMAS: dict[str, dict] = {
    "inspect_artifact": {
        "description": "Inspect an artifact to understand its contents and context.",
        "parameters": {
            "type": "object",
            "required": ["artifact_id"],
            "properties": {
                "artifact_id": {"type": "string", "description": "ID of the artifact to inspect"},
            },
        },
        "time_cost": 10,
        "budget_cost": None,
    },
    "ask_stakeholder": {
        "description": "Ask a stakeholder a direct question.",
        "parameters": {
            "type": "object",
            "required": ["stakeholder_id", "question"],
            "properties": {
                "stakeholder_id": {"type": "string"},
                "question": {"type": "string", "maxLength": 2000},
            },
        },
        "time_cost": 5,
        "budget_cost": None,
    },
    "interview_stakeholder": {
        "description": "Conduct a structured interview with a stakeholder.",
        "parameters": {
            "type": "object",
            "required": ["stakeholder_id"],
            "properties": {
                "stakeholder_id": {"type": "string"},
                "topics": {"type": "array", "items": {"type": "string"}},
                "notes": {"type": "string"},
            },
        },
        "time_cost": 30,
        "budget_cost": None,
    },
    "request_access": {
        "description": "Request access to a system, document, or resource.",
        "parameters": {
            "type": "object",
            "required": ["target", "justification"],
            "properties": {
                "target": {"type": "string"},
                "justification": {"type": "string"},
            },
        },
        "time_cost": 5,
        "budget_cost": None,
    },
    "request_approval": {
        "description": "Request approval for a proposed action or scope.",
        "parameters": {
            "type": "object",
            "required": ["scope", "justification"],
            "properties": {
                "scope": {"type": "string"},
                "justification": {"type": "string"},
            },
        },
        "time_cost": 15,
        "budget_cost": None,
    },
    "register_assumption": {
        "description": "Register an assumption being made about the case.",
        "parameters": {
            "type": "object",
            "required": ["description"],
            "properties": {
                "id": {"type": "string"},
                "description": {"type": "string"},
                "category": {
                    "type": "string",
                    "enum": ["technical", "business", "stakeholder", "general"],
                },
            },
        },
        "time_cost": 5,
        "budget_cost": None,
    },
    "update_assumption": {
        "description": "Update an existing assumption.",
        "parameters": {
            "type": "object",
            "required": ["id"],
            "properties": {
                "id": {"type": "string"},
                "description": {"type": "string"},
                "category": {"type": "string"},
                "status": {"type": "string"},
            },
        },
        "time_cost": 3,
        "budget_cost": None,
    },
    "register_risk": {
        "description": "Register a risk identified during the engagement.",
        "parameters": {
            "type": "object",
            "required": ["description"],
            "properties": {
                "id": {"type": "string"},
                "description": {"type": "string"},
                "impact": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                "likelihood": {"type": "string", "enum": ["low", "medium", "high"]},
                "mitigation": {"type": "string"},
            },
        },
        "time_cost": 10,
        "budget_cost": None,
    },
    "update_risk": {
        "description": "Update an existing risk entry.",
        "parameters": {
            "type": "object",
            "required": ["id"],
            "properties": {
                "id": {"type": "string"},
                "description": {"type": "string"},
                "impact": {"type": "string"},
                "likelihood": {"type": "string"},
                "mitigation": {"type": "string"},
                "status": {"type": "string"},
            },
        },
        "time_cost": 5,
        "budget_cost": None,
    },
    "define_baseline": {
        "description": "Define evaluation baseline, metrics, and current state measurement.",
        "parameters": {
            "type": "object",
            "required": ["description"],
            "properties": {
                "description": {"type": "string"},
                "metrics": {"type": "array", "items": {"type": "string"}},
                "timestamp": {"type": "string"},
            },
        },
        "time_cost": 30,
        "budget_cost": None,
    },
    "define_success_metric": {
        "description": "Define a specific success metric with target and measurement method.",
        "parameters": {
            "type": "object",
            "required": ["name", "target"],
            "properties": {
                "name": {"type": "string"},
                "target": {"type": "string"},
                "measurement": {"type": "string"},
            },
        },
        "time_cost": 10,
        "budget_cost": None,
    },
    "propose_scope": {
        "description": "Propose the scope of work for the engagement.",
        "parameters": {
            "type": "object",
            "required": ["description"],
            "properties": {
                "description": {"type": "string"},
                "included": {"type": "array", "items": {"type": "string"}},
                "excluded": {"type": "array", "items": {"type": "string"}},
            },
        },
        "time_cost": 20,
        "budget_cost": None,
    },
    "reject_scope": {
        "description": "Reject or push back on a proposed scope.",
        "parameters": {
            "type": "object",
            "required": ["reason"],
            "properties": {
                "reason": {"type": "string"},
                "rejected_by": {"type": "string"},
            },
        },
        "time_cost": 5,
        "budget_cost": None,
    },
    "select_architecture": {
        "description": "Select a technical architecture for the solution.",
        "parameters": {
            "type": "object",
            "required": ["name"],
            "properties": {
                "name": {"type": "string"},
                "description": {"type": "string"},
                "components": {"type": "array", "items": {"type": "string"}},
                "rationale": {"type": "string"},
            },
        },
        "time_cost": 45,
        "budget_cost": None,
    },
    "modify_architecture": {
        "description": "Modify the selected architecture with changes.",
        "parameters": {
            "type": "object",
            "required": ["change"],
            "properties": {
                "name": {"type": "string"},
                "description": {"type": "string"},
                "components": {"type": "array", "items": {"type": "string"}},
                "rationale": {"type": "string"},
                "change": {"type": "string"},
                "reason": {"type": "string"},
            },
        },
        "time_cost": 20,
        "budget_cost": None,
    },
    "define_evaluation": {
        "description": "Define evaluation plan with baseline, metrics, and failure classes.",
        "parameters": {
            "type": "object",
            "required": ["baseline"],
            "properties": {
                "baseline": {"type": "string"},
                "metrics": {"type": "array", "items": {"type": "string"}},
                "failure_classes": {"type": "array", "items": {"type": "string"}},
                "thresholds": {"type": "object"},
            },
        },
        "time_cost": 30,
        "budget_cost": None,
    },
    "run_analysis": {
        "description": "Run analysis on data or artifacts.",
        "parameters": {
            "type": "object",
            "required": ["findings"],
            "properties": {
                "type": {"type": "string"},
                "findings": {"type": "string"},
                "conclusion": {"type": "string"},
                "cost": {"type": "number", "default": 0},
            },
        },
        "time_cost": 20,
        "budget_cost": 1000,
    },
    "run_pilot": {
        "description": "Run a pilot of the proposed solution.",
        "parameters": {
            "type": "object",
            "required": ["scope"],
            "properties": {
                "scope": {"type": "string"},
                "duration": {"type": "string"},
                "metrics": {"type": "array", "items": {"type": "string"}},
                "cost": {"type": "number", "default": 5000},
            },
        },
        "time_cost": 120,
        "budget_cost": 5000,
    },
    "inspect_pilot_result": {
        "description": "Inspect and document the results of a completed pilot.",
        "parameters": {
            "type": "object",
            "required": ["summary"],
            "properties": {
                "summary": {"type": "string"},
                "metrics_achieved": {"type": "object"},
                "issues_found": {"type": "array", "items": {"type": "string"}},
            },
        },
        "time_cost": 30,
        "budget_cost": None,
    },
    "escalate_issue": {
        "description": "Escalate an issue to management or a higher authority.",
        "parameters": {
            "type": "object",
            "required": ["issue", "impact"],
            "properties": {
                "issue": {"type": "string"},
                "impact": {"type": "string"},
                "recommended_action": {"type": "string"},
                "escalated_to": {"type": "string"},
            },
        },
        "time_cost": 15,
        "budget_cost": None,
    },
    "communicate_decision": {
        "description": "Communicate a decision to stakeholders or team.",
        "parameters": {
            "type": "object",
            "required": ["decision"],
            "properties": {
                "decision": {"type": "string"},
                "rationale": {"type": "string"},
                "audience": {"type": "string"},
            },
        },
        "time_cost": 10,
        "budget_cost": None,
    },
    "define_rollout": {
        "description": "Define the rollout strategy and plan.",
        "parameters": {
            "type": "object",
            "required": ["strategy"],
            "properties": {
                "strategy": {"type": "string"},
                "phases": {"type": "array", "items": {"type": "string"}},
                "timeline": {"type": "string"},
                "rollout_metrics": {"type": "array", "items": {"type": "string"}},
            },
        },
        "time_cost": 45,
        "budget_cost": None,
    },
    "define_rollback": {
        "description": "Define the rollback plan in case of deployment failure.",
        "parameters": {
            "type": "object",
            "required": ["trigger_conditions"],
            "properties": {
                "trigger_conditions": {"type": "array", "items": {"type": "string"}},
                "rollback_steps": {"type": "array", "items": {"type": "string"}},
                "verification": {"type": "string"},
            },
        },
        "time_cost": 30,
        "budget_cost": None,
    },
    "assign_owner": {
        "description": "Assign an owner for a task, component, or area.",
        "parameters": {
            "type": "object",
            "required": ["owner"],
            "properties": {
                "owner": {"type": "string"},
                "role": {"type": "string"},
            },
        },
        "time_cost": 5,
        "budget_cost": None,
    },
    "prepare_handoff": {
        "description": "Prepare a handoff of deliverables and context.",
        "parameters": {
            "type": "object",
            "required": ["recipient", "documentation"],
            "properties": {
                "recipient": {"type": "string"},
                "documentation": {"type": "string"},
                "outstanding_items": {"type": "array", "items": {"type": "string"}},
            },
        },
        "time_cost": 60,
        "budget_cost": None,
    },
    "submit_final_recommendation": {
        "description": "Submit the final recommendation to close the engagement.",
        "parameters": {
            "type": "object",
            "required": ["summary", "recommendation"],
            "properties": {
                "summary": {"type": "string"},
                "recommendation": {"type": "string"},
                "justification": {"type": "string"},
                "next_steps": {"type": "array", "items": {"type": "string"}},
            },
        },
        "time_cost": 60,
        "budget_cost": None,
    },
    "propose_custom_action": {
        "description": "Propose a custom action not covered by the standard action types.",
        "parameters": {
            "type": "object",
            "required": ["action_name", "description"],
            "properties": {
                "action_name": {"type": "string"},
                "description": {"type": "string"},
                "payload": {"type": "object"},
            },
        },
        "time_cost": 10,
        "budget_cost": None,
    },
}
