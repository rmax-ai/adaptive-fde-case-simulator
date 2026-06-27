import { ActionLauncher } from "./ActionLauncher";
import { ArtifactBrowser } from "./ArtifactBrowser";
import { StateOverview } from "./StateOverview";
import { RegisterPanel } from "./RegisterPanel";
import { StakeholderChat } from "./StakeholderChat";
import { useSession } from "../hooks/useSession";
import { useActions } from "../hooks/useActions";
import type { ActionParams } from "../types";

interface SessionWorkspaceProps {
  sessionId: string;
  onBack: () => void;
}

export function SessionWorkspace({ sessionId, onBack }: SessionWorkspaceProps) {
  const { session, state, isLoading, error } = useSession(sessionId);
  const { actions, execute, isExecuting } = useActions(sessionId);

  if (isLoading) {
    return (
      <div className="workspace-loading">
        <p>Loading session workspace...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="workspace-error">
        <p>Error loading session: {String(error)}</p>
        <button className="btn-secondary" onClick={onBack}>
          Back to Launcher
        </button>
      </div>
    );
  }

  const handleExecuteAction = (actionType: string, params: ActionParams) => {
    execute({ actionType, params });
  };

  return (
    <div className="session-workspace">
      <header className="workspace-header">
        <button className="btn-back" onClick={onBack}>
          &larr; Back
        </button>
        <div className="workspace-title">
          <h2>Case: {state?.case_id ?? session?.case_id ?? "?"}</h2>
          <span className="session-id">Session: {sessionId.slice(0, 8)}...</span>
        </div>
        <span className={`status-badge status-${state?.status ?? "active"}`}>
          {state?.status ?? "unknown"}
        </span>
      </header>

      <div className="workspace-layout">
        <aside className="workspace-left">
          <ArtifactBrowser sessionId={sessionId} />
          <StakeholderChat sessionId={sessionId} />
        </aside>

        <main className="workspace-center">
          <StateOverview sessionId={sessionId} />
          <ActionLauncher
            actions={actions}
            onExecute={handleExecuteAction}
            isExecuting={isExecuting}
          />
        </main>

        <aside className="workspace-right">
          <RegisterPanel sessionId={sessionId} type="assumptions" />
          <RegisterPanel sessionId={sessionId} type="risks" />
        </aside>
      </div>
    </div>
  );
}
