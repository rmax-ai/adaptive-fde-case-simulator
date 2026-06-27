#!/usr/bin/env python3
"""Baseline agent that completes a simulation via the AFCS API.

This script demonstrates a simple heuristic policy for AI agents:
1. Load a case and create a session
2. Inspect all initially visible artifacts
3. Interview each stakeholder once
4. Register assumptions and risks
5. Define baseline and select architecture
6. Submit final recommendation

Usage:
    python scripts/baseline_agent.py [--case wrong_use_case] [--base-url http://localhost:8000]
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

import httpx

# ── Agent State ──────────────────────────────────────────────────────────


class AgentContext:
    """Tracking context for the baseline agent."""

    def __init__(self, case_id: str, base_url: str) -> None:
        self.case_id = case_id
        self.base_url = base_url.rstrip("/")
        self.session_id: str | None = None
        self.client = httpx.Client(base_url=self.base_url, timeout=30.0)


# ── API Helpers ──────────────────────────────────────────────────────────


def create_session(ctx: AgentContext) -> str:
    """Create a new session via the API and return the session ID."""
    resp = ctx.client.post("/api/v1/sessions", json={"case_id": ctx.case_id})
    resp.raise_for_status()
    data = resp.json()
    session_id = data["id"]
    ctx.session_id = session_id
    print(f"[agent] Created session {session_id} for case '{ctx.case_id}'")
    print(f"[agent]   Initial phase: {data.get('visible_state', {}).get('phase', 'unknown')}")
    print(f"[agent]   Budget: ${data.get('visible_state', {}).get('budget_remaining', 0):.0f}")
    return str(session_id)


def get_agent_state(ctx: AgentContext) -> dict[str, Any]:
    """Get the full agent state from the agent API."""
    resp = ctx.client.get(f"/api/v1/agent/sessions/{ctx.session_id}/state")
    resp.raise_for_status()
    return resp.json()


def get_available_actions(ctx: AgentContext) -> list[dict[str, Any]]:
    """Get available action schemas."""
    resp = ctx.client.get(f"/api/v1/agent/sessions/{ctx.session_id}/actions")
    resp.raise_for_status()
    return resp.json()


def execute_action(
    ctx: AgentContext,
    action_type: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute an action and return the result."""
    payload = {"action_type": action_type, "params": params or {}}
    resp = ctx.client.post(f"/api/v1/agent/sessions/{ctx.session_id}/actions", json=payload)
    return resp.json()


# ── Agent Policy ─────────────────────────────────────────────────────────


