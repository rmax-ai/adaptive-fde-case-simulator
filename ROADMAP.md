# AFCS Roadmap

> 8 phases from mega prompt §20. Target: working MVP with 3 seed cases, human browser UI, agent API, replay, and expert review.

---

## Phase 1: Domain Foundation

**Focus:** Core domain model — schemas, events, and state transitions. No UI, no stakeholders.

### Deliverables
- [ ] `packages/case-schema/` — Pydantic v2 case definition models
- [ ] `packages/domain/` — core domain entities (Session, Event, Participant, Artifact)
- [ ] `packages/simulation-engine/` — StateTransitionEngine, ActionRegistry
- [ ] Event model: `simulation_events` + `simulation_sessions` tables
- [ ] Alembic migrations
- [ ] Case validator CLI (`afcs case validate`)
- [ ] Replay tests (event stream → identical state)
- [ ] Property-based tests (monotonic sequences, state hashing)

**Estimated Codex sessions:** 3–4
**Dependencies:** None

---

## Phase 2: Minimal Participant Flow

**Focus:** Participant can create a session, inspect artifacts, register assumptions/risks, and submit a final recommendation.

### Deliverables
- [ ] Session creation and case loading (`POST /sessions`)
- [ ] Artifact inspection (Markdown, JSON, CSV, diagrams, code, metrics)
- [ ] Structured action execution (inspect_artifact, register_assumption, register_risk, etc.)
- [ ] Assumptions register UI
- [ ] Risk register UI
- [ ] Final recommendation submission
- [ ] `apps/api/` — FastAPI routes for all Phase 2 actions
- [ ] `apps/web/` — minimal React workspace (artifact browser, action launcher, registers)
- [ ] Integration tests: session start → artifact inspect → recommendation submit

**Estimated Codex sessions:** 3–4
**Dependencies:** Phase 1

---

## Phase 3: Stakeholders

**Focus:** Hybrid stakeholder engine — policy layer (deterministic) + language layer (LLM). Bounded dialogue.

### Deliverables
- [ ] `packages/stakeholder-engine/` — StakeholderPolicyEngine, StakeholderLanguageRenderer
- [ ] `packages/model-gateway/` — provider-neutral LLM interface, mock provider, external adapter
- [ ] Mock language provider (deterministic, offline)
- [ ] Stakeholder response pipeline (validation → policy → facts → LLM → response → persistence)
- [ ] Disclosure validation (disclosed facts ⊆ allowed facts)
- [ ] Threaded stakeholder conversation UI
- [ ] Qualitative trust signals (cooperative, hesitant, blocked, etc.)
- [ ] Integration tests: stakeholder interview → disclosure → trust change

**Estimated Codex sessions:** 3–5
**Dependencies:** Phase 2

---

## Phase 4: Evaluation

**Focus:** Automated validators, hard constraints, multi-dimensional scoring, participant reports.

### Deliverables
- [ ] `packages/evaluation-engine/` — ValidatorRegistry, EvaluationService, ReportService
- [ ] 12 automated validators (baseline defined, success criteria, decisive evidence, etc.)
- [ ] Hard constraint enforcement (fail case, cap dimension, trigger expert review)
- [ ] 6 evaluation dimensions with machine scores + evidence references
- [ ] Participant capability report generation
- [ ] Outcome scoring (final world state)
- [ ] Trajectory scoring (evidence relevance, sequencing, reversibility, etc.)
- [ ] Property-based tests (score caps, forbidden facts, budget enforcement)

**Estimated Codex sessions:** 3–4
**Dependencies:** Phase 3

---

## Phase 5: Seed Cases

**Focus:** Implement all three complete seed cases with valid/invalid trajectories and case-specific tests.

