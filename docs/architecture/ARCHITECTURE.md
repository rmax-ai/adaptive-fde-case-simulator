# AFCS Architecture

> **Adaptive Forward Deployed Engineer Case Simulator**
> Phase 0a — Architecture Specification
> Senior Software Architecture Review

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Component Architecture](#component-architecture)
4. [Request Lifecycle](#request-lifecycle)
5. [Trust Boundaries](#trust-boundaries)
6. [Event Model](#event-model)
7. [Action System](#action-system)
8. [Evaluation Model](#evaluation-model)
9. [Stakeholder Model](#stakeholder-model)
10. [Seed Cases](#seed-cases)
11. [Case Authoring Toolkit](#case-authoring-toolkit)
12. [API Design](#api-design)
13. [Data Model](#data-model)
14. [Deployment Topology](#deployment-topology)
15. [Risks, Trade-offs, Open Questions](#risks-trade-offs-open-questions)

---

## Executive Summary

The Adaptive Forward Deployed Engineer Case Simulator (AFCS) is a browser-based, stateful simulation platform that evaluates and trains human engineers and AI agents on realistic Forward Deployed Engineer (FDE) work. The system implements a strict separation between hidden canonical state and participant-visible state, using deterministic state transitions driven by structured participant actions and bounded generative LLM dialogue for stakeholder responses. AFCS employs an append-only event model for full replayability, a multi-dimensional evaluation framework (six axes) with automated validators and expert review, and a policy-engineered stakeholder simulation that constrains LLM output to factual bounds. The architecture is designed as a monorepo with three-tier separation — frontend (React + Vite + TanStack Query), backend API (FastAPI + Pydantic v2 + PostgreSQL), and domain packages (simulation engine, evaluation engine, stakeholder engine, model gateway) — enabling both human browser-based participation and programmatic AI agent access through a RESTful agent API.

---

## Architecture Overview

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Participant Layer                           │
│                                                                     │
│  ┌──────────────────────┐         ┌──────────────────────────┐      │
│  │   Web UI (Browser)   │         │   AI Agent (API Client)  │      │
│  │  React + TypeScript  │         │   REST / JSON over HTTP  │      │
│  │  Vite + TanStack Q.  │         │                          │      │
│  └──────────┬───────────┘         └─────────────┬────────────┘      │
│             │                                   │                   │
└─────────────┼───────────────────────────────────┼───────────────────┘
              │           HTTP (TLS)              │
              ▼                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       API Server (FastAPI)                          │
│                                                                     │
│  ┌────────────┐ ┌────────────┐ ┌──────────────┐ ┌───────────────┐  │
│  │  Session   │ │   Action   │ │Stakeholder   │ │  Evaluation   │  │
│  │  Routes    │ │  Routes    │ │ Routes       │ │  Routes       │  │
│  └─────┬──────┘ └─────┬──────┘ └──────┬───────┘ └───────┬───────┘  │
│        │              │               │                 │          │
└────────┼──────────────┼───────────────┼─────────────────┼──────────┘
         │              │               │                 │
         ▼              ▼               ▼                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       Domain Service Layer                           │
│                                                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │ Simulation Engine│  │Stakeholder Engine│  │ Evaluation Engine│  │
│  │                  │  │                  │  │                  │  │
│  │• State Machine   │  │• Policy Layer    │  │• Validators      │  │
│  │• Action Registry │  │• Language Render │  │• Hard Constraints│  │
│  │• Event Model     │  │• Fact Bounds     │  │• Scoring Engine  │  │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘  │
│           │                     │                      │           │
│  ┌──────────────────┐  ┌──────────────────┐            │           │
│  │ Model Gateway    │  │ Case Repository  │            │           │
│  │ • Provider-Agnos.│  │ • Case Schema    │            │           │
│  │ • Retry/Circuit  │  │ • Validation     │            │           │
│  │ • Token Mgmt     │  │ • CLI Toolkit    │            │           │
│  └──────────────────┘  └──────────────────┘            │           │
└────────────────────────┬───────────────────────────────┼───────────┘
                         │                               │
                         ▼                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Data Layer                                   │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                   PostgreSQL Database                         │   │
│  │                                                               │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────┐   │   │
│  │  │  Cases   │ │ Sessions │ │ Events   │ │ Participants   │   │   │
│  │  ├──────────┤ ├──────────┤ ├──────────┤ ├────────────────┤   │   │
│  │  │ Cases    │ │ Sessions │ │ Sim.     │ │ Participants   │   │   │
│  │  │ (canonic)│ │ (run)    │ │ Events   │ │ + Credentials  │   │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └────────────────┘   │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐                     │   │
│  │  │ Evalua-  │ │ Reports  │ │ Stake-   │                     │   │
│  │  │ tions    │ │          │ │ holders  │                     │   │
│  │  └──────────┘ └──────────┘ └──────────┘                     │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    Alembic Migrations                          │   │
│  │        (versioned, immutable migrations only)                 │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### Separation of Concerns

| Layer | Responsibility | Can Access |
|-------|---------------|------------|
| **Web UI** | Participant workspace, visual state, action composition | Participant-visible state only |
| **API Server** | HTTP routing, auth, session mgmt, orchestration | All state (trusted intermediary) |
| **Simulation Engine** | State transitions, action validation, event persistence | Hidden + visible state |
| **Stakeholder Engine** | Policy enforcement, dialogue rendering | Case policy config, hidden state (read) |
| **Evaluation Engine** | Scoring, validation, reports | All state (read-only) |
| **Model Gateway** | LLM provider abstraction, retry, token accounting | Prompt text, model config |
| **Case Schema** | Case definition, validation, authoring tools | Case YAML/JSON definitions |

### Tech Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Frontend | React 18, TypeScript, Vite, TanStack Query | Type safety, fast dev, declarative data fetching |
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic | Type-safe API contracts, async-native, mature ORM |
| Database | PostgreSQL 16 | Relational integrity, JSONB for flexible event data, pg_stat_statements |
| Containerization | Docker Compose (dev), Docker + Kubernetes (prod) | Reproducible environments, horizontal scaling |
| CI/CD | GitHub Actions | Monorepo-aware workflows, matrix testing |
| LLM Providers | OpenAI, Anthropic (via Model Gateway) | Abstraction for provider diversity |

---

## Component Architecture

### 1. Web UI (`apps/web/`)

**Stack:** React 18, TypeScript, Vite, TanStack Query, Tailwind CSS, Monaco Editor

**Responsibilities:**
- Render the multi-pane participant workspace (case brief, chat, artifact editor, system log, evaluation dashboard)
- Compose structured actions from user input (chat messages, file uploads, approval requests, configuration edits)
- Display participant-visible state only — never exposes hidden canonical state keys or simulation metadata
- Maintain optimistic UI updates with TanStack Query cache invalidation on action confirmation
- Provide an artifact viewer/editor with language-aware syntax highlighting (YAML, JSON, Python, Markdown)
- Render stakeholder dialogue in a chat UI with typing indicators and timestamp tracing
- Display evaluation results in a dimensional scorecard with breakdowns

**Multi-Pane Workspace Layout:**
```
┌─────────────────────────────────────────────────────┐
│  Header: Case Title | Timer | Score Overview (dim)  │
├──────────┬──────────────────────────┬────────────────┤
│  Case    │   Main Workspace         │  System Log    │
│  Brief   │                          │                │
│          │  ┌────────────────────┐  │  • Action recv │
│  • Context│  │  Chat / Stakeholder│  │  • State trans │
│  • Goals  │  │  Dialogue Pane    │  │  • Event ID    │
│  • Constr.│  │                   │  │  • Timestamps  │
│          │  └────────────────────┘  │                │
│  Actions  │  ┌────────────────────┐  │  Hidden State  │
│  Avail:   │  │  Artifact Editor/  │  │  Indicators    │
│  • Chat   │  │  Viewer (Monaco)   │  │  (opaque)      │
│  • Upload │  │                   │  │                │
│  • Approv │  └────────────────────┘  │                │
│  • Config │                          │                │
├──────────┴──────────────────────────┴────────────────┤
│  Action Bar: [Submit] [Save Draft] [Request Approval]│
└─────────────────────────────────────────────────────┘
```

**Key Design Decisions:**
- No direct database access — all data flows through API Server
- TanStack Query mutations for all state-changing operations (automatic retry, cache invalidation)
- React Router with session-scoped routes (`/sessions/:sessionId/`)
- WebSocket or SSE for real-time stakeholder responses and state updates

### 2. API Server (`apps/api/`)

**Stack:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, PostgreSQL

**Responsibilities:**
- Expose RESTful endpoints for session lifecycle, action submission, evaluation retrieval
- Handle authentication and authorization (JWT-based, session-scoped)
- Orchestrate domain services (Simulation Engine, Stakeholder Engine, Evaluation Engine)
- Manage database transactions with proper isolation levels
- Serve machine-readable action schemas for AI agent integration
- Provide WebSocket endpoint for real-time push of state changes

**Route Architecture:**
```
/api/v1
├── /health                          # Health check
├── /cases                           # Case CRUD (admin)
│   ├── GET    /                      # List cases
│   ├── GET    /{case_id}             # Get case definition
│   └── POST   /validate              # Validate case schema
├── /sessions                        # Session management
│   ├── POST   /                      # Create session (select case)
│   ├── GET    /{session_id}          # Get session state (visible)
│   ├── POST   /{session_id}/actions  # Submit action
│   ├── GET    /{session_id}/events   # Get event history
│   ├── GET    /{session_id}/state    # Get current visible state
│   └── GET    /{session_id}/actions/schema  # Get available actions
├── /stakeholders                    # Stakeholder dialogue
│   ├── GET    /{session_id}/stakeholders    # List stakeholders
│   └── POST   /{session_id}/stakeholders/{id}/chat  # Send message
├── /evaluations                     # Evaluation endpoints
│   ├── GET    /{session_id}/evaluation       # Get evaluation
│   ├── GET    /{session_id}/report           # Get full report
│   └── POST   /{session_id}/evaluation/expert  # Submit expert review
├── /artifacts                       # Artifact management
│   ├── POST   /{session_id}/artifacts        # Upload artifact
│   ├── GET    /{session_id}/artifacts/{id}   # Get artifact
│   └── DELETE /{session_id}/artifacts/{id}   # Remove artifact (if allowed)
└── /admin                           # Admin endpoints
    ├── GET    /sessions              # All sessions (admin)
    ├── POST   /cases/seed            # Load seed cases
    └── GET    /system/status         # System diagnostics
```

**Middleware Stack:**
1. **CORS** — configured for frontend origin
2. **Auth** — JWT verification, session-scoped
3. **Request ID** — UUID per request for tracing
4. **Rate Limiting** — per-participant, configurable
5. **Transaction** — SQLAlchemy session per request
6. **Error Handler** — structured error responses
7. **Audit Log** — request/response logging (no PII)

### 3. Simulation Engine (`packages/simulation-engine/`)

**Responsibilities:**
- Maintain the canonical state machine for each session
- Validate incoming actions against preconditions and type constraints
- Execute deterministic state transitions
- Emit and persist events to the append-only event table
- Compute pre/post state hashes for each transition (integrity verification)
- Provide materialized state reconstruction from event stream

**Core Interface:**
```
class StateTransitionEngine:
    def validate_action(session: Session, action: Action) -> ValidationResult
    def execute_action(session: Session, action: Action) -> Event
    def compute_state_hash(state: CanonicalState) -> str
    def replay_events(session_id: UUID) -> CanonicalState

class ActionRegistry:
    def register_action(action_type: str, handler: ActionHandler)
    def get_action_schema(action_type: str) -> dict
    def get_available_actions(state: CanonicalState) -> list[ActionSchema]
```

**State Transition Contract:**
- Deterministic: Given same (state, action), always produces same (next_state, events)
- No side effects beyond event emission and state mutation
- Pure functions where possible — all I/O (LLM, DB) handled by orchestration layer
- State is versioned with monotonically increasing sequence numbers

### 4. Stakeholder Engine (`packages/stakeholder-engine/`)

**Responsibilities:**
- Implement the two-layer stakeholder simulation architecture
- **Policy Layer (Deterministic):** Evaluate participant actions against case policy rules to determine:
  - What facts the stakeholder knows and can reveal
  - What response category applies (approval, rejection, request for info, escalation)
  - What constraints bind the language output (do not reveal X, do not approve outside criteria)
- **Language Layer (LLM):** Render policy-determined response in character-appropriate natural language
- Never allow LLM control over permissions, approvals, or state transitions

**Architecture:**
```
Participant Action
       │
       ▼
┌─────────────────────────────┐
│   Policy Engine             │
│   (Deterministic — pure)    │
│                             │
│  • Rule matching            │
│  • Fact availability check  │
│  • Response classification  │
│  • Constraint generation    │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│   Language Renderer         │
│   (LLM — bounded generatn)  │
│                             │
│  • System prompt + policy   │
│  • Character persona        │
│  • Response generation      │
│  • Constraint enforcement   │
└──────────┬──────────────────┘
           │
           ▼
    Stakeholder Response
```

**Policy Rules (examples):**
- `stakeholder.technical_lead.knows_about(X)` — fact availability
- `stakeholder.technical_lead.can_approve(feature)` — permission boundary
- `response_condition(participant_has_completed_stage, "escalation")` — state-dependent responses
- `constraint(do_not_reveal: "canonical_context.risk_assessment")` — information firewall

### 5. Evaluation Engine (`packages/evaluation-engine/`)

**Responsibilities:**
- Coordinate multi-dimensional evaluation across 6 axes
- Run automated validators against session events and state
- Enforce hard constraints (e.g., "must produce security assessment", "must not leak secrets")
- Compute dimension scores with weighted sub-criteria
- Aggregate automated + expert review into final report

**Core Interface:**
```
class EvaluationService:
    def evaluate_session(session: Session) -> EvaluationResult
    def get_dimension_scores(evaluation_id: UUID) -> DimensionScores
    def submit_expert_review(evaluation_id: UUID, review: ExpertReview)

class ValidatorRegistry:
    def register_validator(name: str, validator: Validator)
    def run_validators(session: Session) -> list[ValidationResult]

class HardConstraint:
    def check(session: Session) -> Violation | None
    violation_type: str
    severity: Literal["critical", "major", "minor"]
```

### 6. Model Gateway (`packages/model-gateway/`)

**Responsibilities:**
- Provide a provider-agnostic interface for LLM calls
- Support OpenAI and Anthropic providers with configurable models
- Implement retry logic with exponential backoff
- Provide circuit breaker pattern for provider failures
- Track token usage per session (cost accounting)
- Enforce max token limits and timeout configurations

**Core Interface:**
```
class ModelProviderRegistry:
    def get_provider(name: str) -> BaseModelProvider
    def list_providers() -> list[ProviderInfo]

class BaseModelProvider:
    async def generate(prompt: str, config: ModelConfig) -> ModelResponse
    async def generate_stream(prompt: str, config: ModelConfig) -> AsyncIterator[str]

class ModelConfig:
    provider: str
    model: str
    temperature: float
    max_tokens: int
    timeout: int
```

### 7. Case Schema (`packages/case-schema/`)

**Responsibilities:**
- Define Pydantic v2 models for case definitions
- Provide validation (schema conformance, reachability analysis, completeness checks)
- Supply a CLI toolkit for case authors to create, validate, and test cases
- Enforce the case definition contract: required sections, type constraints, policy completeness

**Case Definition Structure:**
```yaml
# schema/example-case.yaml
case:
  id: wrong-use-case
  title: "The Wrong Use Case"
  version: "1.0.0"
  description: "Participant identifies a GenAI solution mismatch"
  difficulty: intermediate
  estimated_minutes: 45

context:
  briefing: |
    A mid-market retailer wants to implement GenAI for...
  goals:
    - "Identify the mismatch between customer problem and AI solution"
    - "Propose the correct non-AI alternative"
    - "Deliver a recommendation document to the CTO"
  constraints:
    - "Must complete within $50k budget"
    - "Cannot propose a different AI vendor"

stakeholders:
  - id: cto
    name: "Marcus Chen"
    role: "Chief Technology Officer"
    persona: "Technical, budget-conscious, previous failed AI project"
    policy_rules:
      - file: "policies/cto.policy.yaml"

actions:
  chat:
    - type: chat_message
      params:
        recipient: str
        message: str
  upload:
    - type: upload_artifact
      params:
        filename: str
        content: str (base64)
        type: Literal["pdf", "docx", "md", "yaml", "json"]
  request_approval:
    - type: request_approval
      params:
        scope: str
        justification: str

initial_state:
  phase: discovery
  budget_remaining: 50000
  artifacts: []
  stakeholder_relationships:
    cto: 50  # trust score 0-100
  flags:
    - has_warned_about_ai_mismatch: false

hidden_state:
  correct_solution: "Use rule-based recommendation engine, not GenAI"
  risk_explosion: true  # GenAI will fail here, costing $200k+
  evaluation_criteria:
    discovery_weight: 0.30
    technical_weight: 0.20
    delivery_weight: 0.25
    governance_weight: 0.10
    operational_weight: 0.15

evaluation:
  dimensions:
    discovery:
      weight: 0.30
      criteria:
        - "Identified the root cause of customer request"
        - "Determined feasibility of GenAI for this domain"
        - "Uncovered hidden constraints"
    technical:
      weight: 0.20
      # ...
```

---

## Request Lifecycle

### Action Submission Flow

```
Participant                    API Server                Simulation Engine          Stakeholder Engine           Database
    │                              │                          │                           │                         │
    │  POST /session/{id}/actions  │                          │                           │                         │
    │─────────────────────────────>│                          │                           │                         │
    │                              │                          │                           │                         │
    │                              │ 1. Validate auth/session │                           │                         │
    │                              │ 2. Deserialize action    │                           │                         │
    │                              │ 3. Load current state    │                           │                         │
    │                              │                          │                           │                         │
    │                              │──validate_action()──────>│                           │                         │
    │                              │                          │                           │                         │
    │                              │   ValidationResult       │                           │                         │
    │                              │<─────────────────────────│                           │                         │
    │                              │                          │                           │                         │
    │  ─── [if invalid, return 422]───                         │                           │                         │
    │                              │                          │                           │                         │
    │                              │──execute_action()───────>│                           │                         │
    │                              │                          │                           │                         │
    │                              │  [compute pre-state hash] │                          │                         │
    │                              │                          │                           │                         │
    │                              │  ───────────────────────────────────────────── persist_event(event) ─────>│
    │                              │                          │                           │                         │
    │                              │  [compute post-state hash]                        │                         │
    │                              │                          │                           │                         │
    │                              │  Event                   │                           │                         │
    │                              │<─────────────────────────│                           │                         │
    │                              │                          │                           │                         │
    │  ─── [if action triggers stakeholder response] ────     │                           │                         │
    │                              │                          │                           │                         │
    │                              │──stakeholder_response()──────────────────────────>│                         │
    │                              │                          │                           │                         │
    │                              │  [Policy layer evaluates]│                          │                         │
    │                              │  [Language layer renders]                         │                         │
    │                              │                          │                           │                         │
    │                              │  StakeholderResponse     │                           │                         │
    │                              │<──────────────────────────────────────────────────│                         │
    │                              │                          │                           │                         │
    │                              │  [persist stakeholder event] ─────────────────────────────>               │
    │                              │                          │                           │                         │
    │  {updated_state, response}   │                          │                           │                         │
    │<─────────────────────────────│                          │                           │                         │
    │                              │                          │                           │                         │
```

### Detailed Flow Steps

1. **Authentication & Authorization**: Verify JWT, validate session ownership, check participant role
2. **Action Deserialization**: Parse JSON body into typed Pydantic action model; reject unknown action types
3. **State Loading**: Materialize current state from event stream (or load cached snapshot)
4. **Action Validation**: Check preconditions (sufficient budget, correct phase, required dependencies met)
5. **State Transition**: Apply deterministic effect function; compute new canonical state
6. **Event Persistence**: Write append-only event with pre/post state hashes; commit transaction
7. **Stakeholder Handling** (if applicable): Route to Stakeholder Engine; policy evaluation then LLM rendering
8. **Response Assembly**: Build participant-visible state projection; return to caller
9. **Cascade Evaluation** (async): If session-ending action, trigger Evaluation Engine asynchronously

### Phase Model (Case-Dependent)

Each case defines its own phase model. A typical FDE simulation has these phases:

```
DISCOVERY ──> ANALYSIS ──> RECOMMENDATION ──> DELIVERY
    │            │              │                  │
    │            │              │                  │
    ▼            ▼              ▼                  ▼
[Gather info] [Analyze data] [Formulate plan] [Deliver output]
```

Phases constrain which actions are available. Phase transitions are triggered by completing phase-specific milestones (e.g., "has submitted 3 discovery questions" → phase unlocks ANALYSIS).

---

## Trust Boundaries

The system enforces five numbered trust boundaries that define data access constraints between actors and components.

### Boundary 1: Participant ↔ Hidden State (STRONGEST)

| Property | Value |
|----------|-------|
| **Boundary** | The participant NEVER sees canonical hidden state directly |
| **Enforced by** | API layer projection, UI component isolation, response filtering |
| **Mechanism** | State is split into `canonical` (full) and `visible` (projected). Only the visible projection is serialized to participant-facing APIs. |
| **Violation risk** | An error that leaks a `hidden_state` key in API response OR a frontend bug that renders the full state object |
| **Defense** | Pydantic response models with explicit field inclusion; integration tests for every state endpoint; never serialize `CanonicalState` to participant responses |

```
┌────────────────────────┐      ┌───────────────────────────────┐
│   CanonicalState       │      │   ParticipantVisibleState     │
│                        │      │                               │
│  • correct_solution    │      │  • phase                      │
│  • risk_explosion      │  ──> │  • budget_remaining           │
│  • evaluation_criteria │ PROJ │  • available_actions          │
│  • hidden_flags[]      │      │  • stakeholder_messages[]     │
│  • internal_notes      │      │  • artifacts[]                │
│                        │      │  • system_log (filtered)      │
└────────────────────────┘      └───────────────────────────────┘
           ▲                                    ▲
           │                                    │
           │   Simulation Engine                │   API response
           │   (internal use)                   │   (to participant)
           │                                    │
     Database tables                      HTTP JSON body
```

### Boundary 2: Participant ↔ Stakeholder Dialogue

| Property | Value |
|----------|-------|
| **Boundary** | Stakeholder responses are LLM-rendered only; policy layer controls what facts can be revealed |
| **Enforced by** | Policy Engine constraint output enforced in Language Renderer system prompt |
| **Mechanism** | The Policy Engine produces a `ResponseDirective` containing allowed facts, prohibited topics, required tone, and role constraints. The Language Renderer receives this directive as part of its system prompt. |
| **Violation risk** | LLM ignores or escapes the policy constraints in its system prompt |
| **Defense** | Post-generation constraint validator checks response against policy bounds; configurable retry/regenerate on constraint violation; response rejection if constraint violation > N retries |

```
ResponseDirective {
    allowed_facts: List[str],         # Facts the stakeholder can reference
    prohibited_topics: List[str],     # Topics the stakeholder must avoid
    required_tone: str,               # "formal", "concerned", "encouraging"
    response_category: str,           # "approve", "reject", "request_info", "escalate"
    max_reveal_depth: int,            # 0=nothing new, 1=surface info, 2=moderate detail
}
```

### Boundary 3: Participant ↔ Evaluation

| Property | Value |
|----------|-------|
| **Boundary** | Evaluation scores and reports are access-controlled; participants may see scores only after session completion (and configurable embargo) |
| **Enforced by** | API permission checks, session status gate, evaluation visibility config |
| **Mechanism** | GET `/evaluation/{session_id}` returns 403 unless session is `completed` and participant has `view_evaluation` permission |
| **Violation risk** | In-progress score leakage could bias participant behavior |
| **Defense** | State-machine gating: evaluation endpoint only available in `completed` or `evaluated` session states; admin override requires explicit role |

### Boundary 4: Evaluator ↔ Participant Data

| Property | Value |
|----------|-------|
| **Boundary** | Human evaluators (expert reviewers) must have RBAC-scoped access to participant session data |
| **Enforced by** | Role-based access control on admin/evaluation endpoints |
| **Mechanism** | Evaluator role grants read access to session state, events, and artifacts for assigned sessions only |
| **Violation risk** | Evaluator accesses non-assigned session, or accesses participant PII |
| **Defense** | Session-level access control list; mandatory evaluator-session assignment table; audit logging of all evaluator data access |

### Boundary 5: LLM ↔ State

| Property | Value |
|----------|-------|
| **Boundary** | The LLM (via Model Gateway) does NOT control permissions, approvals, state transitions, or any non-language system behavior |
| **Enforced by** | Architecture: LLM only receives prompt context and returns text; all decisions are made by deterministic code |
| **Mechanism** | The Stakeholder Engine's Language Renderer receives structured context and returns a text response. It never receives function-calling capabilities, tool-use permissions, or state-modifying primitives. |
| **Violation risk** | LLM output is parsed to extract structured data that affects state (e.g., "approve" in text is interpreted as approval event) |
| **Defense** | Language Renderer output is treated as opaque text only; all structured decisions come from Policy Engine; explicit output parsing is schema-validated and constrained to pre-approved response formats |

---

## Event Model

### Principles

- **Append-only**: Events are never modified, deleted, or reordered after commit
- **Immutable**: Event payload is written once and frozen
- **Replayable**: Full state can be reconstructed by replaying the event stream from session creation
- **Verifiable**: Pre/post state hashes enable integrity checks
- **Ordered**: Events have monotonically increasing sequence numbers within a session

### Event Schema

```python
# packages/simulation-engine/models.py

class SimulationEvent(Base):
    __tablename__ = "simulation_events"

    id: UUID                   # Primary key, server-generated
    session_id: UUID           # FK to sessions
    sequence_number: int       # Monotonically increasing per session
    event_type: str            # e.g., "action.submitted", "state.transition",
                               #   "stakeholder.response", "phase.transition",
                               #   "action.validation.failed", "session.created",
                               #   "evaluation.completed"
    actor_type: str            # "participant", "system", "stakeholder", "evaluator"
    actor_id: UUID | None      # Participant ID, stakeholder ID, or null for system
    payload: JSONB             # Event-specific data (see below)
    pre_state_hash: str        # SHA-256 of canonical state before event
    post_state_hash: str       # SHA-256 of canonical state after event
    parent_event_id: UUID | None  # Links response events to triggering actions
    created_at: datetime       # Server timestamp (not participant-reported)
    checksum: str              # HMAC-SHA256 over (session_id || seq_num || payload || pre_hash || post_hash)
```

### Event Payload Examples

**Session Created:**
```json
{
    "event_type": "session.created",
    "payload": {
        "case_id": "wrong-use-case",
        "case_version": "1.0.0",
        "participant_id": "uuid-here",
        "initial_state": { "phase": "discovery", "budget_remaining": 50000 }
    }
}
```

**Action Submitted:**
```json
{
    "event_type": "action.submitted",
    "payload": {
        "action_type": "chat_message",
        "params": { "recipient": "cto", "message": "Can you tell me more about your previous AI projects?" },
        "action_id": "uuid-here"
    }
}
```

**State Transition:**
```json
{
    "event_type": "state.transition",
    "payload": {
        "action_id": "uuid-here",
        "deltas": { "budget_remaining": -5000, "stakeholder_relationships.cto": 5 },
        "phase": "discovery",
        "sequence": 4
    }
}
```

**Stakeholder Response:**
```json
{
    "event_type": "stakeholder.response",
    "payload": {
        "stakeholder_id": "cto",
        "response_text": "Yes, we tried a chatbot project last year...",
        "policy_directive_id": "uuid-here",
        "constraint_violations": [],
        "generation_metadata": {
            "provider": "openai",
            "model": "gpt-4o",
            "tokens_used": 342,
            "latency_ms": 1200
        }
    }
}
```

### State Reconstruction

```
function materialize_state(session_id: UUID) -> CanonicalState:
    events = db.query(SimulationEvent)
               .filter_by(session_id=session_id)
               .order_by(sequence_number)
               .all()

    state = load_initial_state(events[0])  # from session.created event
    for event in events[1:]:
        if event.event_type == "state.transition":
            state.apply_deltas(event.payload.deltas)
        if event.event_type == "stakeholder.response":
            state.add_stakeholder_message(...)
        # ... other event types

    return state
```

### Integrity Verification

```python
def verify_event_chain(session_id: UUID) -> IntegrityResult:
    events = get_ordered_events(session_id)
    for i, event in enumerate(events):
        # Verify pre_state_hash matches previous event's post_state_hash
        if i > 0 and event.pre_state_hash != events[i-1].post_state_hash:
            return IntegrityResult.BROKEN_CHAIN(i)

        # Verify checksum
        expected = hmac_sha256(event.session_id, event.sequence_number,
                                event.payload, event.pre_state_hash, event.post_state_hash)
        if event.checksum != expected:
            return IntegrityResult.CHECKSUM_MISMATCH(i)

    return IntegrityResult.OK
```

### Replay Service

The `ReplayService` enables:
- **Session debugging**: Step through events one at a time, inspecting state at each point
- **Evaluation reproducibility**: Re-run evaluations against frozen event streams
- **Audit**: Verify that all state changes are justified by prior events
- **Research**: Export anonymized event streams for analysis

---

## Action System

### Principles

- **Structured**: Every action has a typed schema with validated parameters
- **Deterministic**: Same action in same state always produces same effect
- **Costed**: Actions consume time and/or budget from session resources
- **Preconditioned**: Actions have preconditions that gate execution
- **Discoverable**: Available actions are exposed via machine-readable schema

### Action Definition

```python
# Example: Chat Message Action Schema
ActionSchema(
    type="chat_message",
    display_name="Send Message to Stakeholder",
    description="Send a chat message to an identified stakeholder",
    params={
        "recipient": ParamSchema(
            type="string",
            description="Stakeholder ID to send message to",
            enum=["cto", "engineering_vp", "product_manager"],
            required=True,
        ),
        "message": ParamSchema(
            type="string",
            description="Message content",
            max_length=2000,
            required=True,
        ),
    },
    costs=ActionCosts(
        time_minutes=1,
        budget_dollars=0,
    ),
    preconditions=[
        Precondition(
            description="Selected stakeholder must be available in current phase",
            check="stakeholder_is_available(state, params.recipient)",
        ),
    ],
    handler="handlers.chat_message_handler",
)
```

### Action Types (Core)

| Action Type | Description | Costs | Preconditions |
|------------|-------------|-------|---------------|
| `chat_message` | Send message to stakeholder | 1 min, $0 | Stakeholder available |
| `upload_artifact` | Upload a document/artifact | 5 min, $0 | Phase allows artifacts |
| `request_approval` | Request approval for a decision/plan | 10 min, $0 | Approval is valid option |
| `edit_configuration` | Modify system configuration | 15 min, $0 | Config access granted |
| `run_analysis` | Execute analysis (simulated) | 10 min, $0 (or $budget) | Requires data artifact |
| `submit_recommendation` | Submit final recommendation | 30 min, $0 | Phase === DELIVERY |
| `escalate` | Escalate to higher authority | 5 min, $0 | Escalation path exists |
| `request_meeting` | Request stakeholder meeting | 15 min, $0 | Stakeholder available |

### Action Registry Pattern

```python
# Action Registry (packages/simulation-engine/action_registry.py)

registry = ActionRegistry()

@registry.register("chat_message")
def handle_chat_message(state: CanonicalState, params: dict) -> StateDelta:
    # Deduct costs
    state = state.with_deltas({
        "budget_remaining": state.budget_remaining,
        "time_remaining": state.time_remaining - 1,
    })
    # Record message in state
    state = state.with_message(
        stakeholder_id=params["recipient"],
        message=params["message"],
        direction="outgoing",
    )
    return StateDelta(deltas={...}, next_phase=None)

@registry.register("request_approval")
def handle_request_approval(state: CanonicalState, params: dict) -> StateDelta:
    # Check preconditions
    if not state.approval_paths.get(params["scope"]):
        raise PreconditionFailed(f"No approval path for scope: {params['scope']}")
    # Create pending approval
    state = state.with_pending_approval(
        scope=params["scope"],
        justification=params["justification"],
    )
    return StateDelta(deltas={...}, next_phase=None)
```

### Precondition System

Preconditions are deterministic predicates evaluated against current state:

```python
@registry.precondition("chat_message", "stakeholder_available")
def stakeholder_available(state: CanonicalState, recipient: str) -> bool:
    """Stakeholder must be in the current phase's stakeholder list."""
    return recipient in state.current_phase_stakeholders

@registry.precondition("request_approval", "budget_sufficient")
def budget_sufficient(state: CanonicalState, scope: str, justification: str) -> bool:
    """Approval requests cost $0 but may require remaining budget > threshold."""
    # No budget precondition for basic approval requests
    return True
```

---

## Evaluation Model

### Six Dimensions

| Dimension | Weight (default) | Description | Sample Criteria |
|-----------|-----------------|-------------|-----------------|
| **Discovery** | 30% | Quality of information gathering | Identified root cause, uncovered hidden constraints, asked right stakeholders |
| **Technical** | 20% | Quality of technical solution | Correct architecture choice, appropriate technology selection, feasibility analysis |
| **Evaluation Quality** | 10% | Quality of self-evaluation and reflection | Considered alternatives, identified risks, evaluated trade-offs |
| **Delivery** | 25% | Quality of communication and deliverables | Clear documentation, stakeholder-appropriate language, actionable recommendations |
| **Governance** | 10% | Awareness of compliance and ethics | Security considerations, data privacy, regulatory awareness |
| **Operational Sustainability** | 5% | Long-term viability of solution | Maintainability, scalability, operational cost awareness |

### Scoring Model

```python
class EvaluationResult(BaseModel):
    session_id: UUID
    case_id: str
    participant_id: UUID

    # Dimension scores (0.0 - 1.0)
    discovery_score: float
    technical_score: float
    evaluation_quality_score: float
    delivery_score: float
    governance_score: float
    operational_sustainability_score: float

    # Overall (weighted)
    overall_score: float

    # Hard constraint violations
    hard_constraint_violations: list[ConstraintViolation]

    # Validator results
    validator_results: list[ValidatorResult]

    # Expert review (optional)
    expert_review: ExpertReview | None

    # Metadata
    completed_at: datetime
    evaluation_version: str
```

### Hard Constraints

Hard constraints are non-negotiable pass/fail criteria. Violating a critical hard constraint may result in automatic failure regardless of dimension scores.

```python
class HardConstraintType(str, Enum):
    SECURITY_LEAK = "security_leak"
    MISSING_REQUIRED_DELIVERABLE = "missing_required_deliverable"
    VIOLATED_GOVERNANCE_RULE = "violated_governance_rule"
    BUDGET_EXCEEDED = "budget_exceeded"
    TIMEOUT = "timeout"

class ConstraintViolation(BaseModel):
    constraint_type: HardConstraintType
    severity: Literal["critical", "major", "minor"]
    description: str
    evidence: list[str]  # Event IDs or artifact references
```

### Automated Validators

Validators are composable checks registered in the `ValidatorRegistry`:

- **Discovery validator**: Analyzes chat messages for question coverage against case information needs
- **Solution validator**: Checks artifacts for required solution components
- **Budget validator**: Verifies budget was not exceeded
- **Timeline validator**: Verifies completion within time constraints
- **Security validator**: Scans artifacts for credential leakage, PII exposure
- **Governance validator**: Checks for required compliance acknowledgments
- **Stakeholder validator**: Verifies all required stakeholders were engaged

### Expert Review

Human evaluators can supplement automated scoring:

```python
class ExpertReview(BaseModel):
    evaluation_id: UUID
    reviewer_id: UUID
    dimension_adjustments: dict[str, float]  # Dimension → delta (-0.2 to +0.2)
    qualitative_feedback: str
    flag_for_review: bool  # Marks evaluation for secondary review
    created_at: datetime
```

---

## Stakeholder Model

### Hybrid Architecture

Stakeholders are simulated via a two-layer architecture:

**Layer 1: Policy Engine (Deterministic)**
- Pure logic, no LLM involvement
- Evaluates participant actions against case-defined policy rules
- Determines what the stakeholder knows, thinks, and can say
- Produces a `ResponseDirective` that constrains the LLM output

**Layer 2: Language Renderer (LLM, Bounded)**
- Receives: System prompt (character persona), ResponseDirective, conversation history
- Generates: Character-appropriate natural language response
- Guarantees: No state control, no permission decisions, no information beyond policy bounds

### Response Pipeline

```
Input: Participant Message + Current State
                      │
                      ▼
┌─────────────────────────────────────────────┐
│ 1. Policy Evaluation                         │
│                                              │
│    policy_engine.evaluate(                   │
│        stakeholder_config,                   │
│        current_state,                        │
│        participant_message,                  │
│        conversation_history,                 │
│    ) → ResponseDirective                     │
│                                              │
│    Examples of policy checks:               │
│    • "Does stakeholder know this fact?"     │
│    • "Is this a valid approval request?"    │
│    • "Would stakeholder escalate here?"     │
│    • "What is the stakeholder's emotional   │
│       state based on previous interactions?" │
└─────────────────────┬───────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│ 2. Context Assembly                          │
│                                              │
│    context = {                               │
│        "character": stakeholder_persona,     │
│        "directive": response_directive,      │
│        "history": recent_conversation,       │
│        "participant_message": message,       │
│        "case_context": visible_case_info,    │
│    }                                         │
└─────────────────────┬───────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│ 3. LLM Generation                            │
│                                              │
│    response = model_gateway.generate(        │
│        system_prompt=build_system_prompt(    │
│            character=stakeholder_persona,    │
│            directive=response_directive,     │
│        ),                                    │
│        messages=[{role: "user", content:     │
│            format_context(context)}],        │
│        config=ModelConfig(                   │
│            temperature=0.3,  # low for       │
│                             # consistency    │
│            max_tokens=500,                   │
│        ),                                    │
│    )                                         │
└─────────────────────┬───────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│ 4. Post-Generation Validation                │
│                                              │
│    violations = constraint_validator.check(  │
│        response=response.text,               │
│        directive=response_directive,         │
│    )                                         │
│                                              │
│    if violations:                            │
│        if retry_count < MAX_RETRIES:         │
│            goto step 3 with enhanced prompt  │
│        else:                                 │
│            return fallback_response          │
│                                              │
│    return StakeholderResponse(               │
│        text=response.text,                   │
│        policy_directive_id=directive.id,     │
│        constraint_violations=violations,     │
│        generation_metadata=metadata,         │
│    )                                         │
└─────────────────────────────────────────────┘
```

### Policy Rule Examples

```yaml
# policies/cto.policy.yaml
policies:
  - trigger: "participant_asks_about_budget"
    condition: "phase == 'discovery'"
    action: "reveal_budget_constraint"
    constraints:
      allowed_facts:
        - "budget_upper_bound"    # Can reveal $50k max
        - "previous_project_failure"  # Can reference past failure
      prohibited_topics:
        - "actual_spend_last_project"  # Cannot reveal exact figures
      response_category: "request_info"
      tone: "concerned_but_open"

  - trigger: "participant_proposes_ai_solution"
    condition: "true"
    action: "evaluate_proposed_solution"
    response_category: "escalate_or_question"
    constraints:
      allowed_facts:
        - "domain_feasibility_concerns"
      prohibited_topics:
        - "hidden_evaluation_criteria"
      max_reveal_depth: 1
      tone: "skeptical"
```

### Stakeholder State

Stakeholders have persistent state that evolves during the simulation:

```python
class StakeholderState(BaseModel):
    stakeholder_id: str
    trust_score: float  # 0-100, affected by participant interactions
    knowledge_graph: dict[str, bool]  # Fact ID → known/unknown
    emotional_state: str  # "neutral", "frustrated", "encouraged", "skeptical"
    revealed_facts: list[str]  # Facts already disclosed in conversation
    pending_actions: list[dict]  # Approvals requested, awaiting response
```

---

## Seed Cases

### Case 1: The Wrong Use Case (`cases/wrong-use-case/`)

**Scenario:** A mid-market retailer approaches the participant (FDE) to implement a GenAI customer service chatbot. The participant must discover that the client's actual problem — returns processing and inventory lookup — is better solved with a deterministic rules engine, not GenAI.

**Hidden State:** The GenAI approach would cost $200k+ and fail due to hallucination risk on structured inventory data. The correct solution is a rule-based recommendation engine.

**Learning Objectives:**
- Identify when GenAI is the wrong tool
- Resist solution-selling pressure from the client
- Deliver a compelling non-AI recommendation

### Case 2: Unsafe Autonomy Transition (`cases/unsafe-autonomy/`)

**Scenario:** A client wants to transition an internal ML prototype to full autonomous production without proper testing, monitoring, or rollback procedures. The participant must navigate governance concerns while maintaining client trust.

**Hidden State:** The prototype has undocumented data drift patterns and uses a non-representative training set. A direct production deployment would cause cascading failures in 2-3 weeks.

**Learning Objectives:**
- Identify production readiness gaps
- Negotiate governance requirements without losing client buy-in
- Design safe deployment strategies (shadow mode, canary, blue-green)

### Case 3: The Unmaintainable Prototype (`cases/unmaintainable-prototype/`)

**Scenario:** A client's data science team built a GenAI prototype that works in demo but is a maintenance nightmare — no tests, hardcoded credentials, no CI/CD, undocumented dependencies. The participant must assess and remediate.

**Hidden State:** The prototype has 12 known CVEs in pinned dependencies, has hardcoded API keys in three files, and depends on a deprecated model version.

**Learning Objectives:**
- Conduct production readiness assessment
- Prioritize remediation with limited budget
- Communicate technical debt to non-technical stakeholders

---

## Case Authoring Toolkit

### CLI Commands

```bash
# Scaffold a new case
afcs case create my-new-case \
    --title "My New Case" \
    --difficulty advanced \
    --estimated-minutes 60

# Validate a case definition
afcs case validate cases/my-new-case/case.yaml

# Run reachability analysis
afcs case reachability cases/my-new-case/case.yaml

# Test a case interactively
afcs case test cases/my-new-case/case.yaml

# List all available cases
afcs case list

# Export case to JSON schema
afcs case export cases/my-new-case/case.yaml --format json

# Generate case documentation
afcs case docs cases/my-new-case/case.yaml --output docs/cases/
```

### Reachability Checks

The `reachability` command performs automated analysis:

1. **State Reachability**: For every defined state/phase, verify there is at least one sequence of actions that reaches it
2. **Goal Reachability**: For each defined goal, verify there is at least one action path that achieves it
3. **Stakeholder Access**: Verify all stakeholders can be engaged within the simulation flow
4. **Constraint Satisfaction**: Verify that all constraints are satisfiable (not mutually contradictory)
5. **Completion Validation**: Verify that at least one completion path exists (case is solvable)
6. **Deadlock Detection**: Detect states from which no valid action exists and no goal has been achieved
7. **Budget Feasibility**: Verify that total required costs for any completion path fit within the budget

### Case Directory Structure

```
cases/wrong-use-case/
├── case.yaml                     # Main case definition (required)
├── policies/
│   ├── cto.policy.yaml           # Stakeholder policy rules
│   ├── engineering_vp.policy.yaml
│   └── product_manager.policy.yaml
├── contexts/
│   ├── briefing.md               # Participant briefing document
│   ├── company_overview.md       # Client company background
│   └── technical_context.md      # Optional technical background
├── evaluation/
│   ├── validators.py             # Custom validators (Python)
│   └── criteria.yaml             # Dimension weights and criteria
├── assets/
│   ├── org_chart.png             # Optional visual assets
│   └── sample_data.csv           # Optional sample datasets
└── tests/
    ├── test_reachability.py      # Reachability test specs
    └── test_validators.py        # Validator unit tests
```

---

## API Design

### RESTful Agent API

The API is designed for both human browser consumption and programmatic AI agent access.

**Base URL:** `/api/v1`

**Authentication:** Bearer token in `Authorization` header.

**Content-Type:** `application/json`

### Endpoints (Detailed)

#### Sessions

```
POST /api/v1/sessions
    Body: { "case_id": "wrong-use-case", "participant_id": "uuid" }
    Response: { "session_id": "uuid", "case_title": "...", "initial_state": {...} }

GET /api/v1/sessions/{session_id}
    Response: { "session_id": "uuid", "case": {...}, "state": {...}, "status": "in_progress" }
```

#### Actions

```
GET /api/v1/sessions/{session_id}/actions/schema
    Response: {
        "actions": [
            {
                "type": "chat_message",
                "display_name": "Send Message to Stakeholder",
                "params": {
                    "recipient": { "type": "string", "enum": ["cto", "vp_eng"], "required": true },
                    "message": { "type": "string", "max_length": 2000, "required": true }
                }
            },
            ...
        ]
    }

POST /api/v1/sessions/{session_id}/actions
    Body: {
        "action_type": "chat_message",
        "params": { "recipient": "cto", "message": "..." }
    }
    Response: {
        "event_id": "uuid",
        "sequence_number": 12,
        "new_state": { "phase": "discovery", "budget_remaining": 45000, ... },
        "stakeholder_responses": [
            {
                "stakeholder_id": "cto",
                "response_text": "Ah, good question. Let me tell you...",
                "response_type": "text"
            }
        ]
    }
```

#### Events

```
GET /api/v1/sessions/{session_id}/events
    Query: ?from_sequence=0&limit=50
    Response: {
        "events": [
            {
                "id": "uuid",
                "sequence_number": 0,
                "event_type": "session.created",
                "actor_type": "system",
                "created_at": "2025-01-01T00:00:00Z",
                "payload": { ... }
            },
            ...
        ]
    }
```

#### Evaluations

```
GET /api/v1/sessions/{session_id}/evaluation
    Response: {
        "session_id": "uuid",
        "status": "completed",  # Only available in completed/evaluated state
        "overall_score": 0.78,
        "dimensions": {
            "discovery": { "score": 0.85, "criteria": [...] },
            "technical": { "score": 0.72, "criteria": [...] },
            ...
        },
        "hard_constraint_violations": [...],
        "artifact_url": "/api/v1/sessions/{session_id}/report"
    }
```

#### Machine-Readable Action Schema (Agent API)

For AI agent consumption, action schemas are provided with full type metadata:

```json
{
    "actions": [
        {
            "type": "chat_message",
            "params": {
                "type": "object",
                "properties": {
                    "recipient": {
                        "type": "string",
                        "enum": ["cto", "engineering_vp", "product_manager"],
                        "description": "Target stakeholder ID"
                    },
                    "message": {
                        "type": "string",
                        "maxLength": 2000,
                        "minLength": 1,
                        "description": "Message content to send"
                    }
                },
                "required": ["recipient", "message"],
                "additionalProperties": false
            },
            "costs": {
                "time_minutes": 1,
                "budget_dollars": 0
            },
            "state_constraints": {
                "phase": ["discovery", "analysis", "recommendation", "delivery"],
                "remaining_budget_min": 0
            }
        }
    ]
}
```

### Error Responses

```json
{
    "error": {
        "code": "ACTION_VALIDATION_FAILED",
        "message": "Action preconditions were not met",
        "details": {
            "failed_preconditions": [
                {
                    "name": "stakeholder_available",
                    "message": "Stakeholder 'cto' is not available in current phase 'delivery'"
                }
            ]
        },
        "request_id": "uuid"
    }
}
```

---

## Data Model

### Entity-Relationship Diagram

```
┌────────────────┐       ┌──────────────────┐       ┌──────────────────────┐
│    Case        │       │    Session        │       │ SimulationEvent      │
├────────────────┤       ├──────────────────┤       ├──────────────────────┤
│ id (PK)        │──1:N──│ id (PK)          │──1:N──│ id (PK)              │
│ case_id (uniq) │       │ case_id (FK)     │       │ session_id (FK)      │
│ title          │       │ participant_id   │       │ sequence_number      │
│ version        │       │ status           │       │ event_type           │
│ description    │       │ current_phase    │       │ actor_type           │
│ difficulty     │       │ created_at       │       │ actor_id             │
│ estimated_min  │       │ completed_at     │       │ payload (JSONB)      │
│ schema (JSONB) │       │ state_hash       │       │ pre_state_hash       │
│ created_at     │       │ metadata (JSONB) │       │ post_state_hash      │
│ updated_at     │       │                  │       │ parent_event_id      │
└────────────────┘       └──────────────────┘       │ checksum             │
        │                                            │ created_at           │
        │                                            └──────────────────────┘
        │                                                    │
        │                                                    │
        │      ┌─────────────────────┐                       │
        │      │   Participant       │                       │
        │      ├─────────────────────┤                       │
        │      │ id (PK)             │                       │
        │      │ email               │                       │
        │      │ display_name        │                       │
        │      │ role (enum)         │                       │
        │      │ created_at          │                       │
        │      └─────────────────────┘                       │
        │              │                                     │
        │              │ 1:N                                 │
        │              ▼                                     │
        │      ┌─────────────────────┐                       │
        │      │   SessionParticipant│                       │
        │      ├─────────────────────┤                       │
        │      │ session_id (FK)     │                       │
        │      │ participant_id (FK) │                       │
        │      │ role (enum)         │                       │
        │      │ joined_at           │                       │
        │      └─────────────────────┘                       │
        │                                                    │
        │      ┌─────────────────────┐       ┌──────────────────────┐
        │      │   Evaluation        │       │   Artifact           │
        │      ├─────────────────────┤       ├──────────────────────┤
        │      │ id (PK)             │──1:N──│ id (PK)              │
        │      │ session_id (FK)     │       │ session_id (FK)      │
        │      │ evaluator_id (FK)   │       │ event_id (FK)        │
        │      │ overall_score       │       │ filename             │
        │      │ scores (JSONB)      │       │ content_type         │
        │      │ hard_constraints    │       │ content_hash         │
        │      │   (JSONB)           │       │ storage_path         │
        │      │ expert_review(JSONB)│       │ created_at           │
        │      │ completed_at        │       └──────────────────────┘
        │      │ evaluation_version  │
        │      └─────────────────────┘
        │              │
        │              │ 1:1
        │              ▼
        │      ┌─────────────────────┐
        │      │   Report            │
        │      ├─────────────────────┤
        │      │ id (PK)             │
        │      │ evaluation_id (FK)  │
        │      │ content (JSONB)     │
        │      │ format (enum)       │
        │      │ generated_at        │
        │      └─────────────────────┘
        │
        │      ┌─────────────────────┐
        │      │   Stakeholder       │
        │      ├─────────────────────┤
        │      │ id (PK)             │
        │      │ case_id (FK)        │
        │      │ stakeholder_id      │
        │      │ name                │
        │      │ role                │
        │      │ persona (JSONB)     │
        │      │ policy_config(JSONB)│
        │      └─────────────────────┘
                        │
                        │ 1:N
                        ▼
        ┌──────────────────────────┐
        │   StakeholderState       │
        ├──────────────────────────┤
        │ id (PK)                  │
        │ session_id (FK)          │
        │ stakeholder_id (FK)      │
        │ trust_score              │
        │ knowledge (JSONB)        │
        │ emotional_state          │
        │ revealed_facts (JSONB)   │
        │ updated_at               │
        └──────────────────────────┘
```

### Core Entity Definitions

```python
# packages/domain/models.py

class Case(Base):
    __tablename__ = "cases"
    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, server_default=func.gen_random_uuid())
    case_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(32), nullable=False)  # beginner, intermediate, advanced
    estimated_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    schema: Mapped[dict] = mapped_column(JSONB, nullable=False)  # Full case definition
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, server_default=func.gen_random_uuid())
    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id"), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="in_progress"
    )  # in_progress, completed, evaluated, archived
    current_phase: Mapped[str] = mapped_column(String(64), nullable=False)
    state_hash: Mapped[str] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

class SimulationEvent(Base):
    __tablename__ = "simulation_events"
    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, server_default=func.gen_random_uuid())
    session_id: Mapped[UUID] = mapped_column(ForeignKey("sessions.id"), nullable=False, index=True)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_id: Mapped[Optional[UUID]] = mapped_column(UUID, nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    pre_state_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    post_state_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    parent_event_id: Mapped[Optional[UUID]] = mapped_column(UUID, nullable=True)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    __table_args__ = (
        UniqueConstraint("session_id", "sequence_number", name="uq_event_sequence"),
    )

class Participant(Base):
    __tablename__ = "participants"
    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, server_default=func.gen_random_uuid())
    email: Mapped[str] = mapped_column(String(256), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(
        String(32), nullable=False, default="participant"
    )  # participant, evaluator, admin
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class Evaluation(Base):
    __tablename__ = "evaluations"
    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, server_default=func.gen_random_uuid())
    session_id: Mapped[UUID] = mapped_column(ForeignKey("sessions.id"), nullable=False, unique=True)
    evaluator_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("participants.id"), nullable=True)
    overall_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    scores: Mapped[dict] = mapped_column(JSONB, nullable=True)  # Dimension scores
    hard_constraints: Mapped[list] = mapped_column(JSONB, nullable=True)
    expert_review: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    evaluation_version: Mapped[str] = mapped_column(String(32), nullable=False)

class Artifact(Base):
    __tablename__ = "artifacts"
    id: Mapped[UUID] = mapped_column(UUID, primary_key=True, server_default=func.gen_random_uuid())
    session_id: Mapped[UUID] = mapped_column(ForeignKey("sessions.id"), nullable=False, index=True)
    event_id: Mapped[UUID] = mapped_column(ForeignKey("simulation_events.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(256), nullable=False)
    content_type: Mapped[str] = mapped_column(String(64), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

---

## Deployment Topology

### Local Development

```
┌─────────────────────────────────────────────────────┐
│                   docker-compose.yml                  │
│                                                       │
│  ┌──────────────┐   ┌──────────────┐                 │
│  │   Frontend    │   │    API       │                 │
│  │   :5173       │──>│   :8000      │                 │
│  │   (Vite Dev)  │   │  (FastAPI)   │                 │
│  └──────────────┘   └──────┬───────┘                 │
│                            │                          │
│                            ▼                          │
│                     ┌──────────────┐                  │
│                     │  PostgreSQL   │                  │
│                     │   :5432      │                  │
│                     └──────────────┘                  │
│                                                       │
│  • Hot-reload for frontend and backend                │
│  • Volumes for PostgreSQL data persistence            │
│  • Environment variables via .env file                │
│  • Seed data loaded on first startup                  │
│  • API docs at http://localhost:8000/docs             │
│  • Frontend at http://localhost:5173                  │
└─────────────────────────────────────────────────────┘
```

### Production Considerations

| Concern | Solution |
|---------|----------|
| **Database** | Managed PostgreSQL (RDS/Cloud SQL), read replicas for evaluation queries |
| **API Scaling** | Horizontal scaling behind ALB/nginx, stateless API servers |
| **Frontend Serving** | Static build served via CDN (CloudFront/Cloudflare) or nginx sidecar |
| **LLM Provider Failover** | Circuit breaker in Model Gateway, automatic failover between OpenAI/Anthropic |
| **Secrets Management** | Vault or cloud-native secrets manager (AWS Secrets Manager, GCP Secret Manager) |
| **Observability** | Structured JSON logging, OpenTelemetry tracing, metrics (Datadog/Grafana) |
| **Rate Limiting** | Nginx rate limiting + API-level rate limiting per participant |
| **Backup** | Daily PostgreSQL snapshots, WAL archiving for point-in-time recovery |
| **CI/CD** | GitHub Actions: lint → test → build → dockerize → deploy |
| **Environment Parity** | Docker Compose for dev, K8s manifests for staging/prod |

### Docker Compose Configuration

```yaml
# docker/compose.yaml (dev)
version: "3.8"
services:
  api:
    build:
      context: ..
      dockerfile: apps/api/Dockerfile.dev
    ports: ["8000:8000"]
    environment:
      - DATABASE_URL=postgresql+asyncpg://afcs:afcs@db:5432/afcs
      - LOG_LEVEL=debug
    volumes:
      - ../apps/api:/app/apps/api
      - ../packages:/app/packages
    depends_on: [db]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 10s

  web:
    build:
      context: ..
      dockerfile: apps/web/Dockerfile.dev
    ports: ["5173:5173"]
    environment:
      - VITE_API_URL=http://localhost:8000/api/v1
    volumes:
      - ../apps/web:/app/apps/web
      - ../packages/ui:/app/packages/ui

  db:
    image: postgres:16-alpine
    environment:
      - POSTGRES_USER=afcs
      - POSTGRES_PASSWORD=afcs
      - POSTGRES_DB=afcs
    ports: ["5432:5432"]
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ../docker/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U afcs"]
      interval: 5s

volumes:
  pgdata:
```

---

## Risks, Trade-offs, Open Questions

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **LLM hallucination reveals hidden state** | Medium | Critical | Policy-layer constraint enforcement + post-generation validation; LLM never receives hidden state in prompt |
| **Event chain integrity failure** | Low | High | HMAC checksums per event; pre/post state hash chain; automated integrity verification on replay |
| **Side-channel leakage via timing** | Low | Medium | Constant-time response patterns; no state-dependent query timing differences |
| **Participant action DoS via rapid requests** | Medium | Low | Rate limiting per session; action cost model disincentivizes spam |
| **Case schema incompleteness leads to stuck sessions** | Medium | High | Reachability analysis in CI; deadlock detection; admin override for session rescue |
| **Provider API outage blocks stakeholder responses** | Medium | High | Circuit breaker + automatic failover; fallback canned responses; queue for retry |
| **RBAC configuration error** | Low | High | Mandatory test suite for RBAC rules; integration tests for every role/permission combination |

### Trade-offs

| Decision | Rationale | Downside |
|----------|-----------|----------|
| **Append-only events vs. mutable state** | Full auditability, replay, debugging | Higher storage cost; slower state reads for long sessions |
| **Two-layer stakeholder (policy + LLM) vs. single LLM** | Guaranteed correctness boundaries; no LLM control over system state | Higher latency; more complex code; two potential failure modes |
| **State reconstruction vs. snapshot cache** | Source of truth is always the event stream | Cold-start sessions need full replay; mitigated by periodic snapshots |
| **Pydantic v2 everywhere** | Type-safe across all layers; FastAPI-native | Slight overhead vs. raw dicts on hot paths |
| **JSONB for event payloads vs. normalized tables** | Schema flexibility for evolving event types | No referential integrity inside JSONB; mitigated by Pydantic validation on read |
| **Monorepo vs. multi-repo** | Atomic cross-package changes; shared CI | Monorepo tooling complexity; longer CI pipelines |

### Open Questions

| Question | Status | Notes |
|----------|--------|-------|
| Should session replay be available to participants for self-review? | TBD | Educational value vs. gaming risk |
| What is the artifact storage backend? (S3/GCS/local FS) | TBD | Local FS for dev; S3/GCS for prod |
| Should evaluations be real-time (progressive scoring) or batch (end of session)? | TBD | Progressive enables adaptive hints, but risks biasing participant |
| How should multi-participant sessions work (team mode)? | Future | Out of scope for MVP; session designed for single participant |
| What LLM providers beyond OpenAI/Anthropic? | TBD | Ollama for local dev; Azure OpenAI for enterprise |
| Should cases have version migration support? | TBD | Version pinning in session creation prevents drift |
| What is the data retention policy? | TBD | GDPR considerations; anonymization for research datasets |
| Should there be a participant time limit with auto-submit? | TBD | MVP uses honor system; auto-submit at 2x estimated time |

---

## Appendix: Key Architectural Decisions (ADRs)

### ADR-001: Append-Only Event Store

**Status:** Accepted
**Context:** Need for full auditability, replay, and integrity verification.
**Decision:** All state changes are recorded as immutable append-only events. State is reconstructed by replaying the event stream. Periodic state snapshots are cached for performance.
**Consequences:** Higher storage overhead; full audit trail; replay capability for evaluation and debugging.

### ADR-002: Two-Layer Stakeholder Simulation

**Status:** Accepted
**Context:** LLM-based dialogue must not control system state or leak hidden information.
**Decision:** Stakeholder responses are generated by a deterministic policy layer followed by an LLM language renderer. The policy layer determines what facts can be revealed, what response category applies, and what constraints bind the LLM output. The LLM renders character-appropriate natural language within those constraints.
**Consequences:** More complex architecture; guaranteed fact boundaries; no LLM escape to state control.

### ADR-003: State Hash Chain

**Status:** Accepted
**Context:** Need to detect event tampering and verify state reconstruction integrity.
**Decision:** Each event stores SHA-256 pre-state-hash and post-state-hash. Events also carry an HMAC-SHA256 checksum over (session_id || sequence_number || payload || pre_hash || post_hash).
**Consequences:** Integrity verification is always possible; minor storage overhead (two 64-char hashes + one 64-char HMAC per event); verification is O(n) on replay.

### ADR-004: Pydantic v2 for All Contracts

**Status:** Accepted
**Context:** Multiple packages need to share type definitions and validation.
**Decision:** All API contracts, event schemas, case definitions, and configuration objects use Pydantic v2 models. Shared types live in `packages/shared-types/`.
**Consequences:** Type safety across Python layers; serialization/deserialization is automatic; schema generation for OpenAPI docs.

---

*Document version: 1.0.0 — Phase 0a Architecture Specification*
*Last updated: 2025-01-01*
