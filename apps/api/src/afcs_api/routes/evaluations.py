"""Evaluation and report routes for completed sessions."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as SASession

from afcs_api.db import get_db
from afcs_api.middleware import ActorRole, require_role
from afcs_api.schemas import EvaluationResponse, ReportResponse
from afcs_api.services.session_service import SessionService

router = APIRouter(prefix="/api/v1/sessions/{session_id}", tags=["evaluations"])


@router.get(
    "/evaluation",
    response_model=EvaluationResponse,
    dependencies=[Depends(require_role(ActorRole.EVALUATOR, ActorRole.ADMIN))],
)
def get_evaluation(
    session_id: uuid.UUID,
    db: SASession = Depends(get_db),  # noqa: B008
) -> EvaluationResponse:
    """Get evaluation results for a completed session.

    Returns 403 if session is not COMPLETED or EVALUATED.
    """
    service = SessionService(db)
    record = service.get_session(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if record.status not in ("completed", "evaluated"):
        raise HTTPException(
            status_code=403,
            detail="Session is not completed. Evaluation is only available after "
            "submitting the final recommendation.",
        )

    evaluation = service.get_evaluation(record)
    if evaluation is None:
        raise HTTPException(status_code=500, detail="Failed to compute evaluation")

    return EvaluationResponse(
        session_id=evaluation.get("session_id", str(session_id)),
        overall_score=evaluation.get("overall_score", 0.0),
        dimensions=evaluation.get("dimensions", []),
        hard_constraint_violations=evaluation.get("hard_constraint_violations", []),
        strongest_behaviors=evaluation.get("strongest_behaviors", []),
        weakest_behaviors=evaluation.get("weakest_behaviors", []),
        missed_evidence=evaluation.get("missed_evidence", []),
        status=evaluation.get("status", record.status),
    )


@router.get(
    "/report",
    response_model=ReportResponse,
    dependencies=[Depends(require_role(ActorRole.EVALUATOR, ActorRole.ADMIN))],
)
def get_report(
    session_id: uuid.UUID,
    db: SASession = Depends(get_db),  # noqa: B008
) -> ReportResponse:
    """Get the full participant report for a completed session.

    Returns 403 if session is not COMPLETED or EVALUATED.
    """
    service = SessionService(db)
    record = service.get_session(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if record.status not in ("completed", "evaluated"):
        raise HTTPException(
            status_code=403,
            detail="Session is not completed. Report is only available after "
            "submitting the final recommendation.",
        )

    report = service.get_report(record)
    if report is None:
        raise HTTPException(status_code=500, detail="Failed to generate report")

    evaluation_data = report.get("evaluation")
    evaluation = None
    if evaluation_data:
        evaluation = EvaluationResponse(
            session_id=evaluation_data.get("session_id", str(session_id)),
            overall_score=evaluation_data.get("overall_score", 0.0),
            dimensions=evaluation_data.get("dimensions", []),
            hard_constraint_violations=evaluation_data.get("hard_constraint_violations", []),
            strongest_behaviors=evaluation_data.get("strongest_behaviors", []),
            weakest_behaviors=evaluation_data.get("weakest_behaviors", []),
            missed_evidence=evaluation_data.get("missed_evidence", []),
            status=evaluation_data.get("status", record.status),
        )

    return ReportResponse(
        session_id=report.get("session_id", str(session_id)),
        case_id=report.get("case_id", record.case_id),
        case_version=report.get("case_version", record.case_version),
        participant_id=report.get("participant_id", record.participant_id),
        status=report.get("status", record.status),
        evaluation=evaluation,
        timeline=report.get("timeline", []),
        artifacts_inspected=report.get("artifacts_inspected", []),
        stakeholder_interactions=report.get("stakeholder_interactions", []),
        recommendation=report.get("recommendation", {}),
    )
