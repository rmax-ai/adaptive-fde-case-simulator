import { useState, useEffect } from "react";
import {
  getEvaluation,
  getReport,
} from "../api/client";
import type { EvaluationResponse, ReportResponse } from "../types";

interface EvaluationReportProps {
  sessionId: string;
  onBack: () => void;
}

export function EvaluationReport({ sessionId, onBack }: EvaluationReportProps) {
  const [evaluation, setEvaluation] = useState<EvaluationResponse | null>(null);
  const [report, setReport] = useState<ReportResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"evaluation" | "timeline" | "details">("evaluation");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    Promise.all([
      getEvaluation(sessionId).catch((e: Error) => {
        console.warn("Failed to fetch evaluation:", e);
        return null;
      }),
      getReport(sessionId).catch((e: Error) => {
        console.warn("Failed to fetch report:", e);
        return null;
      }),
    ])
      .then(([evalData, reportData]) => {
        if (cancelled) return;
        setEvaluation(evalData);
        setReport(reportData);
      })
      .catch((err: Error) => {
        if (cancelled) return;
        setError(err.message || "Failed to load report");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  if (loading) {
    return (
      <div className="evaluation-report">
        <div className="report-loading">
          <p>Loading evaluation report...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="evaluation-report">
        <div className="report-error">
          <p>Error: {error}</p>
          <button className="btn-secondary" onClick={onBack}>
            Back to Session
          </button>
        </div>
      </div>
    );
  }

  const evalData = evaluation ?? report?.evaluation;

  return (
    <div className="evaluation-report">
      <header className="report-header">
        <button className="btn-back" onClick={onBack}>
          &larr; Back to Session
        </button>
        <h2>Engagement Report</h2>
        {report && (
          <div className="report-meta">
            <span>Case: {report.case_id} v{report.case_version}</span>
            {report.participant_id && <span>Participant: {report.participant_id}</span>}
            <span>Status: <strong className={`status-${report.status}`}>{report.status}</strong></span>
          </div>
        )}
      </header>

      <nav className="report-tabs">
        <button
          className={`tab-btn ${activeTab === "evaluation" ? "tab-active" : ""}`}
          onClick={() => setActiveTab("evaluation")}
        >
          Evaluation
        </button>
        <button
          className={`tab-btn ${activeTab === "timeline" ? "tab-active" : ""}`}
          onClick={() => setActiveTab("timeline")}
        >
          Timeline
        </button>
        <button
          className={`tab-btn ${activeTab === "details" ? "tab-active" : ""}`}
          onClick={() => setActiveTab("details")}
        >
          Details
        </button>
      </nav>

      <div className="report-content">
        {activeTab === "evaluation" && evalData && (
          <div className="evaluation-section">
            {/* Overall Score */}
            <div className="score-card">
              <div className="overall-score">
                <span className="score-value">{Math.round(evalData.overall_score)}</span>
                <span className="score-label">Overall Score</span>
              </div>
              <div className="score-bar">
                <div
                  className="score-fill"
                  style={{
                    width: `${Math.min(evalData.overall_score, 100)}%`,
                    backgroundColor:
                      evalData.overall_score >= 70
                        ? "#22c55e"
                        : evalData.overall_score >= 40
                          ? "#eab308"
                          : "#ef4444",
                  }}
                />
              </div>
            </div>

            {/* Dimension Breakdown */}
            {evalData.dimensions.length > 0 && (
              <div className="dimensions-section">
                <h3>Dimension Breakdown</h3>
                <div className="dimension-list">
                  {evalData.dimensions.map((dim) => (
                    <div key={dim.name} className="dimension-item">
                      <div className="dimension-header">
                        <span className="dimension-name">{dim.name}</span>
                        <span className="dimension-score">
                          {Math.round(dim.score)} / {Math.round(dim.max_score)}
                        </span>
                      </div>
                      <div className="score-bar bar-sm">
                        <div
                          className="score-fill"
                          style={{
                            width: `${(dim.score / dim.max_score) * 100}%`,
                            backgroundColor:
                              dim.score >= 70
                                ? "#22c55e"
                                : dim.score >= 40
                                  ? "#eab308"
                                  : "#ef4444",
                          }}
                        />
                      </div>
                      {dim.findings.length > 0 && (
                        <div className="findings">
                          <strong>Findings:</strong>
                          <ul>
                            {dim.findings.map((f, i) => (
                              <li key={i}>{f}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {dim.missed_evidence.length > 0 && (
                        <div className="missed-evidence">
                          <strong>Missed evidence:</strong>
                          <ul>
                            {dim.missed_evidence.map((m, i) => (
                              <li key={i}>{m}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Strongest / Weakest Behaviors */}
            {evalData.strongest_behaviors.length > 0 && (
              <div className="behaviors-section">
                <h3>Strongest Behaviors</h3>
                <ul className="behavior-list strong">
                  {evalData.strongest_behaviors.map((b) => (
                    <li key={b}>{b}</li>
                  ))}
                </ul>
              </div>
            )}
            {evalData.weakest_behaviors.length > 0 && (
              <div className="behaviors-section">
                <h3>Areas for Improvement</h3>
                <ul className="behavior-list weak">
                  {evalData.weakest_behaviors.map((b) => (
                    <li key={b}>{b}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Hard Constraint Violations */}
            {evalData.hard_constraint_violations.length > 0 && (
              <div className="constraints-section">
                <h3>Hard Constraints</h3>
                <table className="constraints-table">
                  <thead>
                    <tr>
                      <th>Type</th>
                      <th>Severity</th>
                      <th>Status</th>
                      <th>Details</th>
                    </tr>
                  </thead>
                  <tbody>
                    {evalData.hard_constraint_violations.map((c, i) => (
                      <tr key={i} className={c.passed ? "constraint-pass" : "constraint-fail"}>
                        <td>{c.constraint_type}</td>
                        <td>{c.severity}</td>
                        <td>{c.passed ? "✅ Passed" : "❌ Failed"}</td>
                        <td>{c.details ?? c.description ?? ""}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Missed Evidence */}
            {evalData.missed_evidence.length > 0 && (
              <div className="missed-section">
                <h3>Missed Evidence</h3>
                <ul className="missed-list">
                  {evalData.missed_evidence.map((m, i) => (
                    <li key={i}>{m}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {activeTab === "timeline" && report && (
          <div className="timeline-section">
            <h3>Session Timeline</h3>
            {report.timeline.length === 0 ? (
              <p className="empty-state">No events recorded.</p>
            ) : (
              <div className="timeline-list">
                {report.timeline.map((entry, i) => (
                  <div key={i} className="timeline-entry">
                    <span className="timeline-seq">#{String(entry.sequence ?? i)}</span>
                    <span className="timeline-type">{String(entry.event_type ?? "")}</span>
                    <span className="timeline-actor">{String(entry.actor_type ?? "")}</span>
                    <span className="timeline-summary">
                      {String(entry.summary ?? "").slice(0, 120)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === "details" && report && (
          <div className="details-section">
            <div className="detail-card">
              <h3>Final Recommendation</h3>
              {report.recommendation && Object.keys(report.recommendation).length > 0 ? (
                <div className="recommendation-content">
                  {((): React.ReactNode => {
                    const rec = report.recommendation as Record<string, unknown>;
                    return (
                      <>
                        <p><strong>Summary:</strong> {String(rec.summary ?? "N/A")}</p>
                        <p><strong>Recommendation:</strong> {String(rec.recommendation ?? "N/A")}</p>
                        {rec.justification ? (
                          <p><strong>Justification:</strong> {String(rec.justification)}</p>
                        ) : null}
                        {rec.next_steps && Array.isArray(rec.next_steps) ? (
                          <div>
                            <strong>Next Steps:</strong>
                            <ul>
                              {(rec.next_steps as string[]).map((step, i) => (
                                <li key={i}>{step}</li>
                              ))}
                            </ul>
                          </div>
                        ) : null}
                      </>
                    );
                  })()}
                </div>
              ) : (
                <p className="empty-state">No final recommendation submitted.</p>
              )}
            </div>

            <div className="detail-card">
              <h3>Artifacts Inspected</h3>
              {report.artifacts_inspected.length === 0 ? (
                <p className="empty-state">No artifacts inspected.</p>
              ) : (
                <ul>
                  {report.artifacts_inspected.map((a, i) => (
                    <li key={i}>{a}</li>
                  ))}
                </ul>
              )}
            </div>

            <div className="detail-card">
              <h3>Stakeholder Interactions</h3>
              {report.stakeholder_interactions.length === 0 ? (
                <p className="empty-state">No stakeholder interactions recorded.</p>
              ) : (
                <ul>
                  {report.stakeholder_interactions.map((s, i) => (
                    <li key={i}>{JSON.stringify(s).slice(0, 150)}</li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
