# PYTHON_DEVELOPMENT.md — AFCS Day-to-Day Engineering

Companion to `AGENTS.md`. Covers Python idioms, async patterns, testing, profiling,
observability, and production readiness specific to this project.

---

## Language Idioms

### Pydantic v2

Always use Pydantic v2 syntax:

```python
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime, UTC

class CaseDefinition(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    case_id: str = Field(..., pattern=r"^case_[a-z0-9_]+$")
    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("version")
    @classmethod
    def _check_semver(cls, v: str) -> str:
        parts = v.split(".")
        if len(parts) != 3:
            raise ValueError("Must be semver")
        return v
```

**Rules:**
- `model_config` is reserved — never name a field `model_config`
- Use `default_factory` for mutable defaults (lists, dicts)
- Use `from __future__ import annotations` + string annotations for forward refs
- Call `model_rebuild()` in package `__init__.py` for cross-module type references

### SQLAlchemy 2.0

Use declarative async style:

```python
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import uuid
from datetime import datetime, UTC

class Base(DeclarativeBase):
    pass

class SimulationSession(Base):
    __tablename__ = "simulation_sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id"))
    status: Mapped[str] = mapped_column(String(50))
    current_state: Mapped[dict] = mapped_column(JSONB)
    current_sequence: Mapped[int] = mapped_column(default=0)
    started_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
```

**Rules:**
- Use `Mapped[]` type annotations (not the old `Column()` style)
- JSONB for `current_state` and payload fields
- UUIDs for all primary keys
- No `default=datetime.utcnow` (deprecated)
- Alembic for migrations — always generate, never hand-edit migration files

### Structlog

```python
import structlog

logger = structlog.get_logger()

# Structured logging — never f-strings in log messages
logger.info("action_executed", action_type="inspect_artifact", session_id=str(session_id))
```

---

## Async Patterns

- **FastAPI routes**: `async def` with async SQLAlchemy sessions
- **LLM calls**: await `model_provider.generate()` — never block the event loop
- **State transitions**: synchronous (deterministic, no I/O) — no async needed
- **Background tasks**: use `asyncio.create_task()` for report generation, evaluation

```python
# FastAPI dependency for DB session
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session

@router.post("/sessions/{session_id}/actions")
async def execute_action(
    session_id: UUID,
    action: ActionRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ActionResponse:
    service = SessionService(db)
    result = await service.execute_action(session_id, action)
    return result
```

---

## Testing

### Unit tests

```python
import pytest
from afcs.domain.events import SimulationEvent
from uuid import uuid4

def test_event_sequence_is_monotonic():
    session_id = uuid4()
    events = [
        SimulationEvent(session_id=session_id, sequence_number=i, ...)
        for i in range(10)
    ]
    for i, e in enumerate(events):
        assert e.sequence_number == i
```

### Async tests

```python
import pytest
from httpx import AsyncClient, ASGITransport
from afcs.api.main import app

@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_create_session(client: AsyncClient):
    response = await client.post("/sessions", json={"case_id": "case_wrong_use_case"})
    assert response.status_code == 201
    assert response.json()["status"] == "active"
```

### Property-based tests

```python
from hypothesis import given, strategies as st

@given(
    actions=st.lists(st.sampled_from(VALID_ACTIONS), min_size=1, max_size=50)
)
def test_action_sequence_never_exceeds_budget(actions):
    budget = 100.0
    remaining = budget
    for action in actions:
        cost = ACTION_COSTS[action]
        if cost > remaining:
            break  # expected — budget exhausted
        remaining -= cost
    assert remaining >= 0
```

### Test organization

```
tests/
├── unit/                    # Pure function tests (no I/O)
│   ├── test_events.py
│   ├── test_transitions.py
│   └── test_validators.py
├── contract/                # API schema compliance
│   └── test_agent_api.py
├── integration/             # Database + services
│   ├── test_session_flow.py
│   └── test_stakeholder.py
├── case-validation/         # Per case
│   ├── test_wrong_use_case.py
│   ├── test_unsafe_autonomy.py
│   └── test_unmaintainable.py
├── adversarial/             # Security tests
│   ├── test_prompt_injection.py
│   └── test_state_extraction.py
└── e2e/                     # Playwright + httpx
    ├── test_human_flow.py
    └── test_agent_flow.py
```

---

## Profiling & Performance

- Profile before optimizing — never guess
- Hot path: state transition engine (called on every action) — keep it pure and fast
- Cold path: LLM calls (latency-dominated) — not optimization targets
- Use `cProfile` for CPU profiling, `py-spy` for production profiling
- Benchmark state hashing with `pytest-benchmark`

---

## Observability

OpenTelemetry spans for:

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

@tracer.start_as_current_span("state_transition")
def apply_transition(current_state: dict, action: Action) -> dict:
    span = trace.get_current_span()
    span.set_attribute("action_type", action.action_type)
    span.set_attribute("session_id", str(action.session_id))
    # ...
```

Record on every span:
- `session_id`, `case_id`, `action_type`, `event_type`
- `model_version`, `prompt_version` (for LLM spans)
- `latency_ms`, `token_count` (for LLM spans)
- `error_type`, `retry_count` (for error spans)

---

## Production Readiness

- **Health endpoint**: `GET /health` returns 200 if DB + services alive
- **Readiness endpoint**: `GET /ready` returns 200 if migrations applied
- **Graceful shutdown**: handle SIGTERM, drain in-flight requests
- **Connection pooling**: asyncpg pool size = 2 × CPU cores
- **No raw secrets in code**: use environment variables or a secret manager

---

## References

- `AGENTS.md` — project conventions and non-negotiables
- `PYTHON_API_DESIGN.md` — API surface design
- `docs/architecture/ARCHITECTURE.md` — system architecture
