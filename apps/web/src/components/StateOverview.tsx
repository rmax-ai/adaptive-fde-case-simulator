import { useQuery } from "@tanstack/react-query";
import { getEvents } from "../api/client";
import { getState } from "../api/client";

interface StateOverviewProps {
  sessionId: string;
}

export function StateOverview({ sessionId }: StateOverviewProps) {
  const { data: state, isLoading: stateLoading } = useQuery({
    queryKey: ["sessionState", sessionId],
    queryFn: () => getState(sessionId),
    enabled: !!sessionId,
    refetchInterval: 5000,
  });

  const { data: events } = useQuery({
    queryKey: ["events", sessionId],
    queryFn: () => getEvents(sessionId, undefined, 20),
    enabled: !!sessionId,
  });

  if (stateLoading) {
    return (
      <div className="panel state-overview">
        <h3 className="panel-title">State</h3>
        <p className="loading-text">Loading state...</p>
      </div>
    );
  }

  return (
    <div className="panel state-overview">
      <h3 className="panel-title">State Overview</h3>
      {state && (
        <div className="state-info">
          <div className="state-field">
            <span className="field-label">Step:</span>
            <span className="field-value">{state.current_step}</span>
          </div>
          <div className="state-field">
            <span className="field-label">Status:</span>
            <span className="field-value">{state.status}</span>
          </div>
          <div className="state-field">
            <span className="field-label">Scenario:</span>
            <p className="field-text">{state.scenario_summary}</p>
          </div>
        </div>
      )}

      <h4 className="section-subtitle">Recent Events</h4>
      <div className="event-list">
        {(!events || events.length === 0) ? (
          <p className="empty-text">No events yet.</p>
        ) : (
          events.slice().reverse().map((ev) => (
            <div key={ev.event_id} className="event-item">
              <span className="event-seq">#{ev.sequence}</span>
              <span className="event-type">{ev.event_type}</span>
              <span className="event-actor">{ev.actor}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
