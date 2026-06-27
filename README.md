# Adaptive Forward Deployed Engineer Case Simulator (AFCS)

Evaluate and train human engineers and AI agents on realistic Forward Deployed Engineer work. Stateful simulations with deterministic consequences, evidence-linked scoring, and immutable session traces.

**[📖 Documentation & Demo Site](https://rmax-ai.github.io/adaptive-fde-case-simulator/)**

## Quick Start

```bash
# Install Python deps
uv sync --extra dev

# Run tests
uv run pytest tests/          # 350 tests

# Validate a case
uv run afcs validate ./cases/wrong-use-case/

# Start the API
uv run uvicorn afcs_api.app:app --reload
```

## What Makes This Different

Not a chatbot. Not a quiz. AFCS simulates real enterprise AI deployment scenarios:

- **Deterministic truth, generative language** — LLM renders stakeholder dialogue only. Permissions, facts, and approvals are policy-controlled
- **6-dimensional scoring** — Discovery, Technical Reasoning, Evaluation Quality, Delivery, Governance, and Operational Sustainability
- **Append-only traceability** — every state change is an immutable event. Full session replay
- **Hard safety constraints** — automatic failure for unauthorized irreversible actions, regulatory bypass, or credential exposure
- **Human + Agent interfaces** — browser workspace for humans, structured REST API for AI agents

## Architecture

See the [interactive architecture doc](https://rmax-ai.github.io/adaptive-fde-case-simulator/architecture/) or [docs/architecture/](docs/architecture/).

## Docker

```bash
docker compose up
```

Starts PostgreSQL + FastAPI API server.

## Seed Cases

| Case | Difficulty | Budget | Key Challenge |
|------|-----------|--------|---------------|
| Wrong Use-Case Selection | Intermediate | $50k | RAG vs workflow redesign |
| Unsafe Autonomy Transition | Advanced | $75k | Auto-approve without safeguards |
| Unmaintainable Prototype | Advanced | $120k | Scale brittle bespoke system |

## Tech Stack

- **Frontend:** React + TypeScript + Vite + TanStack Query
- **Backend:** Python 3.12 + FastAPI + Pydantic v2
- **Database:** PostgreSQL + SQLAlchemy 2.0 + Alembic
- **CI/CD:** GitHub Actions (ruff + pytest)
- **Docs:** SvelteKit static site on GitHub Pages

## License

MIT
