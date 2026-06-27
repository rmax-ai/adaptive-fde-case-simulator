"""RBAC middleware for role-based access control.

Checks the X-Actor-Role header on sensitive endpoints.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum

from fastapi import HTTPException, Request


class ActorRole(StrEnum):
    """Allowed actor roles for AFCS API access control."""

    PARTICIPANT = "participant"
    EVALUATOR = "evaluator"
    ADMIN = "admin"


def require_role(*allowed_roles: ActorRole) -> Callable[[Request], None]:
    """FastAPI dependency that enforces role-based access.

    Usage:
        @router.get(
            "/evaluation",
            dependencies=[Depends(require_role(ActorRole.EVALUATOR, ActorRole.ADMIN))],
        )

    The role is read from the X-Actor-Role header. Returns 403 if the
    role is missing or not in the allowed set.
    """

    def dependency(request: Request) -> None:
        role_header = request.headers.get("X-Actor-Role", "").strip().lower()
        if not role_header:
            raise HTTPException(
                status_code=403,
                detail="Missing X-Actor-Role header. Access denied.",
            )
        if role_header not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=(
                    f"Role '{role_header}' is not authorised for this "
                    f"endpoint. Required one of: {', '.join(allowed_roles)}"
                ),
            )

    return dependency


def get_actor_role(request: Request) -> str | None:
    """Extract the actor role from the request header, if present."""
    return request.headers.get("X-Actor-Role", "").strip().lower() or None
