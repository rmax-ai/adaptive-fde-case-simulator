"""Tests for each built-in action handler."""

from __future__ import annotations

from afcs_simulation_engine.actions import ACTION_HANDLERS


class TestActionHandlers:
    """Verify each action handler produces correct state modifications."""

    def _run(self, action_type: str, state: dict | None = None, params: dict | None = None) -> dict:
        handler = ACTION_HANDLERS.get(action_type)
        assert handler is not None, f"No handler for '{action_type}'"
        return handler(state or {}, params or {})

    # -- 1. inspect_artifact --

    def test_inspect_artifact_adds_to_inspected(self) -> None:
        result = self._run("inspect_artifact", {"artifacts_inspected": []}, {"artifact_id": "doc1"})
        assert result["artifacts_inspected"] == ["doc1"]

    def test_inspect_artifact_is_idempotent(self) -> None:
        result = self._run("inspect_artifact", {"artifacts_inspected": ["doc1"]}, {"artifact_id": "doc1"})
        assert result["artifacts_inspected"] == ["doc1"]

    def test_inspect_artifact_creates_list(self) -> None:
        result = self._run("inspect_artifact", {}, {"artifact_id": "doc1"})
        assert result["artifacts_inspected"] == ["doc1"]

    # -- 2. ask_stakeholder --

    def test_ask_stakeholder_records_question(self) -> None:
        result = self._run("ask_stakeholder", {}, {"stakeholder_id": "cto", "question": "Any risks?"})
        assert len(result["stakeholder_questions"]) == 1
        assert result["stakeholder_questions"][0]["stakeholder_id"] == "cto"

    # -- 3. interview_stakeholder --

    def test_interview_stakeholder_increases_trust(self) -> None:
        state = {"trust_scores": {"cto": 50}}
        result = self._run("interview_stakeholder", state, {"stakeholder_id": "cto", "topics": ["budget"]})
        assert result["trust_scores"]["cto"] == 55

    # -- 4. request_access --

    def test_request_access_creates_pending(self) -> None:
        result = self._run("request_access", {}, {"target": "db", "justification": "Need data"})
        assert result["access_requests"][0]["status"] == "pending"

    # -- 5. request_approval --

    def test_request_approval_creates_pending(self) -> None:
        result = self._run("request_approval", {}, {"scope": "deploy", "justification": "Ready"})
        assert result["approval_requests"][0]["status"] == "pending"

    # -- 6. register_assumption --

    def test_register_assumption(self) -> None:
        result = self._run("register_assumption", {}, {"id": "a1", "description": "API is stable"})
        assert len(result["assumptions"]) == 1
        assert result["assumptions"][0]["id"] == "a1"

    # -- 7. update_assumption --

    def test_update_assumption(self) -> None:
        state = {"assumptions": [{"id": "a1", "description": "old", "category": "general"}]}
        result = self._run("update_assumption", state, {"id": "a1", "description": "updated"})
        assert result["assumptions"][0]["description"] == "updated"

    # -- 8. register_risk --

    def test_register_risk(self) -> None:
        result = self._run("register_risk", {}, {"id": "r1", "description": "Data breach", "impact": "high"})
        assert result["risks"][0]["impact"] == "high"

    # -- 9. update_risk --

    def test_update_risk(self) -> None:
        state = {"risks": [{"id": "r1", "description": "old", "impact": "low"}]}
        result = self._run("update_risk", state, {"id": "r1", "impact": "critical"})
        assert result["risks"][0]["impact"] == "critical"

    # -- 10. define_baseline --

    def test_define_baseline_sets_baseline_and_advances_phase(self) -> None:
        result = self._run("define_baseline", {"phase": "discovery"}, {"description": "Current state"})
        assert "baseline" in result
        assert result["baseline"]["description"] == "Current state"
        assert result["phase"] == "evaluation"

    # -- 11. define_success_metric --

    def test_define_success_metric(self) -> None:
        result = self._run("define_success_metric", {}, {"name": "latency", "target": "<100ms"})
        assert result["success_metrics"][0]["name"] == "latency"

    # -- 12. propose_scope --

    def test_propose_scope(self) -> None:
        result = self._run("propose_scope", {}, {"description": "Build API", "included": ["auth"]})
        assert result["proposed_scope"]["status"] == "proposed"

    # -- 13. reject_scope --

    def test_reject_scope(self) -> None:
        state = {"proposed_scope": {"status": "proposed"}}
        result = self._run("reject_scope", state, {"reason": "Out of budget"})
        assert result["proposed_scope"]["status"] == "rejected"

    # -- 14. select_architecture --

    def test_select_architecture_advances_phase(self) -> None:
        result = self._run("select_architecture", {"phase": "evaluation"}, {"name": "Microservices"})
        assert result["selected_architecture"]["name"] == "Microservices"
        assert result["phase"] == "architecture"

    # -- 15. modify_architecture --

    def test_modify_architecture(self) -> None:
        state = {"selected_architecture": {"name": "Monolith", "components": []}}
        result = self._run("modify_architecture", state, {"change": "Split auth module"})
        assert len(result["selected_architecture"]["modifications"]) == 1

    # -- 16. define_evaluation --

    def test_define_evaluation(self) -> None:
        result = self._run("define_evaluation", {}, {"baseline": "v1.0", "metrics": ["accuracy"]})
        assert result["evaluation_plan"]["baseline"] == "v1.0"

    # -- 17. run_analysis --

    def test_run_analysis_deducts_budget(self) -> None:
        result = self._run("run_analysis", {"budget_remaining": 50000}, {"findings": "Bug found", "cost": 500})
        assert result["budget_remaining"] == 49500

    # -- 18. run_pilot --

    def test_run_pilot_advances_phase(self) -> None:
        result = self._run("run_pilot", {"phase": "architecture", "budget_remaining": 50000},
                           {"scope": "Test", "cost": 5000})
        assert result["pilot"]["status"] == "running"
        assert result["phase"] == "delivery"
        assert result["budget_remaining"] == 45000

    # -- 19. inspect_pilot_result --

    def test_inspect_pilot_result(self) -> None:
        state = {"pilot": {"status": "running"}}
        result = self._run("inspect_pilot_result", state, {"summary": "All good"})
        assert result["pilot"]["status"] == "completed"

    # -- 20. escalate_issue --

    def test_escalate_issue(self) -> None:
        result = self._run("escalate_issue", {}, {"issue": "Security flaw", "impact": "Critical"})
        assert result["escalated_issues"][0]["issue"] == "Security flaw"

    # -- 21. communicate_decision --

    def test_communicate_decision(self) -> None:
        result = self._run("communicate_decision", {}, {"decision": "Proceed", "audience": "team"})
        assert result["decisions"][0]["decision"] == "Proceed"

    # -- 22. define_rollout --

    def test_define_rollout(self) -> None:
        result = self._run("define_rollout", {}, {"strategy": "Canary", "phases": ["10%", "50%", "100%"]})
        assert result["rollout_plan"]["strategy"] == "Canary"

    # -- 23. define_rollback --

    def test_define_rollback(self) -> None:
        result = self._run("define_rollback", {}, {"trigger_conditions": ["error_rate > 1%"]})
        assert "trigger_conditions" in result["rollback_plan"]

    # -- 24. assign_owner --

    def test_assign_owner(self) -> None:
        result = self._run("assign_owner", {}, {"owner": "alice", "role": "tech_lead"})
        assert result["owner"] == "alice"

    # -- 25. prepare_handoff --

    def test_prepare_handoff(self) -> None:
        result = self._run("prepare_handoff", {}, {"recipient": "ops", "documentation": "README"})
        assert result["handoff"]["status"] == "prepared"

    # -- 26. submit_final_recommendation --

    def test_submit_final_recommendation_completes(self) -> None:
        result = self._run("submit_final_recommendation", {"phase": "reporting"},
                           {"summary": "Done", "recommendation": "Launch"})
        assert result["status"] == "completed"
        assert result["phase"] == "completed"

    # -- 27. propose_custom_action --

    def test_propose_custom_action(self) -> None:
        result = self._run("propose_custom_action", {}, {"action_name": "custom_review", "description": "..."})
        assert result["custom_actions"][0]["action_name"] == "custom_review"

    # -- All handlers are pure (no side effects on input) --

    def test_handlers_are_pure_functions(self) -> None:
        """Handlers must not mutate the input state."""
        original = {"phase": "discovery", "budget_remaining": 50000}
        state = dict(original)
        self._run("inspect_artifact", state, {"artifact_id": "doc1"})
        assert state == original  # input unchanged
