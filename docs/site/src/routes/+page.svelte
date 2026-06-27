<script>
  import { base } from "$app/paths";
</script>

<svelte:head>
  <title>AFCS — Adaptive Forward Deployed Engineer Case Simulator</title>
  <meta name="description" content="Evaluate and train engineers and AI agents on realistic enterprise AI deployment scenarios. Stateful simulations, evidence-linked scoring, deterministic replay." />
</svelte:head>

<section class="hero">
  <div class="hero-badge">Enterprise AI Readiness Platform</div>
  <h1>Adaptive Forward Deployed Engineer<br>Case Simulator</h1>
  <p class="hero-sub">
    Evaluate and train human engineers and AI agents on realistic enterprise AI deployments.
    Stateful simulations with deterministic consequences, evidence-linked scoring,
    and immutable session traces — not a chatbot, not a quiz.
  </p>
  <div class="hero-actions">
    <a href={base + "/demo/"} class="btn-primary">Try the Demo</a>
    <a href="https://github.com/rmax-ai/adaptive-fde-case-simulator" class="btn-secondary" target="_blank" rel="noopener">GitHub ↗</a>
  </div>
</section>

<section class="stats">
  <div class="stat">
    <span class="stat-num">350</span>
    <span class="stat-label">Tests Passing</span>
  </div>
  <div class="stat">
    <span class="stat-num">8</span>
    <span class="stat-label">Build Phases</span>
  </div>
  <div class="stat">
    <span class="stat-num">3</span>
    <span class="stat-label">Seed Cases</span>
  </div>
  <div class="stat">
    <span class="stat-num">27</span>
    <span class="stat-label">Action Handlers</span>
  </div>
  <div class="stat">
    <span class="stat-num">6</span>
    <span class="stat-label">Scoring Dimensions</span>
  </div>
  <div class="stat">
    <span class="stat-num">15</span>
    <span class="stat-label">Adversarial Tests</span>
  </div>
</section>

<section class="section">
  <h2>What Makes This Different</h2>
  <p class="section-sub">Most AI evaluation platforms are glorified quizzes. AFCS is a stateful work simulation.</p>
  <div class="cards">
    <div class="card">
      <div class="card-icon">&#9881;</div>
      <h3>Deterministic Truth, Generative Language</h3>
      <p>LLMs render stakeholder dialogue only. Permissions, facts, approvals, and state transitions are policy-controlled — fully replayable.</p>
    </div>
    <div class="card">
      <div class="card-icon">&#9733;</div>
      <h3>Multi-Dimensional Scoring</h3>
      <p>Not one number. Six independent axes: Discovery, Technical Reasoning, Evaluation Quality, Delivery, Governance, and Operational Sustainability.</p>
    </div>
    <div class="card">
      <div class="card-icon">&#8634;</div>
      <h3>Append-Only Traceability</h3>
      <p>Every state change is an immutable event. Replay any session from its event stream. Verify integrity with pre/post state hashes.</p>
    </div>
    <div class="card">
      <div class="card-icon">&#128274;</div>
      <h3>Hard Safety Constraints</h3>
      <p>Automatic failure for unauthorized irreversible actions, regulatory bypass, or credential exposure. Scored separately from capability.</p>
    </div>
    <div class="card">
      <div class="card-icon">&#129302;</div>
      <h3>Human + Agent Interfaces</h3>
      <p>Browser-based participant workspace for humans. Structured REST API for AI agents. Same simulation, same evaluation.</p>
    </div>
    <div class="card">
      <div class="card-icon">&#9888;</div>
      <h3>Adversarial Hardening</h3>
      <p>15 adversarial tests: prompt injection, hidden state extraction, event tampering, cross-session access. RBAC + rate limiting built in.</p>
    </div>
  </div>
</section>

