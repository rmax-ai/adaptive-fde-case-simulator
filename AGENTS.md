# AGENTS.md – Guidelines for AFCS

This document captures the conventions and guidelines that all contributors
and AI coding agents (Codex, subagents) must follow when working on the
**Adaptive Forward Deployed Engineer Case Simulator**.

> Companion docs: `PYTHON_DEVELOPMENT.md`, `PYTHON_API_DESIGN.md`,
> `docs/architecture/ARCHITECTURE.md`, `docs/security/THREAT_MODEL.md`

---

## 1. Repo Structure

Monorepo with strict separation:

```
afcs/
├── apps/           # Deployable applications (web UI, API server)
├── packages/       # Shared libraries (domain, engines, gateway, ui)
├── cases/          # YAML case definitions (one directory per case)
├── tests/          # contract, integration, e2e, case-validation, adversarial
├── docs/           # architecture, case-authoring, evaluation, security, ops
├── scripts/        # CLI entry points, dev helpers
├── docker/         # Dockerfiles, compose
└── README.md
```

**Rules:**
- `packages/` libraries must NOT import from `apps/`
- `apps/api` depends on all `packages/`; `apps/web` depends on `packages/ui` and `packages/shared-types`
- Case YAML files (.yaml) live under `cases/<case-name>/` — one file per case version
- No circular imports between packages

---

## 2. Python Conventions

- **Python 3.12+** required
- **Pydantic v2** for all data models, schemas, validation
- **SQLAlchemy 2.0** (declarative, async) for persistence
- **FastAPI** for the API layer — keep route handlers thin, delegate to services
- **Type annotations everywhere** — strict mypy/pyright mode
- **Use `datetime.now(UTC)` NOT `datetime.utcnow()`** (deprecated in 3.12+)
- **Use `from __future__ import annotations`** in all modules
- **Pydantic forward references**: use string annotations + `model_rebuild()` for cross-module types
- **No `src/__init__.py`** — `src/` layout packages must not have a top-level `__init__.py`

### Project configuration

```toml
# pyproject.toml (key sections)
[project]
name = "afcs"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "pydantic>=2.9",
    "sqlalchemy>=2.0",
    "alembic>=1.14",
    "asyncpg>=0.30",
    "structlog>=24",
]

[project.optional-dependencies]
dev = [
    "pytest>=8",
    "pytest-asyncio>=0.24",
    "ruff>=0.7",
    "ty>=0.6",
    "httpx>=0.28",
    "playwright>=1.49",
]

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "RUF", "B", "SIM", "C4"]

[tool.ty]
packages = ["apps.api", "packages"]
```

---

## 3. Error Handling

- **Domain exceptions** in `packages/domain/exceptions.py` — never raise raw `Exception`
- **FastAPI exception handlers** map domain exceptions to HTTP responses
- **No bare `except:`** — always catch specific exception types
- **Validation errors** return structured Pydantic error responses, never raw tracebacks
- **Simulation errors** (invalid action, precondition failure) return typed error events

```python
# packages/domain/exceptions.py
class SimulationError(Exception): ...
class InvalidActionError(SimulationError): ...
class PreconditionError(SimulationError): ...
class HardConstraintViolation(SimulationError): ...
class ForbiddenDisclosure(SimulationError): ...
```

---

## 4. Testing

- **pytest** with `pytest-asyncio` for all async tests
- **Test location**: `tests/<category>/` mirrors source structure
- **Coverage requirement**: >80% on all `packages/` domain logic
- **Property-based tests**: use `hypothesis` for event ordering, state hashing, forbidden facts
- **Contract tests**: `tests/contract/` — API schema compliance
- **Integration tests**: `tests/integration/` — session start-to-completion
- **E2E tests**: `tests/end-to-end/` — Playwright for browser, httpx for agent API
- **Case validation tests**: `tests/case-validation/` — every seed case must have 2+ valid trajectories
- **Adversarial tests**: `tests/adversarial/` — prompt injection, state extraction, score manipulation

### Running tests

```bash
# All tests
uv run pytest tests/ -v

# Specific category
uv run pytest tests/case-validation/ -v

# With coverage
uv run pytest tests/ --cov=packages --cov=apps/api --cov-report=term-missing
```

### TDD requirement

Every feature follows RED-GREEN-REFACTOR. Write the failing test FIRST, verify it fails, then implement.

---

## 6. Dependencies

- **uv** for dependency management (`uv sync --extra dev`)
- **Version pinning**: `>=` for compatible upgrades, exact pins in `uv.lock`
- **No new dependencies** without documented justification in the PR
- **Audit before adding**: check license, maintenance status, size

---

## 7. Formatting and Linting

```bash
# Format
uv run ruff format src/ tests/

# Lint (auto-fix)
uv run ruff check --fix src/ tests/

# Type check
uv run ty check

# ⛔ HARD GATE: All three must pass before any commit
```

---

## 8. CI/CD

- **GitHub Actions** workflow in `.github/workflows/ci.yml`
- Required checks for PR merge:
  1. `ruff check` (zero errors)
  2. `ruff format --check` (zero diffs)
  3. `ty check` (zero errors)
  4. `pytest` (all pass)
- **No PR merge without green CI**

---

## 9. Architecture Non-Negotiables

These principles from the mega spec MUST be followed:

1. **Domain logic before infrastructure** — core simulation logic has zero framework dependencies
2. **Deterministic truth, generative language** — LLM renders words only; policy controls facts
3. **Structured actions before unrestricted chat** — every participant interaction is a typed action
4. **Evidence-linked evaluation** — every score cites specific events
5. **Multiple valid strategies** — no single "correct" architecture in any case
6. **Append-only traceability** — all state changes flow through the event stream
7. **No hidden magic** — every state transition is explicit and testable
8. **No vendor lock-in** — core domain components are provider-agnostic
9. **No single score** — capability is a vector, not a number

---

## 10. Key Gotchas

- **`datetime.utcnow()`** is deprecated in 3.12+ → use `datetime.now(UTC)`
- **`src/__init__.py`** causes ty "Source file found twice" → delete it
- **Pydantic v2 `model_config`** is reserved → never name a field `model_config`
- **Forward references**: use string annotations + call `model_rebuild()` in `__init__.py`
- **Worktree `.venv`** — don't copy `.venv` between worktrees; run `uv sync --extra dev` in each
- **Trailing commas in parenthesized strings** → creates tuples, not strings

---

## 11. References

- `PYTHON_DEVELOPMENT.md` — day-to-day Python engineering
- `PYTHON_API_DESIGN.md` — API surface design conventions
- `docs/architecture/ARCHITECTURE.md` — system architecture
- `docs/security/THREAT_MODEL.md` — threat model and security controls
- `docs/case-authoring/` — how to write and validate cases
- `docs/evaluation/` — scoring model and validators
