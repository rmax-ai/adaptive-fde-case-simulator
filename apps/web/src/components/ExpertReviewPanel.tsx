import { useState } from "react";
import { submitExpertReview } from "../api/client";
import type { ExpertDimensionScore, ExpertReviewResponse } from "../types";

interface ExpertReviewPanelProps {
  sessionId: string;
  availableDimensions?: string[];
  eventOptions?: Array<{ id: string; summary: string }>;
}

const DEFAULT_DIMENSIONS = [
  "discovery",
  "technical",
  "evaluation_quality",
  "delivery",
  "governance",
  "operational_sustainability",
];

export function ExpertReviewPanel({
  sessionId,
  availableDimensions,
  eventOptions,
}: ExpertReviewPanelProps) {
  const dimensions = availableDimensions ?? DEFAULT_DIMENSIONS;
  const events = eventOptions ?? [];

  const [scores, setScores] = useState<Record<string, number>>(() => {
    const initial: Record<string, number> = {};
    for (const dim of dimensions) {
      initial[dim] = 50;
    }
    return initial;
  });
  const [justifications, setJustifications] = useState<Record<string, string>>(
    {},
  );
  const [citedEvents, setCitedEvents] = useState<Record<string, string[]>>({});
  const [strengths, setStrengths] = useState<Record<string, string[]>>({});
  const [weaknesses, setWeaknesses] = useState<Record<string, string[]>>({});
  const [overallComment, setOverallComment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<ExpertReviewResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeDim, setActiveDim] = useState<string>(dimensions[0] ?? "");

  const handleScoreChange = (dimension: string, value: number) => {
    setScores((prev) => ({ ...prev, [dimension]: Math.max(0, Math.min(100, value)) }));
  };

  const handleJustificationChange = (dimension: string, value: string) => {
    setJustifications((prev) => ({ ...prev, [dimension]: value }));
  };

  const handleCiteEvent = (dimension: string, eventId: string) => {
    setCitedEvents((prev) => {
      const current = prev[dimension] ?? [];
      if (current.includes(eventId)) {
        return {
          ...prev,
          [dimension]: current.filter((id) => id !== eventId),
        };
      }
      return { ...prev, [dimension]: [...current, eventId] };
    });
  };

  const handleAddStrength = (dimension: string) => {
    const text = prompt("Enter strength:");
    if (text && text.trim()) {
      setStrengths((prev) => ({
        ...prev,
        [dimension]: [...(prev[dimension] ?? []), text.trim()],
      }));
    }
  };

  const handleAddWeakness = (dimension: string) => {
    const text = prompt("Enter weakness:");
    if (text && text.trim()) {
      setWeaknesses((prev) => ({
        ...prev,
        [dimension]: [...(prev[dimension] ?? []), text.trim()],
      }));
    }
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    setError(null);

    const dimensionScores: ExpertDimensionScore[] = dimensions.map((dim) => ({
      dimension: dim,
      score: scores[dim] ?? 50,
      justification: justifications[dim] ?? "",
      cited_event_ids: citedEvents[dim] ?? [],
      cited_event_summaries: (citedEvents[dim] ?? []).map((eid) => {
        const ev = events.find((e) => e.id === eid);
        return ev ? ev.summary : eid;
      }),
      strengths: strengths[dim] ?? [],
      weaknesses: weaknesses[dim] ?? [],
    }));

    try {
      const response = await submitExpertReview(sessionId, {
        dimension_scores: dimensionScores,
        overall_comment: overallComment,
      });
      setResult(response);
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Failed to submit expert review",
      );
    } finally {
      setSubmitting(false);
    }
  };

  // Submitted state
  if (result) {
    return (
      <div className="expert-review-panel">
        <div className="expert-review-submitted">
          <h3>Expert Review Submitted</h3>
          <p className="submitted-at">
            Submitted at: {result.submitted_at}
          </p>
          {result.overall_comment && (
            <div className="overall-comment">
              <strong>Overall Comment:</strong>
              <p>{result.overall_comment}</p>
            </div>
          )}
          <div className="submitted-scores">
            <h4>Dimension Scores</h4>
            {result.dimension_scores.map((ds) => (
              <div key={ds.dimension} className="submitted-score-card">
                <div className="score-header">
                  <span className="dim-label">{ds.dimension}</span>
                  <span className="dim-score">{Math.round(ds.score)}/100</span>
                </div>
                <div className="score-bar">
                  <div
                    className="score-fill"
                    style={{
                      width: `${ds.score}%`,
                      backgroundColor:
                        ds.score >= 70
                          ? "#22c55e"
                          : ds.score >= 40
                            ? "#eab308"
                            : "#ef4444",
                    }}
                  />
                </div>
                {ds.justification && <p className="justification">{ds.justification}</p>}
                {ds.cited_event_ids.length > 0 && (
                  <div className="cited-events">
                    <strong>Cited Events:</strong>
                    <ul>
                      {ds.cited_event_summaries.map((s, i) => (
                        <li key={i}>{s}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {ds.strengths.length > 0 && (
                  <div className="dim-strengths">
                    <strong>Strengths:</strong>
                    <ul>
                      {ds.strengths.map((s, i) => (
                        <li key={i}>{s}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {ds.weaknesses.length > 0 && (
                  <div className="dim-weaknesses">
                    <strong>Weaknesses:</strong>
                    <ul>
                      {ds.weaknesses.map((w, i) => (
                        <li key={i}>{w}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="expert-review-panel">
      <h3>Expert Review Panel</h3>
      <p className="panel-subtitle">
        Score each dimension (0-100) and cite supporting events
      </p>

      {error && (
        <div className="panel-error">
          <p>Error: {error}</p>
        </div>
      )}

      {/* Dimension Navigation */}
      <div className="dimension-nav">
        {dimensions.map((dim) => (
          <button
            key={dim}
            className={`dim-nav-btn ${activeDim === dim ? "nav-active" : ""}`}
            onClick={() => setActiveDim(dim)}
          >
            {dim.replace(/_/g, " ")}
            <span className="nav-score">{Math.round(scores[dim] ?? 50)}</span>
          </button>
        ))}
      </div>

      {/* Active Dimension Editor */}
      <div className="dimension-editor">
        <div className="editor-header">
          <h4>{activeDim.replace(/_/g, " ")}</h4>
          <div className="score-input-group">
            <label>Score (0-100):</label>
            <input
              type="range"
              min={0}
              max={100}
              value={scores[activeDim] ?? 50}
              onChange={(e) =>
                handleScoreChange(activeDim, Number(e.target.value))
              }
              className="score-slider"
            />
            <input
              type="number"
              min={0}
              max={100}
              value={scores[activeDim] ?? 50}
              onChange={(e) =>
                handleScoreChange(activeDim, Number(e.target.value))
              }
              className="score-input"
            />
          </div>
        </div>

        {/* Score Bar Preview */}
        <div className="score-bar preview-bar">
          <div
            className="score-fill"
            style={{
              width: `${scores[activeDim] ?? 50}%`,
              backgroundColor:
                (scores[activeDim] ?? 50) >= 70
                  ? "#22c55e"
                  : (scores[activeDim] ?? 50) >= 40
                    ? "#eab308"
                    : "#ef4444",
            }}
          />
        </div>

        {/* Justification */}
        <div className="editor-field">
          <label>Justification:</label>
          <textarea
            value={justifications[activeDim] ?? ""}
            onChange={(e) =>
              handleJustificationChange(activeDim, e.target.value)
            }
            placeholder="Explain your reasoning for this score..."
            rows={3}
          />
        </div>

        {/* Event Citations */}
        {events.length > 0 && (
          <div className="editor-field">
            <label>Cite Supporting Events:</label>
            <div className="event-citation-list">
              {events.map((ev) => {
                const isCited = (citedEvents[activeDim] ?? []).includes(ev.id);
                return (
                  <button
                    key={ev.id}
                    className={`citation-btn ${isCited ? "cited" : ""}`}
                    onClick={() => handleCiteEvent(activeDim, ev.id)}
                  >
                    <span className="citation-check">
                      {isCited ? "✓" : "○"}
                    </span>
                    <span className="citation-summary">{ev.summary}</span>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Strengths / Weaknesses */}
        <div className="editor-lists">
          <div className="list-section">
            <div className="list-header">
              <strong>Strengths</strong>
              <button
                className="btn-add"
                onClick={() => handleAddStrength(activeDim)}
              >
                +
              </button>
            </div>
            <ul className="strength-list">
              {(strengths[activeDim] ?? []).map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ul>
          </div>
          <div className="list-section">
            <div className="list-header">
              <strong>Weaknesses</strong>
              <button
                className="btn-add"
                onClick={() => handleAddWeakness(activeDim)}
              >
                +
              </button>
            </div>
            <ul className="weakness-list">
              {(weaknesses[activeDim] ?? []).map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      {/* Overall Comment */}
      <div className="overall-comment-editor">
        <label>Overall Comment:</label>
        <textarea
          value={overallComment}
          onChange={(e) => setOverallComment(e.target.value)}
          placeholder="Summarise your overall assessment of this session..."
          rows={4}
        />
      </div>

      {/* Submit */}
      <button
        className="btn-primary btn-submit-review"
        onClick={handleSubmit}
        disabled={submitting}
      >
        {submitting ? "Submitting..." : "Submit Expert Review"}
      </button>
    </div>
  );
}
