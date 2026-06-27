import { useQuery } from "@tanstack/react-query";
import { getState } from "../api/client";

interface RegisterPanelProps {
  sessionId: string;
  type: "assumptions" | "risks";
}

export function RegisterPanel({ sessionId, type }: RegisterPanelProps) {
  const { data: state, isLoading } = useQuery({
    queryKey: ["sessionState", sessionId],
    queryFn: () => getState(sessionId),
    enabled: !!sessionId,
    refetchInterval: 5000,
  });

  const entries = type === "assumptions"
    ? state?.registers.assumptions ?? []
    : state?.registers.risks ?? [];

  const title = type === "assumptions" ? "Assumptions" : "Risks";

  if (isLoading) {
    return (
      <div className="panel register-panel">
        <h3 className="panel-title">{title}</h3>
        <p className="loading-text">Loading...</p>
      </div>
    );
  }

  const severityColor = (severity?: string) => {
    switch (severity) {
      case "critical": return "sev-critical";
      case "high": return "sev-high";
      case "medium": return "sev-medium";
      case "low": return "sev-low";
      default: return "";
    }
  };

  return (
    <div className="panel register-panel">
      <h3 className="panel-title">{title}</h3>
      {entries.length === 0 ? (
        <p className="empty-text">No {type.toLowerCase()} registered.</p>
      ) : (
        <ul className="register-list">
          {entries.map((entry) => (
            <li key={entry.id} className="register-entry">
              <div className="register-entry-header">
                <span className={`severity-badge ${severityColor(entry.severity)}`}>
                  {entry.severity ?? "info"}
                </span>
                <span className={`status-badge status-${entry.status}`}>
                  {entry.status}
                </span>
              </div>
              <p className="register-entry-desc">{entry.description}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
