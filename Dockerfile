# =============================================================================
# Stage 1: Build (dependencies)
# =============================================================================
FROM python:3.12-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY packages/ packages/
COPY apps/api/src/afcs_api/ apps/api/src/afcs_api/

RUN uv sync --frozen --no-dev

# =============================================================================
# Stage 2: Runtime
# =============================================================================
FROM python:3.12-slim AS runtime

EXPOSE 8000

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Copy installed dependencies from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY apps/ apps/
COPY packages/ packages/

# Ensure the PYTHONPATH includes all package source roots
ENV PYTHONPATH="/app/packages/case-schema/src:/app/packages/domain/src:/app/packages/simulation-engine/src:/app/packages/stakeholder-engine/src:/app/packages/evaluation-engine/src:/app/packages/model-gateway/src:/app/packages/shared-types/src:/app/apps/api/src"

# Default command: run uvicorn
CMD ["uvicorn", "afcs_api.app:app", "--host", "0.0.0.0", "--port", "8000"]
