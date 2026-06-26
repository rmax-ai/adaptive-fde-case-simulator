# AFCS — Specification

## Scope

A browser-based application where participants enter simulated enterprise AI engagements.
Evaluates and trains human engineers and AI agents on realistic Forward Deployed Engineer
work — discovery, diagnosis, architecture, governance, delivery, and operations.

MVP domain: enterprise support and refund operations. 3 seed cases, 4-6 stakeholders per case.

---

## Features

### Simulation Engine
- Deterministic state transitions with append-only event model
- Hidden canonical state + participant-visible state
- Structured actions with preconditions, effects, time/budget costs
- Session replay from initial state + event stream
- Materialized state for efficient reads

### Hybrid Stakeholder Engine
- Policy layer controls facts, permissions, approvals, state transitions
- LLM renders conversational language only
- Response pipeline: validation → policy → facts → LLM → persistence
- Disclosure validation (disclosed ⊆ allowed)
- Qualitative trust signals (no numeric scores exposed)

### Multi-Dimensional Evaluation
- 6 dimensions: Discovery, Technical, Evaluation, Delivery, Governance, Sustainability
- Automated validators with evidence references
- Hard constraints (fail case, cap dimension, trigger review)
- Expert review console with score adjudication
- Participant capability report (vector, not single score)
- Pairwise trajectory comparison

### Participant Workspace (Browser)
- Multi-pane layout: overview, communications, artifacts, stakeholders, registers
- Architecture workspace (component palette, structured JSON output)
- Evaluation workspace (baseline, metrics, failure classes, thresholds)
- Threaded stakeholder conversations (email/Slack-like)
- Assumptions and risk registers
- Final recommendation submission

### Agent API
- RESTful endpoints for programmatic simulation
- Machine-readable action schemas
- Session state, artifacts, stakeholders, events, report

### Case Authoring
- YAML case definitions with Pydantic v2 validation
- CLI toolkit (validate, simulate, inspect, test-reachability, diff)
- Hidden-fact reachability checks
- Version comparison

### Seed Cases
1. **Wrong use-case selection** — RAG assistant vs workflow redesign
2. **Unsafe autonomy transition** — recommendation → auto-approve without safeguards
3. **Successful but unmaintainable prototype** — scaling a brittle bespoke system

---

## Acceptance Criteria

### Phase 1 — Domain Foundation
- [ ] AC-1: Case schema validates all seed cases without errors
- [ ] AC-2: Event model supports append-only writes with monotonic sequences
- [ ] AC-3: State transition engine applies deterministic effects from actions
- [ ] AC-4: Replay from event stream produces identical state
- [ ] AC-5: Property-based tests verify monotonicity and state hashing

### Phase 2 — Participant Flow
- [ ] AC-6: Participant can create session, inspect artifacts, register assumptions/risks
- [ ] AC-7: Structured actions execute with validation and precondition checks
- [ ] AC-8: Final recommendation can be submitted
- [ ] AC-9: Integration test: session start → artifacts → recommendation

### Phase 3 — Stakeholders
- [ ] AC-10: Stakeholder policy engine controls fact disclosure
- [ ] AC-11: Mock provider generates deterministic stakeholder responses
- [ ] AC-12: Disclosure validation rejects forbidden facts
- [ ] AC-13: Trust changes are applied based on participant actions
- [ ] AC-14: Stakeholder messages are persisted in event stream

### Phase 4 — Evaluation
- [ ] AC-15: All 12 automated validators produce evidence-linked results
- [ ] AC-16: Hard constraints correctly fail or cap cases
- [ ] AC-17: 6 evaluation dimensions produce independent scores
- [ ] AC-18: Participant report includes capability vector, strengths, failures

### Phase 5 — Seed Cases
- [ ] AC-19: Case 1 supports ≥2 valid trajectories
- [ ] AC-20: Case 2 supports ≥2 valid trajectories
- [ ] AC-21: Case 3 supports ≥2 valid trajectories
- [ ] AC-22: All hidden facts are reachable via at least one action path
- [ ] AC-23: Strong and weak trajectories produce different score vectors

### Phase 6 — Replay & Expert Review
- [ ] AC-24: Session replay shows chronological events with state diffs
- [ ] AC-25: Expert evaluator can score dimensions with event citations
- [ ] AC-26: Pairwise comparison of two trajectories works correctly

### Phase 7 — Agent Interface
- [ ] AC-27: Agent API exposes all actions with machine-readable schemas
- [ ] AC-28: Reference agent completes a case via API
- [ ] AC-29: Contract tests verify API ↔ simulation engine compliance

### Phase 8 — Hardening
- [ ] AC-30: RBAC enforces participant/evaluator/author/admin separation
- [ ] AC-31: Adversarial tests pass (prompt injection, state extraction, score manipulation)
- [ ] AC-32: `docker compose up` starts all services without errors
- [ ] AC-33: CI pipeline passes (lint, type check, test, e2e)
- [ ] AC-34: All core domain logic has >80% test coverage

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript 5, Vite 6, TanStack Query |
| Backend | Python 3.12, FastAPI, Pydantic v2 |
| Database | PostgreSQL 16, SQLAlchemy 2, Alembic |
| LLM Gateway | Provider-neutral interface (mock + external adapter) |
| Observability | OpenTelemetry |
| Testing | pytest, Playwright, hypothesis |
| Dev Env | Docker Compose |
| CI | GitHub Actions |

---

## Non-Goals (MVP)

- Live enterprise integrations
- Unrestricted internet/shell access
- Fully autonomous case generation
- Model training
- High-stakes hiring decisions
- Multiplayer simulations
- Full cloud infrastructure emulation
- I-POMDP solvers
- OAuth token exchange
- Automatic promotion of generated cases
