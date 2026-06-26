# PYTHON_API_DESIGN.md — AFCS API Surface Design

Companion to `AGENTS.md`. Covers API naming, type design, error architecture,
and versioning for the AFCS FastAPI backend and agent API.

---

## Naming Conventions

- **Routes**: RESTful, noun-based, plural for collections
  - `POST /sessions` — create
  - `GET /sessions/{id}` — read
  - `GET /sessions/{id}/actions` — list available actions
  - `POST /sessions/{id}/actions` — execute action
  - `GET /sessions/{id}/artifacts` — list artifacts
  - `GET /sessions/{id}/artifacts/{artifact_id}` — read artifact
  - `GET /sessions/{id}/stakeholders` — list stakeholders
  - `POST /sessions/{id}/stakeholders/{stakeholder_id}/messages` — send message
  - `POST /sessions/{id}/final-recommendation` — submit recommendation
  - `GET /sessions/{id}/report` — get participant report
  - `GET /sessions/{id}/events` — get event stream
- **Query parameters**: snake_case (`?case_id=...`, `?include_events=true`)
- **JSON body**: camelCase for web API compatibility (Pydantic `alias_generator`)

---

## Type Design

### Request/Response models

```python
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from datetime import datetime

class CreateSessionRequest(BaseModel):
    model_config = ConfigDict(alias_generator=lambda s: "".join(
        word.capitalize() if i else word
        for i, word in enumerate(s.split("_"))
    ))

    case_id: str = Field(..., examples=["wrong-use-case"])
    participant_id: str | None = None

class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    case_id: str
    case_version: str
    status: str
    current_sequence: int
    started_at: datetime
    completed_at: datetime | None
```

### Error types

```python
class APIError(BaseModel):
    error_code: str  # machine-readable slug
    message: str     # human-readable
    details: dict | None = None  # structured context

# Example error codes:
# - "invalid_action" — action not in allowed actions
# - "precondition_failed" — required conditions not met
# - "hard_constraint_violation" — irreversible without approval
# - "forbidden_disclosure" — stakeholder refused
# - "session_not_found"
# - "case_not_found"
```

---

## Action Schemas (Agent API)

Every action must expose its parameter schema for machine discovery:

```python
class ActionSchema(BaseModel):
    action_type: str
    description: str
    parameters_schema: dict  # JSON Schema
    preconditions: list[str]
    time_cost: int  # minutes (simulated)
    budget_cost: float | None = None

# GET /sessions/{id}/actions returns:
# {
#   "actions": [
#     {
#       "action_type": "define_evaluation",
#       "description": "Define evaluation baseline, metrics, and failure classes",
#       "parameters_schema": {
#         "type": "object",
#         "required": ["baseline", "metrics", "failure_classes"],
#         "properties": {
#           "baseline": {"type": "string"},
#           "metrics": {"type": "array", "items": {"type": "string"}},
#           "failure_classes": {"type": "array", "items": {"type": "string"}}
#         }
#       },
#       "preconditions": ["session_active", "artifacts_inspected"],
#       "time_cost": 30,
#       "budget_cost": null
#     }
#   ]
# }
```

---

## Stakeholder Message Format

```python
class StakeholderMessageRequest(BaseModel):
    content: str = Field(..., max_length=2000)

class StakeholderMessageResponse(BaseModel):
    message_id: str
    stakeholder_id: str
    content: str
    tone: str  # cooperative | hesitant | blocked | escalating | awaiting_evidence
    timestamp: datetime
    disclosed_fact_ids: list[str]
    policy_decision_id: str
```

**Rules:**
- `disclosed_fact_ids` must be a subset of `allowed_facts` from the policy engine
- `tone` is a qualitative signal — never expose numeric trust scores via API
- Messages are immutable — stored in the event stream

---

## Pagination

For potentially large collections:

```python
class PaginationParams(BaseModel):
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=200)

class PaginatedResponse(BaseModel):
    items: list
    total: int
    offset: int
    limit: int
```

---

## Versioning

- **API version**: URL prefix `/api/v1/`
- **Case version**: semantic version in case YAML — API returns `case_version`
- **Schema evolution**: additive only (new fields, never remove)
- **Backward compatibility**: v1 endpoints remain available during v2 development

---

## OpenAPI / Swagger

- FastAPI auto-generates OpenAPI at `/docs` and `/redoc`
- All request/response models must have `examples` and `description` fields
- Tag routes by domain: `sessions`, `artifacts`, `stakeholders`, `evaluation`, `admin`

```python
router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])
```

---

## References

- `AGENTS.md` — project conventions
- `PYTHON_DEVELOPMENT.md` — day-to-day engineering
- `docs/architecture/ARCHITECTURE.md` — API section
