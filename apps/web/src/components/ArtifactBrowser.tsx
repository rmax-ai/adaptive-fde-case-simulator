import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getArtifacts, getArtifact } from "../api/client";
import type { Artifact } from "../types";

interface ArtifactBrowserProps {
  sessionId: string;
}

export function ArtifactBrowser({ sessionId }: ArtifactBrowserProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data: artifacts, isLoading } = useQuery({
    queryKey: ["artifacts", sessionId],
    queryFn: () => getArtifacts(sessionId),
    enabled: !!sessionId,
  });

  const { data: selectedArtifact } = useQuery({
    queryKey: ["artifact", sessionId, selectedId],
    queryFn: () => getArtifact(sessionId, selectedId!),
    enabled: !!selectedId,
  });

  if (isLoading) {
    return (
      <div className="panel artifact-browser">
        <h3 className="panel-title">Artifacts</h3>
        <p className="loading-text">Loading artifacts...</p>
      </div>
    );
  }

  return (
    <div className="panel artifact-browser">
      <h3 className="panel-title">Artifacts</h3>
      {(!artifacts || artifacts.length === 0) ? (
        <p className="empty-text">No artifacts yet.</p>
      ) : (
        <ul className="artifact-list">
          {artifacts.map((a: Artifact) => (
            <li key={a.artifact_id}>
              <button
                className={`artifact-item ${selectedId === a.artifact_id ? "active" : ""}`}
                onClick={() => setSelectedId(a.artifact_id)}
              >
                <span className="artifact-name">{a.name}</span>
                <span className="artifact-type">{a.artifact_type}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {selectedArtifact && (
        <div className="artifact-detail">
          <h4 className="artifact-detail-title">{selectedArtifact.name}</h4>
          <pre className="artifact-content">{selectedArtifact.content}</pre>
        </div>
      )}
    </div>
  );
}
