# AFCS — Decisions

Design rationale for key architectural choices.

---

## Major Assumptions

1. **Participants are engineers**, not lay users — the UI can assume technical literacy
2. **LLM quality is sufficient** for dialogue rendering (no need for SOTA models)
3. **Deterministic state is the source of truth** — LLM outputs are replaceable
4. **Local-only MVP** — no cloud deployment needed in Phase 1-7
5. **Single-tenant sessions** — no concurrent multiplayer in MVP
6. **Stakeholder behavior is authored, not learned** — policy rules are hand-written per case

---

## Key Decisions

### D-001: Python backend + React frontend

**Chosen:** Python 3.12 (FastAPI, Pydantic v2, SQLAlchemy 2) + React (TypeScript, Vite)
**Rejected:** Full-stack TypeScript, Django, Flask

**Rationale:**
- Pydantic v2 is the best-in-class schema validation library — critical for case definitions
- FastAPI's OpenAPI auto-generation serves both human UI and agent API
- SQLAlchemy 2's async support matches the event-driven architecture
- React + Vite is the most mature SPA stack with excellent TypeScript support
- Separating frontend/backend keeps the agent API independent of the UI

### D-002: Monorepo with packages/

**Chosen:** Single repo with `packages/` for shared libraries, `apps/` for deployables
**Rejected:** Separate repos per component, microservices

**Rationale:**
- Tight coupling between simulation engine, stakeholder engine, and evaluation engine — separate repos would create versioning overhead
- `packages/` enforces dependency direction (domain ← engines ← API)
- Single `uv sync` installs everything for local dev
- Easier to maintain consistency across the 8-phase build sequence

### D-003: Hybrid stakeholder (deterministic policy + LLM language)

**Chosen:** Policy layer controls facts, approvals, trust, state transitions. LLM only renders language.
**Rejected:** Pure LLM stakeholders, pure rule-based stakeholders

**Rationale:**
- Pure LLM stakeholders are non-deterministic — can't replay, can't verify, can leak hidden facts
- Pure rule-based stakeholders feel robotic and don't test real FDE soft skills
- Hybrid approach gives the best of both: auditability + realism
- LLM can be swapped (mock → external) without changing simulation behavior

### D-004: Append-only event model

**Chosen:** All state changes flow through `simulation_events` table. State materialized separately.
**Rejected:** Mutable state with audit log, event sourcing framework

**Rationale:**
- Event sourcing without the framework overhead — just an append-only table + materialized view
- Replay is trivial: replay events in sequence order
- Full audit trail without additional infrastructure
- Pre/post state hashes enable cryptographic verification of state integrity

### D-005: Multi-dimensional evaluation (not one score)

**Chosen:** 6 independent dimensions, each with machine score + human score + adjudicated final
**Rejected:** Single weighted score, percentile ranking

**Rationale:**
- FDE is not a single skill — collapsing to one score hides capability profile
- Participants may excel at discovery but fail at governance — this must be visible
- Expert evaluators can adjudicate machine scores with rationale
- Hard constraints operate independently of scores (fail/cap regardless of performance)

### D-006: PostgreSQL with JSONB for state

**Chosen:** PostgreSQL with JSONB `current_state` column + typed columns for queryable fields
**Rejected:** MongoDB, Redis, pure JSON files

**Rationale:**
- Relational integrity for sessions, cases, users — JSONB for flexible state blobs
- Alembic migrations for schema evolution
- Single database — no sync issues between document store and relational store
- JSONB is queryable (index on session status, case_id, etc.)

### D-007: Docker Compose for local dev

**Chosen:** `docker compose up` starts PostgreSQL + API + Web + mock LLM
**Rejected:** Kubernetes, manual install scripts, `uv run` only

**Rationale:**
- One command to start everything — essential for contributor onboarding
- Mock provider eliminates external API dependencies for local dev
- Production deployment is out of scope for MVP — Docker Compose is sufficient

### D-008: YAML case definitions

**Chosen:** YAML files under `cases/<name>/` — one directory per case
**Rejected:** Python classes, JSON, database-stored

**Rationale:**
- YAML is human-readable and diffable (critical for version comparison)
- File-based means no database dependency for case authoring
- One directory per case keeps artifacts, stakeholder configs, and evaluation rules together
- Pydantic v2 validates on load — same schema whether YAML or JSON

---

## Known Limitations

- **No adaptive generation in MVP** — extension points designed but not implemented (Phase 9+)
- **No I-POMDP solvers** — stakeholder behavior is authored, not inferred
- **No cloud deployment** — local Docker only, production hardening deferred
- **No hiring use** — system is for training/evaluation only, not employment decisions
- **No multiplayer** — single participant per session
- **LLM rendering quality depends on provider** — mock provider is deterministic but robotic; external provider quality varies
