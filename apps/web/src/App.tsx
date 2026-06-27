import { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SessionWorkspace } from "./components/SessionWorkspace";
import { createSession } from "./api/client";

const queryClient = new QueryClient();

const CASE_OPTIONS = [
  { id: "security-posture-review", label: "Security Posture Review" },
  { id: "migration-assessment", label: "Migration Assessment" },
  { id: "incident-response", label: "Incident Response" },
];

function LauncherForm({
  onSessionCreated,
}: {
  onSessionCreated: (id: string) => void;
}) {
  const [caseId, setCaseId] = useState(CASE_OPTIONS[0]!.id);
  const [participantId, setParticipantId] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsCreating(true);
    setError(null);
    try {
      const session = await createSession(caseId, participantId || undefined);
      onSessionCreated(session.session_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create session");
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="launcher">
      <div className="launcher-card">
        <h1 className="launcher-title">AFCS</h1>
        <p className="launcher-subtitle">
          Adaptive Forward Deployed Engineer Case Simulator
        </p>

        <form className="launcher-form" onSubmit={handleCreate}>
          <div className="form-group">
            <label htmlFor="case-select">Case</label>
            <select
              id="case-select"
              value={caseId}
              onChange={(e) => setCaseId(e.target.value)}
            >
              {CASE_OPTIONS.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="participant-id">
              Participant ID <span className="optional">(optional)</span>
            </label>
            <input
              id="participant-id"
              type="text"
              value={participantId}
              onChange={(e) => setParticipantId(e.target.value)}
              placeholder="e.g., engineer-01"
            />
          </div>

          {error && <p className="error-message">{error}</p>}

          <button
            type="submit"
            className="btn-primary"
            disabled={isCreating}
          >
            {isCreating ? "Creating..." : "Start Simulation"}
          </button>
        </form>
      </div>
    </div>
  );
}

function AppInner() {
  const [sessionId, setSessionId] = useState<string | null>(null);

  if (sessionId) {
    return (
      <SessionWorkspace
        sessionId={sessionId}
        onBack={() => setSessionId(null)}
      />
    );
  }

  return <LauncherForm onSessionCreated={setSessionId} />;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppInner />
    </QueryClientProvider>
  );
}
