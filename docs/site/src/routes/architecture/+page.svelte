<svelte:head>
  <title>Architecture — AFCS</title>
</svelte:head>

<h1>System Architecture</h1>

<p class="section-sub">
  The AFCS architecture enforces a strict separation between hidden canonical state and participant-visible projections, using deterministic state transitions driven by structured participant actions.
</p>

<section>
  <h2>Component Architecture</h2>
  <pre><code>┌─────────────────────────────────────────────────────────────────────┐
│                         Participant Layer                           │
│                                                                     │
│  ┌──────────────────────┐         ┌──────────────────────────┐      │
│  │   Web UI (Browser)   │         │   AI Agent (API Client)  │      │
│  │  React + TypeScript  │         │   REST / JSON over HTTP  │      │
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
│  │ • State Machine  │  │ • Policy Layer   │  │ • Validators     │  │
│  │ • Action Registry│  │ • Language Render│  │ • Hard Constraint│  │
│  │ • Event Model    │  │ • Fact Bounds    │  │ • Scoring Engine │  │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘  │
│           │                     │                      │           │
│  ┌──────────────────┐  ┌──────────────────┐            │           │
│  │ Model Gateway    │  │ Case Repository  │            │           │
│  │ • Provider-Agnos.│  │ • Case Schema    │            │           │
│  │ • Mock Provider  │  │ • Validation     │            │           │
│  └──────────────────┘  └──────────────────┘            │           │
└────────────────────────┬───────────────────────────────┼───────────┘
                         │                               │
                         ▼                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Data Layer                                   │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                   PostgreSQL Database                         │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────┐   │   │
│  │  │  Cases   │ │ Sessions │ │ Events   │ │ Participants   │   │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └────────────────┘   │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐                     │   │
│  │  │ Evalua-  │ │ Reports  │ │ Stake-   │                     │   │
│  │  │ tions    │ │          │ │ holders  │                     │   │
│  │  └──────────┘ └──────────┘ └──────────┘                     │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘</code></pre>
</section>

<section>
  <h2>Trust Boundaries</h2>
  <p>The system enforces five numbered trust boundaries that define data access constraints.</p>

  <table>
    <thead>
      <tr><th>#</th><th>Boundary</th><th>Mechanism</th><th>Risk</th></tr>
    </thead>
    <tbody>
      <tr>
        <td>B1</td>
        <td>Participant ↔ Hidden State</td>
        <td>CanonicalState → VisibleState projection. Only projected state reaches API.</td>
        <td>Leaking hidden state keys in API response</td>
      </tr>
      <tr>
        <td>B2</td>
        <td>Participant ↔ Stakeholder</td>
        <td>Policy layer controls facts. Post-generation constraint validation.</td>
        <td>LLM ignores policy constraints</td>
      </tr>
      <tr>
        <td>B3</td>
        <td>Participant ↔ Evaluation</td>
        <td>Score endpoint returns 403 until session is completed/evaluated.</td>
        <td>In-progress score leakage biases behavior</td>
      </tr>
      <tr>
        <td>B4</td>
        <td>Evaluator ↔ Participant Data</td>
        <td>RBAC + session-level ACL. Audit logging of all evaluator access.</td>
        <td>Cross-session or unauthorized PII access</td>
      </tr>
      <tr>
        <td>B5</td>
        <td>Agent ↔ Environment</td>
        <td>Bounded synthetic tools. No unrestricted shells, no arbitrary credentials.</td>
        <td>Agent escaping simulation sandbox</td>
      </tr>
    </tbody>
  </table>
</section>

<section>
  <h2>Stakeholder Engine</h2>
  <p>The hybrid architecture is the core innovation: deterministic policy controls facts, permissions, and approvals. The LLM only renders language.</p>

  <pre><code>Participant Action
       │
       ▼