<section class="section dark-section">
  <h2>Trust Architecture</h2>
  <p class="section-sub">Five trust boundaries enforce separation between hidden canonical state and participant-visible projections.</p>
  <div class="trust-diagram">
    <div class="trust-row">
      <div class="trust-box trust-critical">
        <div class="trust-label">B1</div>
        <div class="trust-title">Participant → Hidden State</div>
        <div class="trust-desc">Canonical state is NEVER exposed. Only projected visible state reaches the API.</div>
      </div>
      <div class="trust-arrow">→</div>
      <div class="trust-box">
        <div class="trust-label">B2</div>
        <div class="trust-title">Participant → Stakeholder</div>
        <div class="trust-desc">Policy layer controls facts. LLM renders language only. Post-generation validation.</div>
      </div>
    </div>
    <div class="trust-row">
      <div class="trust-box">
        <div class="trust-label">B3</div>
        <div class="trust-title">Participant → Evaluation</div>
        <div class="trust-desc">Scores gated behind session completion. 403 until evaluated. No in-progress score leakage.</div>
      </div>
      <div class="trust-arrow">→</div>
      <div class="trust-box">
        <div class="trust-label">B4</div>
        <div class="trust-title">Evaluator → Participant</div>
        <div class="trust-desc">RBAC-scoped. Session-level ACL. Audit logging of all evaluator data access.</div>
      </div>
    </div>
  </div>
</section>

<section class="section">
  <h2>Three Realistic Seed Cases</h2>
  <p class="section-sub">Every case has multiple valid strategies, hidden facts, and deterministic consequences.</p>
  <div class="case-cards">
    <div class="case-card">
      <h3>Wrong Use-Case Selection</h3>
      <div class="case-meta">intermediate · $50k · 30 days</div>
      <p>A team wants a RAG assistant for customer support. The real problem is inconsistent refund policy — not knowledge access. Can you avoid building the wrong thing?</p>
      <div class="case-tags">
        <span>discovery</span><span>scope reduction</span><span>workflow analysis</span>
      </div>
    </div>
    <div class="case-card">
      <h3>Unsafe Autonomy Transition</h3>
      <div class="case-meta">advanced · $75k · 45 days</div>
      <p>Upgrade a recommendation assistant to auto-approve refunds. Irreversible actions, missing approvals, and rare edge cases absent from evaluation data.</p>
      <div class="case-tags">
        <span>governance</span><span>risk assessment</span><span>rollback planning</span>
      </div>
    </div>
    <div class="case-card">
      <h3>Unmaintainable Prototype</h3>
      <div class="case-meta">advanced · $120k · 60 days</div>
      <p>A brittle bespoke system with zero tests needs to scale 10x. No platform support, no runbooks, no owner. Should you scale it or refactor?</p>
      <div class="case-tags">
        <span>operations</span><span>ownership</span><span>platform strategy</span>
      </div>
    </div>
  </div>
</section>

<section class="cta-section">
  <h2>Ready to Evaluate Real FDE Capability?</h2>
  <p>Not a chatbot. Not a quiz. A stateful, replayable work simulation with evidence-linked evaluation.</p>
  <div class="hero-actions">
    <a href={base + "/demo/"} class="btn-primary">Try the Interactive Demo</a>
    <a href={base + "/architecture/"} class="btn-secondary">Read the Architecture</a>
  </div>
</section>

