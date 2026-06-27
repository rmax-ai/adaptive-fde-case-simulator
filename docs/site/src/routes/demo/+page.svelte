<script>
  let step = 0;
  let selectedAction = null;
  let interviewTarget = null;
  let showEvaluation = false;

  const steps = [
    { id: "briefing", title: "The Briefing", icon: "📋" },
    { id: "discover", title: "Discovery", icon: "🔍" },
    { id: "decide", title: "Decision", icon: "🎯" },
    { id: "evaluate", title: "Evaluation", icon: "📊" },
  ];

  const stakeholderResponses = {
    cto: {
      initial: "We need a GenAI assistant for customer support. The board wants an AI launch this quarter. Six weeks, no more. What do you think?",
      probed: "Look, our last AI project... it didn't go well. I need this to succeed. The board is watching. Can you make this work?",
      revealed: "Fine. The last project failed because we tried to automate too much. But this is different — it's just document search, right?",
    },
    ops: {
      initial: "I manage the support team. Our agents handle 200+ tickets a day. Response times are down 30% since last quarter. We need help.",
      probed: "Honestly? Most escalations aren't about knowledge. They're about refund policy — which regions qualify, what amounts, what exceptions apply.",
      revealed: "64% of handling time is assembling account data from three different systems. The policy docs only cover 62% of regional cases.",
    },
  };

  let chatHistory = [];
  let inspectedArtifacts = [];
  let discoveredFacts = [];
  let finalDecision = null;
  let evaluationScores = null;

  const artifacts = [
    { id: "support-metrics", name: "Support Metrics Dashboard", desc: "CSV: 200+ tickets/day, 30% response time decline, 64% time on data assembly" },
    { id: "refund-errors", name: "Refund Error Analysis", desc: "JSON: 62% of cases require manual policy override due to incomplete regional coverage" },
    { id: "policy-kb", name: "Policy Knowledge Base", desc: "Markdown: Only 62% of regional refund policies documented. Remaining 38% handled ad-hoc." },
    { id: "ai-vendor-proposal", name: "AI Vendor Proposal", desc: "PDF: RAG pipeline proposal, $200k implementation, 12-week timeline. Pushes GenAI as solution." },
  ];

  function nextStep() {
    if (step < steps.length - 1) {
      step++;
      selectedAction = null;
      interviewTarget = null;
      chatHistory = [];
    }
  }

  function inspectArtifact(id) {
    if (!inspectedArtifacts.includes(id)) {
      inspectedArtifacts = [...inspectedArtifacts, id];
      if (id === "support-metrics" || id === "refund-errors") {
        discoveredFacts = [...discoveredFacts, "64% of handling time is data assembly, not knowledge retrieval"];
      }
      if (id === "policy-kb") {
        discoveredFacts = [...discoveredFacts, "Policy knowledge base covers only 62% of regional cases"];
      }
    }
  }

  function sendMessage(stakeholder, message) {
    let response;
    if (chatHistory.length === 0) {
      response = stakeholderResponses[stakeholder].initial;
    } else if (chatHistory.length === 1) {
      response = stakeholderResponses[stakeholder].probed;
      if (stakeholder === "ops") {
        discoveredFacts = [...discoveredFacts, "Most escalations are about refund policy, not knowledge access"];
        discoveredFacts = [...discoveredFacts, "64% of handling time is assembling structured account data"];
      }
    } else {
      response = stakeholderResponses[stakeholder].revealed;
      if (stakeholder === "cto") {
        discoveredFacts = [...discoveredFacts, "Previous AI project failed due to over-automation"];
      }
      if (stakeholder === "ops") {
        discoveredFacts = [...discoveredFacts, "Policy knowledge base covers only 62% of regional cases"];
      }
    }
    chatHistory = [...chatHistory, { role: "participant", text: message }, { role: stakeholder, text: response }];
  }

  function selectAction(action) {
    selectedAction = action;
  }

  function makeDecision(decision) {
    finalDecision = decision;
    // Generate evaluation scores
    if (decision === "workflow") {
      evaluationScores = {
        discovery: { score: 0.88, label: "Strong" },
        technical: { score: 0.82, label: "Solid" },
        evaluation_quality: { score: 0.75, label: "Good" },
        delivery: { score: 0.80, label: "Solid" },
        governance: { score: 0.70, label: "Adequate" },
        operational_sustainability: { score: 0.85, label: "Strong" },
        overall: 0.82,
        verdict: "Efficient success — identified the real bottleneck and avoided unnecessary complexity.",
      };
    } else if (decision === "rag") {
      evaluationScores = {
        discovery: { score: 0.35, label: "Weak" },
        technical: { score: 0.45, label: "Weak" },
        evaluation_quality: { score: 0.30, label: "Weak" },
        delivery: { score: 0.50, label: "Marginal" },
        governance: { score: 0.40, label: "Weak" },
        operational_sustainability: { score: 0.25, label: "Weak" },
        overall: 0.38,
        verdict: "Missed the real problem. Optimized retrieval before validating the workflow. The policy coverage gap remains unresolved.",
      };
    }
    showEvaluation = true;
    step = 3;
  }

  function reset() {
    step = 0;
    selectedAction = null;
    interviewTarget = null;
    chatHistory = [];
    inspectedArtifacts = [];
    discoveredFacts = [];
    finalDecision = null;
    evaluationScores = null;
    showEvaluation = false;
  }