┌─────────────────────────────┐
│   Policy Engine             │
│   (Deterministic - pure)    │
│                             │
│  • Rule matching            │
│  • Fact availability check  │
│  • Response classification  │     ← LLM has NO control here
│  • Constraint generation    │
└──────────┬──────────────────┘
           │  ResponseDirective
           ▼
┌─────────────────────────────┐
│   Language Renderer         │
│   (LLM - bounded)           │
│                             │
│  • System prompt + policy   │
│  • Persona-aware tone       │
│  • Response generation      │
│  • Post-generation validate │     ← disclosed ⊆ allowed
└──────────┬──────────────────┘
           │
           ▼
    Stakeholder Response</code></pre>
</section>

<section>
  <h2>Event Model</h2>
  <p>Every state change flows through the append-only <code>simulation_events</code> table. State is materialized separately for efficient reads. Replay is trivial: replay events in sequence order.</p>

  <pre><code>simulation_events (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL,
    sequence_number BIGINT NOT NULL,
    event_type TEXT NOT NULL,
    actor_type TEXT NOT NULL,      -- 'participant', 'system', 'stakeholder'
    actor_id TEXT,
    payload JSONB NOT NULL,
    pre_state_hash TEXT NOT NULL,   -- SHA-256 of state before action
    post_state_hash TEXT NOT NULL,  -- SHA-256 of state after action
    created_at TIMESTAMPTZ NOT NULL,
    UNIQUE(session_id, sequence_number)
)</code></pre>
</section>

<section>
  <h2>Evaluation Model</h2>
  <p>Six independent dimensions, each scored 0.0-1.0. No single number claims to represent complete FDE capability.</p>

  <table>
    <thead>
      <tr><th>Dimension</th><th>Weight</th><th>What it Measures</th></tr>
    </thead>
    <tbody>
      <tr><td>Discovery</td><td>30%</td><td>Quality of information gathering, root cause identification</td></tr>
      <tr><td>Technical Reasoning</td><td>20%</td><td>Architecture choice, feasibility analysis, constraint awareness</td></tr>
      <tr><td>Evaluation Quality</td><td>10%</td><td>Self-evaluation, alternative consideration, risk identification</td></tr>
      <tr><td>Delivery</td><td>25%</td><td>Communication clarity, actionable recommendations</td></tr>
      <tr><td>Governance</td><td>10%</td><td>Security, compliance, regulatory awareness</td></tr>
      <tr><td>Operational Sustainability</td><td>5%</td><td>Maintainability, scalability, ownership, cost awareness</td></tr>
    </tbody>
  </table>
</section>

<section>
  <h2>Technology Stack</h2>
  <table>
    <thead><tr><th>Layer</th><th>Technology</th></tr></thead>
    <tbody>
      <tr><td>Frontend</td><td>React + TypeScript + Vite + TanStack Query</td></tr>
      <tr><td>Backend API</td><td>Python 3.12 + FastAPI + Pydantic v2</td></tr>
      <tr><td>Database</td><td>PostgreSQL + SQLAlchemy 2.0 + Alembic</td></tr>
      <tr><td>Domain Logic</td><td>Pure Pydantic v2 models (zero framework deps)</td></tr>
      <tr><td>Simulation Engine</td><td>Deterministic pure functions + append-only event stream</td></tr>
      <tr><td>Stakeholder Engine</td><td>Hybrid: policy (deterministic) + LLM (language only)</td></tr>
      <tr><td>Model Gateway</td><td>Provider-agnostic Protocol + mock provider for dev</td></tr>
      <tr><td>CI/CD</td><td>GitHub Actions: ruff + pytest + Docker Compose</td></tr>
    </tbody>
  </table>
</section>

<style>
  h1 { margin-bottom: 0.5rem; }
  .section-sub { color: #94a3b8; margin-bottom: 2rem; }
  section { margin-bottom: 3rem; }
  section h2 {
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #1e293b;
    margin-bottom: 1rem;
  }
  section p { margin-bottom: 0.75rem; }
</style>