def run_baseline_agent(ctx: AgentContext) -> dict[str, Any]:
    """Run the baseline agent policy through a complete simulation."""
    # 1. Create session
    session_id = create_session(ctx)
    if not session_id:
        sys.exit(1)

    state = get_agent_state(ctx)
    print(f"[agent] Phase: {state['phase']}, status: {state['status']}")

    # 2. Inspect all initially visible artifacts
    print("\n[agent] --- Phase: Inspect all visible artifacts ---")
    artifacts = state.get("artifacts", [])
    print(f"[agent] Found {len(artifacts)} visible artifacts")
    for artifact in artifacts:
        result = execute_action(
            ctx,
            "inspect_artifact",
            {"artifact_id": artifact.get("id", "")},
        )
        if result.get("success"):
            print(f"[agent]   Inspected artifact: {artifact.get('name', artifact.get('id'))}")
        else:
            print(f"[agent]   Failed to inspect {artifact.get('id')}: {result.get('error')}")

    # 3. Interview each stakeholder once
    print("\n[agent] --- Phase: Interview stakeholders ---")
    state = get_agent_state(ctx)
    stakeholders = state.get("stakeholders", [])
    print(f"[agent] Found {len(stakeholders)} stakeholders")
    for stakeholder in stakeholders:
        sid = stakeholder.get("id", "")
        result = execute_action(
            ctx,
            "interview_stakeholder",
            {
                "stakeholder_id": sid,
                "topics": ["goals", "constraints", "needs"],
                "notes": f"Initial interview with {stakeholder.get('role', sid)}",
            },
        )
        if result.get("success"):
            print(f"[agent]   Interviewed {stakeholder.get('role', sid)} ({sid})")
        else:
            print(f"[agent]   Failed to interview {sid}: {result.get('error')}")

    # 4. Register assumptions
    print("\n[agent] --- Phase: Register assumptions ---")
    execute_action(
        ctx,
        "register_assumption",
        {
            "description": "Users will need training on any new system",
            "category": "stakeholder",
        },
    )
    print("[agent]   Registered assumption: user training needs")

    execute_action(
        ctx,
        "register_assumption",
        {
            "description": "Current ticket volume requires automated solution",
            "category": "business",
        },
    )
    print("[agent]   Registered assumption: ticket volume justifies automation")

    # 5. Register risks
    print("\n[agent] --- Phase: Register risks ---")
    execute_action(
        ctx,
        "register_risk",
        {
            "description": "GenAI may hallucinate on unstructured ticket data",
            "impact": "high",
            "likelihood": "medium",
            "mitigation": "Use rule-based routing as fallback",
        },
    )
    print("[agent]   Registered risk: GenAI hallucination")

    # 6. Define baseline (advances phase to evaluation)
    print("\n[agent] --- Phase: Define baseline ---")
    execute_action(
        ctx,
        "define_baseline",
        {
            "description": "Current manual ticket routing baseline",
            "metrics": ["tickets_per_day", "resolution_time", "accuracy"],
        },
    )
    print("[agent]   Defined baseline, advanced to evaluation phase")

    # 7. Define success metrics
    print("\n[agent] --- Phase: Define success metrics ---")
    execute_action(
        ctx,
        "define_success_metric",
        {
            "name": "Accuracy",
            "target": ">95% automated routing accuracy",
            "measurement": "A/B comparison",
        },
    )
    execute_action(
        ctx,
        "define_success_metric",
        {
            "name": "Resolution Time",
            "target": "Reduce by 40%",
            "measurement": "Track mean time to resolve",
        },
    )
    print("[agent]   Defined success metrics")

    # 8. Propose scope
    print("\n[agent] --- Phase: Propose scope ---")
    execute_action(
        ctx,
        "propose_scope",
        {
            "description": "Implement rule-based workflow automation for ticket routing",
            "included": ["Ticket analysis", "Rule engine", "Dashboard"],
            "excluded": ["GenAI integration", "Full CRM replacement"],
        },
    )
    print("[agent]   Proposed scope")

    # 9. Select architecture (advances to architecture phase)
    print("\n[agent] --- Phase: Select architecture ---")
    execute_action(
        ctx,
        "select_architecture",
        {
            "name": "Rule-based workflow automation",
            "description": "Drools-based rule engine with CRM integration",
            "components": ["Rule engine", "CRM adapter", "Dashboard UI"],
            "rationale": "Cost-effective, proven technology, no hallucination risk",
        },
    )
    print("[agent]   Selected architecture, advanced to architecture phase")

    # 10. Run analysis
    print("\n[agent] --- Phase: Run analysis ---")
    execute_action(
        ctx,
        "run_analysis",
        {
            "type": "cost-benefit",
            "findings": "Rule-based automation is 10x cheaper than GenAI for structured routing",
            "conclusion": "Rule-based approach recommended",
        },
    )
    print("[agent]   Ran cost-benefit analysis")

    # 11. Run pilot (advances to delivery phase)
    print("\n[agent] --- Phase: Run pilot ---")
    execute_action(
        ctx,
        "run_pilot",
        {
            "scope": "Route 10% of tickets through rule engine",
            "duration": "2 weeks",
            "metrics": ["accuracy", "speed", "user_satisfaction"],
        },
    )
    print("[agent]   Launched pilot, advanced to delivery phase")

    # 12. Inspect pilot results
    print("\n[agent] --- Phase: Inspect pilot results ---")
    execute_action(
        ctx,
        "inspect_pilot_result",
        {
            "summary": "Rule engine achieved 97% routing accuracy in pilot",
            "metrics_achieved": {"accuracy": 97, "speed_improvement": 35},
            "issues_found": ["CRM rate limiting needs tuning"],
        },
    )
    print("[agent]   Inspected pilot results")

    # 13. Define rollout
    print("\n[agent] --- Phase: Define rollout ---")
    execute_action(
        ctx,
        "define_rollout",
        {
            "strategy": "Phased rollout starting with support team",
            "phases": ["Phase 1: 25%", "Phase 2: 50%", "Phase 3: 100%"],
            "timeline": "4 weeks",
        },
    )
    print("[agent]   Defined rollout strategy")

    # 14. Define rollback
    print("\n[agent] --- Phase: Define rollback ---")
    execute_action(
        ctx,
        "define_rollback",
        {
            "trigger_conditions": ["Accuracy below 90%", "User complaints > 5%"],
            "rollback_steps": ["Revert to manual routing", "Notify team"],
            "verification": "Confirm all tickets are being routed correctly",
        },
    )
    print("[agent]   Defined rollback plan")

    # 15. Prepare handoff (requires reporting phase - advance via prepare_handoff)
    print("\n[agent] --- Phase: Prepare handoff ---")
    execute_action(
        ctx,
        "prepare_handoff",
        {
            "recipient": "Engineering team",
            "documentation": "Rule engine spec, deployment guide, runbook",
            "outstanding_items": ["CRM tuning", "User training materials"],
        },
    )
    print("[agent]   Prepared handoff")

    # 16. Submit final recommendation
    print("\n[agent] --- Phase: Submit final recommendation ---")
    result = execute_action(
        ctx,
        "submit_final_recommendation",
        {
            "summary": "The GenAI-based solution is the wrong approach for this case. "
            "A rule-based workflow automation engine is the correct solution.",
            "recommendation": "Implement rule-based workflow automation instead of GenAI",
            "justification": (
                "1. Rule-based engine is sufficient for structured ticket routing\\n"
                "2. GenAI risks hallucination on unstructured ticket data\\n"
                "3. Rule-based approach is 10x cheaper and proven\\n"
                "4. No cloud infrastructure needed for model hosting\\n"
                "5. Faster deployment: 4 weeks vs 12+ weeks for GenAI"
            ),
            "next_steps": [
                "Build rule engine",
                "Integrate with CRM",
                "Train support team",
                "Run phased rollout",
            ],
        },
    )
    if result.get("success"):
        print("[agent]   Submitted final recommendation - session completed!")
    else:
        print(f"[agent]   Failed to submit: {result.get('error')}")

    # Final state
    final_state = get_agent_state(ctx)
    print(f"\n[agent] Final status: {final_state['status']}")
    print(f"[agent] Final phase: {final_state['phase']}")
    print(f"[agent] Events recorded: {final_state['event_count']}")
    print("[agent] Simulation complete!")

    return final_state


# ── Main ─────────────────────────────────────────────────────────────────


def main() -> None:
    """Parse arguments and run the baseline agent."""
    parser = argparse.ArgumentParser(description="AFCS Baseline Agent")
    parser.add_argument(
        "--case",
        default="wrong_use_case",
        help="Case ID to simulate (default: wrong_use_case)",
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL of the AFCS API (default: http://localhost:8000)",
    )
    args = parser.parse_args()

    ctx = AgentContext(case_id=args.case, base_url=args.base_url)

    # Verify API is reachable
    try:
        health = ctx.client.get("/health")
        health.raise_for_status()
        print(f"[agent] Connected to AFCS API at {args.base_url}")
    except httpx.ConnectError:
        print(f"[agent] ERROR: Cannot connect to {args.base_url}. Is the server running?")
        sys.exit(1)

    run_baseline_agent(ctx)


if __name__ == "__main__":
    main()
