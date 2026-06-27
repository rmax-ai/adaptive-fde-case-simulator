import { useState, useEffect } from "react";
import { getReplayTimeline } from "../api/client";
import type { ReplayTimelineResponse, ReplayEventEntry } from "../types";

interface ReplayTimelineProps {
  sessionId: string;
}

export function ReplayTimeline({ sessionId }: ReplayTimelineProps) {
  const [data, setData] = useState<ReplayTimelineResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeDimension, setActiveDimension] = useState<string | null>(null);
  const [expandedEvent, setExpandedEvent] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    getReplayTimeline(sessionId, activeDimension ?? undefined)
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message || "Failed to load replay timeline");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [sessionId, activeDimension]);

  if (loading) {
    return (
      <div className="replay-timeline">
        <div className="replay-loading">
          <p>Loading replay timeline...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="replay-timeline">
        <div className="replay-error">
          <p>Error: {error}</p>
        </div>
      </div>
    );
  }

  if (!data || data.events.length === 0) {
    return (
      <div className="replay-timeline">
        <div className="replay-empty">
          <p>No events recorded for this session.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="replay-timeline">
      <div className="replay-header">
        <h3>
          Session Timeline
          <span className="event-count">{data.total_events} events</span>
        </h3>
      </div>

      {/* Dimension Filter Pills */}
      <div className="dimension-filters">
        <button
          className={`filter-pill ${activeDimension === null ? "pill-active" : ""}`}
          onClick={() => setActiveDimension(null)}
        >
          All
        </button>
        {data.available_dimensions.map((dim) => (
          <button
            key={dim}
            className={`filter-pill ${activeDimension === dim ? "pill-active" : ""}`}
            onClick={() =>
              setActiveDimension(dim === activeDimension ? null : dim)
            }
          >
            {dim.replace(/_/g, " ")}
          </button>
        ))}
      </div>

      {/* Timeline Events */}
      <div className="timeline-list">
        {data.events.map((entry: ReplayEventEntry, index: number) => {
          const seq = (entry.event?.sequence as number) ?? index;
          const isExpanded = expandedEvent === index;

          return (
            <div
              key={seq}
              className={`timeline-card ${isExpanded ? "card-expanded" : ""}`}
            >
              <div
                className="timeline-card-header"
                onClick={() =>
                  setExpandedEvent(isExpanded ? null : index)
                }
              >
                <span className="event-sequence">#{seq}</span>
                <span className="event-summary">{entry.summary}</span>
                <span className="event-type">{entry.event?.event_type as string}</span>
                <span className="event-actor">{entry.event?.actor_type as string}</span>
                <div className="dimension-tags">
                  {entry.dimensions.map((dim) => (
                    <span key={dim} className="dimension-tag">
                      {dim}
                    </span>
                  ))}
                </div>
                <span className="expand-icon">{isExpanded ? "▲" : "▼"}</span>
              </div>

              {isExpanded && (
                <div className="timeline-card-body">
                  {/* State Diffs */}
                  {entry.state_diff && entry.state_diff.length > 0 && (
                    <div className="state-diffs">
                      <h4>State Changes</h4>
                      <table className="diff-table">
                        <thead>
                          <tr>
                            <th>Path</th>
                            <th>Operation</th>
                            <th>Before</th>
                            <th>After</th>
                          </tr>
                        </thead>
                        <tbody>
                          {entry.state_diff.map((diff, di) => (
                            <tr key={di}>
                              <td className="diff-path">{diff.path}</td>
                              <td>
                                <span className={`op-badge op-${diff.operation}`}>
                                  {diff.operation}
                                </span>
                              </td>
                              <td className="diff-value">
                                {formatValue(diff.old_value)}
                              </td>
                              <td className="diff-value">
                                {formatValue(diff.new_value)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {/* Event Details */}
                  <div className="event-details">
                    <h4>Event Details</h4>
                    <dl className="details-grid">
                      <dt>Event ID</dt>
                      <dd className="mono">
                        {String(entry.event?.event_id ?? "").slice(0, 8)}...
                      </dd>
                      <dt>Type</dt>
                      <dd>{entry.event?.event_type as string}</dd>
                      <dt>Actor</dt>
                      <dd>
                        {entry.event?.actor_type as string}
                        {entry.event?.actor_id
                          ? ` (${entry.event.actor_id as string})`
                          : ""}
                      </dd>
                      <dt>Pre Hash</dt>
                      <dd className="mono">
                        {String(entry.event?.pre_state_hash ?? "").slice(0, 12)}...
                      </dd>
                      <dt>Post Hash</dt>
                      <dd className="mono">
                        {String(entry.event?.post_state_hash ?? "").slice(0, 12)}...
                      </dd>
                    </dl>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "object") {
    try {
      return JSON.stringify(value).slice(0, 80);
    } catch {
      return String(value);
    }
  }
  return String(value).slice(0, 80);
}
