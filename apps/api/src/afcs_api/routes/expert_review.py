"""Expert review route — dimension scoring with event citations."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as SASession

from afcs_api.db import get_db
from afcs_api.schemas import (
    ExpertDimensionScore,
    ExpertReviewRequest,
    ExpertReviewResponse,
)
from afcs_api.services.session_service import SessionService

router = APIRouter(
    prefix="/api/v1/sessions/{session_id}/evaluation", tags=["expert-review"]
)


@router.post("/expert", response_model=ExpertReviewResponse)
def submit_expert_review(
    session_id: uuid.UUID,
    body: ExpertReviewRequest,
    db: SASession = Depends(get_db),  # noqa: B008
) -> ExpertReviewResponse:
    """Submit an expert review with dimension scores and event citations.

    Expert reviewers assign scores (0-100) for each evaluation dimension,
    provide narrative justification, and cite specific events that support
    their assessment through event IDs.
    """
    service = SessionService(db)
    record = service.get_session(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Validate cited event IDs exist for this session
    if body.dimension_scores:
        all_cited_ids: set[str] = set()
        for ds in body.dimension_scores:
            all_cited_ids.update(ds.cited_event_ids)

        if all_cited_ids:
            existing_events = service.get_events(session_id, from_sequence=0, limit=500)
            existing_ids = {str(e.id) for e in existing_events}
            missing = all_cited_ids - existing_ids
            if missing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cited event IDs not found in session: {', '.join(sorted(missing))}",
                )

    # Summarise each score with event link citations (if summaries not provided)
    enriched_scores = []
    for ds in body.dimension_scores:
        cited_summaries = list(ds.cited_event_summaries)
        if not cited_summaries and ds.cited_event_ids:
            # Fetch summaries from events if not provided
            existing_events = service.get_events(session_id, from_sequence=0, limit=500)
            event_map = {str(e.id): e for e in existing_events}
            for cid in ds.cited_event_ids:
                if cid in event_map:
                    ev = event_map[cid]
                    cited_summaries.append(
                        f"seq {ev.sequence}: {ev.event_type} ({ev.actor_type})"
                    )

        enriched_scores.append(
            ExpertDimensionScore(
                dimension=ds.dimension,
                score=ds.score,
                justification=ds.justification,
                cited_event_ids=ds.cited_event_ids,
                cited_event_summaries=cited_summaries,
                strengths=ds.strengths,
                weaknesses=ds.weaknesses,
            )
        )

    return ExpertReviewResponse(
        session_id=str(session_id),
        dimension_scores=enriched_scores,
        overall_comment=body.overall_comment,
        submitted_at=datetime.now(UTC).isoformat(),
    )