</script>

<svelte:head>
  <title>Interactive Demo — AFCS</title>
</svelte:head>

<h1>Interactive Demo: Wrong Use-Case Selection</h1>
<p class="demo-intro">
  You are a Forward Deployed Engineer. A retailer wants a RAG assistant for customer support.
  Walk through the simulation to discover what's really going on.
</p>

<div class="demo-container">
  <!-- Step indicators -->
  <div class="step-indicators">
    {#each steps as s, i}
      <button class="step-dot" class:active={step === i} class:done={step > i} onclick={() => step = i}>
        <span class="step-icon">{s.icon}</span>
        <span class="step-title">{s.title}</span>
      </button>
    {/each}
  </div>

  <div class="demo-content">
    <!-- Step 0: Briefing -->
    {#if step === 0}
      <div class="step-panel">
        <h2>The Briefing</h2>
        <div class="briefing-card">
          <div class="briefing-header">
            <span class="briefing-label">Stated Request</span>
          </div>
          <p class="briefing-quote">"Build a RAG assistant for customer support within six weeks. Budget: $50k. The board wants an AI launch this quarter."</p>
          <div class="briefing-meta">
            <div><strong>Deadline:</strong> 30 days</div>
            <div><strong>Budget:</strong> $50,000</div>
            <div><strong>Domain:</strong> Enterprise Support & Refund Operations</div>
          </div>
        </div>

        <h3>Available Actions</h3>
        <div class="action-bar">
          <button class:active={selectedAction === "inspect"} onclick={() => selectAction("inspect")}>
            🔍 Inspect Artifacts
          </button>
          <button class:active={selectedAction === "interview"} onclick={() => selectAction("interview")}>
            💬 Interview Stakeholders
          </button>
        </div>

        {#if selectedAction === "inspect"}
          <div class="action-panel">
            <h3>Evidence Artifacts</h3>
            <div class="artifact-grid">
              {#each artifacts as a}
                <button class="artifact-card" class:inspected={inspectedArtifacts.includes(a.id)} onclick={() => inspectArtifact(a.id)}>
                  <div class="artifact-name">{a.name}</div>
                  <div class="artifact-desc">{a.desc}</div>
                  {#if inspectedArtifacts.includes(a.id)}
                    <div class="artifact-check">✓ Inspected</div>
                  {/if}
                </button>
              {/each}
            </div>
          </div>
        {/if}

        {#if selectedAction === "interview"}
          <div class="action-panel">
            <h3>Stakeholders</h3>
            <div class="stakeholder-select">
              <button class:active={interviewTarget === "cto"} onclick={() => { interviewTarget = "cto"; chatHistory = []; }}>
                <div class="stakeholder-name">Marcus Chen</div>
                <div class="stakeholder-role">CTO</div>
                <div class="stakeholder-trust trust-neutral">Cooperative</div>
              </button>
              <button class:active={interviewTarget === "ops"} onclick={() => { interviewTarget = "ops"; chatHistory = []; }}>
                <div class="stakeholder-name">Sarah Kim</div>
                <div class="stakeholder-role">Head of Support Ops</div>
                <div class="stakeholder-trust trust-low">Hesitant</div>
              </button>
            </div>

            {#if interviewTarget}
              <div class="chat-window">
                {#each chatHistory as msg}
                  <div class="chat-msg" class:participant={msg.role === "participant"} class:stakeholder={msg.role !== "participant"}>
                    <div class="chat-bubble">{msg.text}</div>
                  </div>
                {/each}
                {#if chatHistory.length === 0}
                  <div class="chat-prompt">
                    <button onclick={() => sendMessage(interviewTarget, "Tell me about your goals for this project.")}>
                      "Tell me about your goals for this project."
                    </button>
                  </div>
                {:else if chatHistory.length === 2}
                  <div class="chat-prompt">
                    <button onclick={() => sendMessage(interviewTarget, "What's the biggest bottleneck in your current process?")}>
                      "What's the biggest bottleneck in your current process?"
                    </button>
                  </div>
                {:else if chatHistory.length === 4}
                  <div class="chat-prompt">
                    <button onclick={() => sendMessage(interviewTarget, "Is there anything you haven't told me about the previous project?")}>
                      "Is there anything you haven't told me?"
                    </button>
                  </div>
                {/if}
              </div>
            {/if}
          </div>
        {/if}

        {#if inspectedArtifacts.length > 0}
          <div class="discoveries">
            <h3>Discovered Facts</h3>
            {#each discoveredFacts as fact}
              <div class="discovery-item">{fact}</div>
            {/each}
          </div>
        {/if}

        <button class="next-btn" onclick={nextStep} disabled={inspectedArtifacts.length === 0}>
          Continue to Decision →
        </button>
      </div>
    {/if}

    <!-- Step 1: Decision -->
    {#if step === 1}
      <div class="step-panel">
        <h2>Your Recommendation</h2>
        <p class="decision-context">
          Based on what you've discovered: 64% of handling time is data assembly, the policy KB covers only 62% of cases,
          and the real bottleneck is workflow design — not knowledge access.
        </p>

        <div class="decision-options">
          <button class="decision-card decision-strong" onclick={() => makeDecision("workflow")}>
            <h3>Redesign the Workflow</h3>
            <p>Automate evidence assembly first. Keep refund decisions in recommendation mode. Fix the policy coverage gap. No AI system needed.</p>
            <div class="decision-impact">✓ Addresses root cause · Low risk · Under budget</div>
          </button>
          <button class="decision-card decision-weak" onclick={() => makeDecision("rag")}>
            <h3>Build the RAG Assistant</h3>
            <p>Proceed with the GenAI document search system as requested. Optimize retrieval quality. Deploy within 6 weeks.</p>
            <div class="decision-impact decision-bad">✗ Ignores root cause · $200k+ risk · Policy gap unresolved</div>
          </button>
        </div>
      </div>
    {/if}

    <!-- Step 3: Evaluation -->
    {#if step === 3 && evaluationScores}
      <div class="step-panel">
        <h2>Evaluation Results</h2>
        <div class="eval-verdict">
          <div class="eval-overall">{evaluationScores.overall.toFixed(2)}</div>
          <div class="eval-overall-label">Overall Score</div>
        </div>
        <p class="eval-summary">{evaluationScores.verdict}</p>

        <div class="eval-dimensions">
          {#each Object.entries(evaluationScores).filter(([k]) => k !== "overall" && k !== "verdict") as [dim, data]}
            <div class="eval-dim">
              <div class="eval-dim-name">{dim.replace(/_/g, " ")}</div>
              <div class="eval-dim-bar">
                <div class="eval-dim-fill" style="width: {data.score * 100}%; background: {data.score >= 0.7 ? '#22c55e' : data.score >= 0.5 ? '#eab308' : '#ef4444'}"></div>
              </div>
              <div class="eval-dim-score">{data.score.toFixed(2)} <span class="eval-dim-label">{data.label}</span></div>
            </div>
          {/each}
        </div>

        <div class="eval-details">
          {#if finalDecision === "workflow"}
            <h3>What You Did Well</h3>
            <ul>
              <li>Inspected all available evidence before recommending</li>
              <li>Discovered the latent problem (workflow, not knowledge)</li>
              <li>Narrowed scope to the real bottleneck</li>
              <li>Avoided unnecessary AI complexity</li>
              <li>Proposed a measurable, reversible intervention</li>
            </ul>
          {:else}
            <h3>What You Missed</h3>
            <ul>
              <li>Did not question whether search was the real bottleneck</li>
              <li>Ignored the policy coverage gap (62% documented)</li>
              <li>Optimized retrieval before validating the workflow hypothesis</li>
              <li>Proposed $200k+ solution for a problem that needed process change</li>
              <li>No rollback plan if the RAG system underperforms</li>
            </ul>
          {/if}
        </div>

        <button class="next-btn" onclick={reset}>Try Another Path →</button>
      </div>
    {/if}
  </div>
</div>

<section class="demo-cta">
  <h2>This is what AFCS measures</h2>
  <p>Not whether you picked the "right" architecture. Whether you:<br>
  gathered evidence before deciding, discovered the latent problem,<br>
  narrowed scope appropriately, and defined a reversible path forward.</p>
  <p>The full platform runs 3 complete cases with 27 action types,<br>
  12 automated validators, and 6 evaluation dimensions.</p>
  <div style="margin-top: 1.5rem;">
    <a href="https://github.com/rmax-ai/adaptive-fde-case-simulator" class="demo-btn" target="_blank" rel="noopener">
      View on GitHub ↗
    </a>
  </div>
</section>

<style>
  .demo-intro {
    max-width: 640px;
    color: #94a3b8;
    margin-bottom: 2rem;
    font-size: 1rem;
  }
  .demo-container {
    background: rgba(30, 41, 59, 0.2);
    border: 1px solid #1e293b;
    border-radius: 16px;
    overflow: hidden;
  }
  .step-indicators {
    display: flex;
    border-bottom: 1px solid #1e293b;
  }
  .step-dot {
    flex: 1;
    padding: 0.75rem;
    background: none;
    border: none;
    color: #475569;
    cursor: pointer;
    text-align: center;
    font-size: 0.8rem;
    transition: all 0.15s;
  }
  .step-dot:hover { color: #94a3b8; }
  .step-dot.active { color: #22d3ee; background: rgba(34, 211, 238, 0.05); }
  .step-dot.done { color: #22c55e; }
  .step-icon { display: block; font-size: 1.25rem; margin-bottom: 0.15rem; }

  .demo-content { padding: 2rem; }
  .step-panel { max-width: 800px; margin: 0 auto; }
  .step-panel h2 { margin-bottom: 0.5rem; }
  .step-panel h3 { margin: 1.25rem 0 0.5rem; }

  /* Briefing */
  .briefing-card {
    background: rgba(30, 41, 59, 0.4);
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
  }
  .briefing-label {
    font-family: "JetBrains Mono", monospace;
    font-size: 0.7rem;
    color: #22d3ee;
    text-transform: uppercase;
    letter-spacing: 0.1em;
  }
  .briefing-quote {
    font-size: 1.1rem;
    color: #e2e8f0;
    font-style: italic;
    margin: 0.75rem 0;
  }
  .briefing-meta {
    display: flex;
    gap: 2rem;
    font-size: 0.8rem;
    color: #64748b;
  }

  /* Actions */
  .action-bar {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1rem;
  }
  .action-bar button {
    padding: 0.6rem 1rem;
    background: rgba(30, 41, 59, 0.4);
    border: 1px solid #1e293b;
    border-radius: 8px;
    color: #94a3b8;
    cursor: pointer;
    font-size: 0.9rem;
    transition: all 0.15s;
  }
  .action-bar button:hover { border-color: #334155; }
  .action-bar button.active { border-color: #22d3ee; color: #22d3ee; background: rgba(34, 211, 238, 0.05); }

  .action-panel { margin: 1rem 0; }

  /* Artifacts */
  .artifact-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 0.5rem;
  }
  .artifact-card {
    padding: 0.75rem;
    background: rgba(30, 41, 59, 0.3);
    border: 1px solid #1e293b;
    border-radius: 8px;
    cursor: pointer;
    text-align: left;
    transition: all 0.15s;
    color: inherit;
  }
  .artifact-card:hover { border-color: #334155; }
  .artifact-card.inspected { border-color: #22c55e; background: rgba(34, 197, 94, 0.05); }
  .artifact-name { font-weight: 600; font-size: 0.9rem; margin-bottom: 0.25rem; }
  .artifact-desc { font-size: 0.75rem; color: #64748b; }
  .artifact-check { font-size: 0.7rem; color: #22c55e; margin-top: 0.35rem; }

  /* Stakeholders */
  .stakeholder-select {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 0.75rem;
  }
  .stakeholder-select button {
    flex: 1;
    padding: 0.75rem;
    background: rgba(30, 41, 59, 0.3);
    border: 1px solid #1e293b;
    border-radius: 8px;
    cursor: pointer;
    text-align: left;
    transition: all 0.15s;
    color: inherit;
  }
  .stakeholder-select button:hover { border-color: #334155; }
  .stakeholder-select button.active { border-color: #22d3ee; }
  .stakeholder-name { font-weight: 600; font-size: 0.9rem; }
  .stakeholder-role { font-size: 0.75rem; color: #64748b; margin-bottom: 0.25rem; }
  .stakeholder-trust {
    display: inline-block;
    padding: 0.1rem 0.5rem;
    border-radius: 4px;
    font-size: 0.65rem;
    font-weight: 500;
  }
  .trust-neutral { background: rgba(34, 211, 238, 0.1); color: #22d3ee; }
  .trust-low { background: rgba(234, 179, 8, 0.1); color: #eab308; }

  /* Chat */
  .chat-window {
    background: rgba(2, 6, 23, 0.4);
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 1rem;
    max-height: 300px;
    overflow-y: auto;
  }
  .chat-msg { margin-bottom: 0.75rem; display: flex; }
  .chat-msg.participant { justify-content: flex-end; }
  .chat-msg.stakeholder { justify-content: flex-start; }
  .chat-bubble {
    max-width: 80%;
    padding: 0.6rem 0.85rem;
    border-radius: 10px;
    font-size: 0.85rem;
    line-height: 1.5;
  }
  .participant .chat-bubble { background: rgba(34, 211, 238, 0.15); color: #e2e8f0; }
  .stakeholder .chat-bubble { background: rgba(30, 41, 59, 0.6); color: #cbd5e1; }
  .chat-prompt { margin-top: 0.5rem; }
  .chat-prompt button {
    width: 100%;
    padding: 0.5rem 0.75rem;
    background: rgba(30, 41, 59, 0.4);
    border: 1px dashed #334155;
    border-radius: 8px;
    color: #94a3b8;
    cursor: pointer;
    font-size: 0.85rem;
    text-align: left;
    transition: all 0.15s;
  }
  .chat-prompt button:hover { border-color: #22d3ee; color: #e2e8f0; }

  /* Discoveries */
  .discoveries { margin-top: 1.25rem; }
  .discovery-item {
    padding: 0.5rem 0.75rem;
    background: rgba(34, 197, 94, 0.05);
    border: 1px solid rgba(34, 197, 94, 0.15);
    border-radius: 6px;
    margin-bottom: 0.35rem;
    font-size: 0.8rem;
    color: #86efac;
  }

  .next-btn {
    display: block;
    width: 100%;
    margin-top: 1.5rem;
    padding: 0.85rem;
    background: #22d3ee;
    color: #020617;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    font-size: 1rem;
    cursor: pointer;
    transition: all 0.15s;
  }
  .next-btn:hover { background: #67e8f9; }
  .next-btn:disabled { opacity: 0.3; cursor: not-allowed; }

  /* Decision */
  .decision-context {
    color: #94a3b8;
    margin-bottom: 1.5rem;
    font-size: 0.95rem;
  }
  .decision-options {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 1rem;
  }
  .decision-card {
    padding: 1.5rem;
    border-radius: 12px;
    cursor: pointer;
    text-align: left;
    transition: all 0.2s;
    color: inherit;
    border: 1px solid #1e293b;
    background: rgba(30, 41, 59, 0.3);
  }
  .decision-card:hover { border-color: #334155; transform: translateY(-2px); }
  .decision-strong { border-color: rgba(34, 197, 94, 0.3); }
  .decision-weak { border-color: rgba(239, 68, 68, 0.2); }
  .decision-card h3 { margin-bottom: 0.5rem; font-size: 1rem; }
  .decision-card p { font-size: 0.85rem; color: #94a3b8; margin-bottom: 0.75rem; }
  .decision-impact {
    font-size: 0.75rem;
    padding: 0.35rem 0.6rem;
    border-radius: 4px;
    background: rgba(34, 197, 94, 0.1);
    color: #86efac;
  }
  .decision-bad { background: rgba(239, 68, 68, 0.1); color: #fca5a5; }

  /* Evaluation */
  .eval-verdict {
    text-align: center;
    margin: 1.5rem 0;
  }
  .eval-overall {
    font-family: "JetBrains Mono", monospace;
    font-size: 3.5rem;
    font-weight: 700;
    color: #22d3ee;
  }
  .eval-overall-label {
    font-size: 0.85rem;
    color: #64748b;
  }
  .eval-summary {
    text-align: center;
    color: #94a3b8;
    max-width: 500px;
    margin: 0 auto 2rem;
  }
  .eval-dimensions {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    margin-bottom: 2rem;
  }
  .eval-dim {
    display: grid;
    grid-template-columns: 160px 1fr 100px;
    align-items: center;
    gap: 0.75rem;
  }
  .eval-dim-name {
    font-size: 0.8rem;
    color: #64748b;
    text-transform: capitalize;
  }
  .eval-dim-bar {
    height: 8px;
    background: rgba(30, 41, 59, 0.5);
    border-radius: 4px;
    overflow: hidden;
  }
  .eval-dim-fill { height: 100%; border-radius: 4px; transition: width 0.5s ease; }
  .eval-dim-score {
    font-family: "JetBrains Mono", monospace;
    font-size: 0.85rem;
    color: #e2e8f0;
    text-align: right;
  }
  .eval-dim-label { font-size: 0.7rem; color: #64748b; }

  .eval-details {
    background: rgba(30, 41, 59, 0.3);
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 1.25rem;
  }
  .eval-details h3 { margin-bottom: 0.5rem; margin-top: 0; }
  .eval-details ul { padding-left: 1.25rem; }
  .eval-details li {
    font-size: 0.85rem;
    color: #94a3b8;
    margin-bottom: 0.35rem;
  }
  .eval-details li::marker { color: #22d3ee; }

  /* CTA */
  .demo-cta {
    text-align: center;
    padding: 3rem 0 1rem;
  }
  .demo-cta p { max-width: 560px; margin: 0 auto 0.75rem; color: #94a3b8; }
  .demo-btn {
    display: inline-block;
    padding: 0.75rem 1.75rem;
    background: rgba(30, 41, 59, 0.5);
    border: 1px solid #334155;
    color: #e2e8f0;
    border-radius: 8px;
    font-weight: 500;
    font-size: 1rem;
    transition: all 0.15s;
  }
  .demo-btn:hover { background: rgba(30, 41, 59, 0.8); text-decoration: none; }

  @media (max-width: 768px) {
    .decision-options { grid-template-columns: 1fr; }
    .artifact-grid { grid-template-columns: 1fr; }
    .stakeholder-select { flex-direction: column; }
    .eval-dim { grid-template-columns: 100px 1fr 70px; }
  }
</style>