### Deliverables
- [ ] `cases/wrong-use-case/` — Wrong use-case selection (RAG vs workflow)
- [ ] `cases/unsafe-autonomy/` — Unsafe autonomy transition (recommendation → auto-approve)
- [ ] `cases/unmaintainable-prototype/` — Successful but unmaintainable prototype
- [ ] Each case: full YAML definition, artifacts, stakeholder definitions, evaluation config
- [ ] At least 2 valid trajectories per case (verified via simulation)
- [ ] At least 3 invalid trajectories per case (verified rejection)
- [ ] Reachability checks pass for all hidden facts
- [ ] Case-specific tests in `tests/case-validation/`

**Estimated Codex sessions:** 4–6
**Dependencies:** Phase 4

---

## Phase 6: Replay and Expert Review

**Focus:** Session replay timeline, expert scoring console, pairwise trajectory comparison.

### Deliverables
- [ ] Replay timeline UI (chronological events, state changes, stakeholder messages)
- [ ] Event filters by capability dimension
- [ ] Expert review console (inspect replay, score dimensions, cite events)
- [ ] Pairwise trajectory comparison (A better / B better / equivalent / incomparable)
- [ ] Machine score adjudication (override with rationale)
- [ ] Invalid case flagging for evaluators
- [ ] `packages/simulation-engine/` — ReplayService

**Estimated Codex sessions:** 2–3
**Dependencies:** Phase 5

---

## Phase 7: Agent Interface

**Focus:** Structured API for AI agents to complete simulations programmatically.

### Deliverables
- [ ] Agent API endpoints (POST/GET sessions, actions, artifacts, stakeholders, report)
- [ ] Machine-readable action schemas (parameter schemas, preconditions)
- [ ] Agent session runner (reference baseline)
- [ ] API documentation (OpenAPI/Swagger)
- [ ] Contract tests (agent API ↔ simulation engine)
- [ ] Basic reference agent that completes a case via API

**Estimated Codex sessions:** 2–3
**Dependencies:** Phase 5 (needs seed cases for testing)

---

## Phase 8: Hardening

**Focus:** Security, performance, deployment readiness.

### Deliverables
- [ ] RBAC (participant, evaluator, author, admin roles)
- [ ] Session isolation enforcement
- [ ] Rate limiting
- [ ] Content size limits
- [ ] Audit logging
- [ ] Adversarial tests (prompt injection, hidden state extraction, event tampering, etc.)
- [ ] Performance tests
- [ ] Docker Compose single-command launch
- [ ] CI pipeline (GitHub Actions: lint, type check, test, e2e)
- [ ] `.env.example`, database migrations, fixture loader, dev reset command
- [ ] Health and readiness endpoints
- [ ] Deployment documentation

**Estimated Codex sessions:** 3–4
**Dependencies:** All previous phases

---

## Total Estimate

| Phase | Codex Sessions | Key Dependency |
|-------|---------------|----------------|
| 1. Domain Foundation | 3–4 | None |
| 2. Minimal Participant Flow | 3–4 | Phase 1 |
| 3. Stakeholders | 3–5 | Phase 2 |
| 4. Evaluation | 3–4 | Phase 3 |
| 5. Seed Cases | 4–6 | Phase 4 |
| 6. Replay & Expert Review | 2–3 | Phase 5 |
| 7. Agent Interface | 2–3 | Phase 5 |
| 8. Hardening | 3–4 | All |
| **Total** | **23–33** | |

---

## Acceptance Criteria (from mega prompt §21)

- [ ] Human completes all 3 cases in browser
- [ ] AI agent completes all 3 cases via API
- [ ] Each case supports ≥2 valid strategies
- [ ] Every session is fully replayable
- [ ] Every state change attributable to an event
- [ ] Stakeholders cannot reveal forbidden facts
- [ ] Automated validators produce evidence-linked results
- [ ] Expert evaluators can override scores with rationale
- [ ] Reports show capability vector, not one score
- [ ] Hard safety failures correctly fail or cap cases
- [ ] Case validation detects unreachable hidden facts
- [ ] Core domain logic has strong test coverage
- [ ] E2E tests pass in CI
- [ ] Application runs locally with `docker compose up`
- [ ] Documentation sufficient for authoring a 4th case