<style>
  .hero {
    text-align: center;
    padding: 5rem 1rem 4rem;
  }
  .hero-badge {
    display: inline-block;
    padding: 0.3rem 0.75rem;
    background: rgba(34, 211, 238, 0.1);
    border: 1px solid rgba(34, 211, 238, 0.2);
    border-radius: 100px;
    color: #22d3ee;
    font-size: 0.8rem;
    font-weight: 500;
    margin-bottom: 1.5rem;
  }
  .hero h1 {
    font-size: 2.8rem;
    line-height: 1.2;
    margin-bottom: 1.25rem;
    background: linear-gradient(135deg, #e2e8f0 0%, #22d3ee 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }
  .hero-sub {
    max-width: 640px;
    margin: 0 auto 2rem;
    font-size: 1.1rem;
    color: #94a3b8;
    line-height: 1.7;
  }
  .hero-actions {
    display: flex;
    gap: 1rem;
    justify-content: center;
    flex-wrap: wrap;
  }
  .btn-primary {
    display: inline-block;
    padding: 0.75rem 1.75rem;
    background: #22d3ee;
    color: #020617;
    border-radius: 8px;
    font-weight: 600;
    font-size: 1rem;
    transition: all 0.15s;
  }
  .btn-primary:hover { background: #67e8f9; text-decoration: none; }
  .btn-secondary {
    display: inline-block;
    padding: 0.75rem 1.75rem;
    border: 1px solid #1e293b;
    color: #94a3b8;
    border-radius: 8px;
    font-weight: 500;
    font-size: 1rem;
    transition: all 0.15s;
  }
  .btn-secondary:hover { border-color: #334155; color: #e2e8f0; text-decoration: none; }

  .stats {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 1rem;
    max-width: 1000px;
    margin: 0 auto 4rem;
    text-align: center;
  }
  .stat {
    padding: 1.25rem 0.5rem;
    background: rgba(30, 41, 59, 0.3);
    border: 1px solid #1e293b;
    border-radius: 8px;
  }
  .stat-num {
    display: block;
    font-family: "JetBrains Mono", monospace;
    font-size: 1.75rem;
    font-weight: 700;
    color: #22d3ee;
  }
  .stat-label {
    display: block;
    font-size: 0.75rem;
    color: #64748b;
    margin-top: 0.25rem;
  }

  .section { padding: 4rem 0; }
  .section-sub { max-width: 640px; margin-bottom: 2rem; color: #94a3b8; font-size: 1rem; }
  .dark-section { background: rgba(30, 41, 59, 0.2); border-radius: 16px; margin: 2rem 0; padding: 3rem 2rem; }

  .cards {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
  }
  .card {
    padding: 1.5rem;
    background: rgba(30, 41, 59, 0.3);
    border: 1px solid #1e293b;
    border-radius: 12px;
  }
  .card-icon { font-size: 1.5rem; margin-bottom: 0.75rem; }
  .card h3 { font-size: 1rem; margin-bottom: 0.5rem; }
  .card p { font-size: 0.85rem; color: #64748b; margin: 0; }

  .trust-diagram { display: flex; flex-direction: column; gap: 1rem; }
  .trust-row { display: grid; grid-template-columns: 1fr auto 1fr; gap: 0.5rem; align-items: start; }
  .trust-box {
    padding: 1.25rem;
    background: rgba(30, 41, 59, 0.4);
    border: 1px solid #1e293b;
    border-radius: 10px;
  }
  .trust-critical { border-color: rgba(239, 68, 68, 0.3); }
  .trust-label {
    display: inline-block;
    padding: 0.15rem 0.5rem;
    background: rgba(34, 211, 238, 0.1);
    border-radius: 4px;
    font-family: "JetBrains Mono", monospace;
    font-size: 0.7rem;
    color: #22d3ee;
    margin-bottom: 0.5rem;
  }
  .trust-title { font-weight: 600; font-size: 0.9rem; margin-bottom: 0.25rem; }
  .trust-desc { font-size: 0.8rem; color: #64748b; margin: 0; }
  .trust-arrow { font-size: 2rem; color: #334155; display: flex; align-items: center; padding-top: 0.75rem; }

  .case-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; }
  .case-card {
    padding: 1.5rem;
    background: rgba(30, 41, 59, 0.3);
    border: 1px solid #1e293b;
    border-radius: 12px;
  }
  .case-card h3 { font-size: 1rem; margin-bottom: 0.25rem; }
  .case-meta { font-family: "JetBrains Mono", monospace; font-size: 0.75rem; color: #22d3ee; margin-bottom: 0.75rem; }
  .case-card p { font-size: 0.85rem; color: #64748b; margin-bottom: 0.75rem; }
  .case-tags { display: flex; flex-wrap: wrap; gap: 0.35rem; }
  .case-tags span {
    padding: 0.15rem 0.5rem;
    background: rgba(30, 41, 59, 0.5);
    border-radius: 4px;
    font-size: 0.7rem;
    color: #94a3b8;
  }

  .cta-section {
    text-align: center;
    padding: 4rem 1rem;
    background: linear-gradient(180deg, transparent, rgba(34, 211, 238, 0.03));
    border-radius: 16px;
    margin-top: 2rem;
  }
  .cta-section h2 { font-size: 1.75rem; }
  .cta-section p { max-width: 500px; margin: 0 auto 2rem; }

  @media (max-width: 768px) {
    .hero h1 { font-size: 1.75rem; }
    .stats { grid-template-columns: repeat(3, 1fr); }
    .cards { grid-template-columns: 1fr; }
    .trust-row { grid-template-columns: 1fr; }
    .trust-arrow { display: none; }
    .case-cards { grid-template-columns: 1fr; }
  }
</style>
