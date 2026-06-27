<svelte:head>
  <title>Build Phases — AFCS</title>
</svelte:head>

<h1>Build Phases</h1>
<p class="section-sub">The MVP was built in 8 phases over 20 PRs, with 350 tests and zero lint errors throughout.</p>

<div class="timeline">
  <div class="phase">
    <div class="phase-marker">1</div>
    <div class="phase-content">
      <h3>Domain Foundation</h3>
      <div class="phase-meta">153 tests · PR #10</div>
      <p>CaseSchema (19 Pydantic v2 models), domain entities (Session, Event, State, Artifacts), StateTransitionEngine with 27 action handlers, deterministic replay, case validator CLI (5 commands).</p>
      <div class="phase-artifacts">
        <code>packages/case-schema/</code><code>packages/domain/</code><code>packages/simulation-engine/</code><code>apps/api/cli.py</code>
      </div>
    </div>
  </div>

  <div class="phase">
    <div class="phase-marker">2</div>
    <div class="phase-content">
      <h3>Participant Flow</h3>
      <div class="phase-meta">175 tests · PR #11</div>
      <p>FastAPI application, SQLAlchemy 2.0 ORM (3 models), Alembic migrations, session/action/event/artifact endpoints, React + Vite + TanStack Query workspace with 3-pane layout.</p>
      <div class="phase-artifacts">
        <code>apps/api/</code><code>apps/web/</code><code>tests/integration/</code>
      </div>
    </div>
  </div>

  <div class="phase">
    <div class="phase-marker">3</div>
    <div class="phase-content">
      <h3>Stakeholders</h3>
      <div class="phase-meta">223 tests · PR #12</div>
      <p>Hybrid stakeholder engine: PolicyEngine (6 rule types) + LanguageRenderer with post-generation validation. ModelGateway with provider-neutral Protocol + MockProvider.</p>
      <div class="phase-artifacts">
        <code>packages/stakeholder-engine/</code><code>packages/model-gateway/</code>
      </div>
    </div>
  </div>

  <div class="phase">
    <div class="phase-marker">4</div>
    <div class="phase-content">
      <h3>Evaluation</h3>
      <div class="phase-meta">300 tests · PR #13</div>
      <p>12 automated validators, 6 hard constraints (3 critical, 1 major, 2 minor), 6-dimension scoring, auto-triggered report generation on session completion.</p>
      <div class="phase-artifacts">
        <code>packages/evaluation-engine/</code><code>routes/evaluations.py</code>
      </div>
    </div>
  </div>

  <div class="phase">
    <div class="phase-marker">5</div>
    <div class="phase-content">
      <h3>Seed Cases</h3>
      <div class="phase-meta">327 tests · PR #14</div>
      <p>3 complete cases: Wrong Use-Case Selection, Unsafe Autonomy Transition, Unmaintainable Prototype. All hidden facts reachable. 2+ valid strategy patterns per case.</p>
      <div class="phase-artifacts">
        <code>cases/wrong-use-case/</code><code>cases/unsafe-autonomy/</code><code>cases/unmaintainable-prototype/</code>
      </div>
    </div>
  </div>

  <div class="phase">
    <div class="phase-marker">6</div>
    <div class="phase-content">
      <h3>Replay & Expert Review</h3>
      <div class="phase-meta">PR #15</div>
      <p>ReplayService with state diff computation and dimension tagging. Expert review panel with dimension scoring and event citations. Pairwise trajectory comparison.</p>
      <div class="phase-artifacts">
        <code>ReplayTimeline.tsx</code><code>ExpertReviewPanel.tsx</code><code>routes/replay.py</code>
      </div>
    </div>
  </div>

  <div class="phase">
    <div class="phase-marker">7</div>
    <div class="phase-content">
      <h3>Agent Interface</h3>
      <div class="phase-meta">335 tests · PR #16</div>
      <p>Dedicated agent API endpoints with machine-readable action schemas. Reference baseline agent script using heuristic policy. Agent-friendly error handling.</p>
      <div class="phase-artifacts">
        <code>routes/agent.py</code><code>scripts/baseline_agent.py</code>
      </div>
    </div>
  </div>

  <div class="phase">
    <div class="phase-marker">8</div>
    <div class="phase-content">
      <h3>Hardening</h3>
      <div class="phase-meta">350 tests · PR #17</div>
      <p>GitHub Actions CI pipeline, Docker Compose, RBAC middleware, slowapi rate limiting, 15 adversarial tests (prompt injection, state extraction, event tampering, cross-session access).</p>
      <div class="phase-artifacts">
        <code>.github/workflows/ci.yml</code><code>docker-compose.yml</code><code>tests/adversarial/</code>
      </div>
    </div>
  </div>
</div>

<section style="text-align:center; padding:3rem 0;">
  <h2>Engineering Principles</h2>
  <div class="principles">
    <div class="principle">Domain logic before infrastructure</div>
    <div class="principle">Deterministic truth, generative language</div>
    <div class="principle">Structured actions before unrestricted chat</div>
    <div class="principle">Evidence-linked evaluation</div>
    <div class="principle">Multiple valid strategies per case</div>
    <div class="principle">Append-only traceability</div>
    <div class="principle">No single score as complete FDE ability</div>
  </div>
</section>

<style>
  h1 { margin-bottom: 0.5rem; }
  .section-sub { color: #94a3b8; margin-bottom: 2rem; }

  .timeline { position: relative; padding-left: 2.5rem; }
  .timeline::before {
    content: "";
    position: absolute;
    left: 1.25rem;
    top: 0;
    bottom: 0;
    width: 2px;
    background: #1e293b;
  }
  .phase {
    position: relative;
    margin-bottom: 2rem;
  }
  .phase-marker {
    position: absolute;
    left: -2.5rem;
    width: 2.5rem;
    height: 2.5rem;
    border-radius: 50%;
    background: linear-gradient(135deg, #22d3ee, #0891b2);
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: "JetBrains Mono", monospace;
    font-weight: 700;
    font-size: 1rem;
    color: #020617;
    z-index: 1;
  }
  .phase-content {
    background: rgba(30, 41, 59, 0.3);
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 1.25rem;
  }
  .phase-content h3 { font-size: 1.05rem; margin-bottom: 0.25rem; }
  .phase-meta { font-family: "JetBrains Mono", monospace; font-size: 0.75rem; color: #22d3ee; margin-bottom: 0.5rem; }
  .phase-content p { font-size: 0.85rem; color: #94a3b8; margin-bottom: 0.5rem; }
  .phase-artifacts { display: flex; flex-wrap: wrap; gap: 0.35rem; }
  .phase-artifacts code {
    font-size: 0.7rem;
    background: rgba(30, 41, 59, 0.5);
    padding: 0.15rem 0.5rem;
  }

  .principles { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 0.75rem; margin-top: 1.5rem; }
  .principle {
    padding: 0.75rem 1rem;
    background: rgba(30, 41, 59, 0.3);
    border: 1px solid #1e293b;
    border-radius: 8px;
    font-size: 0.85rem;
    color: #94a3b8;
    text-align: center;
  }
</style>
