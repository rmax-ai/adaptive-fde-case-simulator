import { useState, useCallback, useRef, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getStakeholders, sendStakeholderMessage } from "../api/client";
import type {
  StakeholderInfo,
  TrustSignal,
  MessageEntry,
} from "../types";

interface StakeholderChatProps {
  sessionId: string;
}

// ── Trust signal badge colors ─────────────────────────────────────────

const TRUST_COLORS: Record<TrustSignal, string> = {
  cooperative: "trust-cooperative",
  hesitant: "trust-hesitant",
  blocked: "trust-blocked",
  escalating: "trust-escalating",
  awaiting_evidence: "trust-awaiting",
};

const TRUST_LABELS: Record<TrustSignal, string> = {
  cooperative: "Cooperative",
  hesitant: "Hesitant",
  blocked: "Blocked",
  escalating: "Escalating",
  awaiting_evidence: "Awaiting Evidence",
};

// ── Component ─────────────────────────────────────────────────────────

export function StakeholderChat({ sessionId }: StakeholderChatProps) {
  const queryClient = useQueryClient();
  const [selectedStakeholder, setSelectedStakeholder] =
    useState<StakeholderInfo | null>(null);
  const [inputText, setInputText] = useState("");

  // Persisted conversations keyed by stakeholder id
  const [conversations, setConversations] = useState<
    Record<string, MessageEntry[]>
  >({});

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Fetch stakeholders
  const { data: stakeholdersData, isLoading: loadingStakeholders } = useQuery({
    queryKey: ["stakeholders", sessionId],
    queryFn: () => getStakeholders(sessionId),
    enabled: !!sessionId,
    refetchInterval: 5000,
  });

  const stakeholders = stakeholdersData?.stakeholders ?? [];

  // Send message mutation
  const sendMutation = useMutation({
    mutationFn: ({
      stakeholderId,
      message,
    }: {
      stakeholderId: string;
      message: string;
    }) => sendStakeholderMessage(sessionId, stakeholderId, message),
    onSuccess: (data) => {
      // Add response to conversation
      setConversations((prev) => {
        const stakeholderId = data.stakeholder_id;
        const existing = prev[stakeholderId] ?? [];
        return {
          ...prev,
          [stakeholderId]: [
            ...existing,
            {
              id: `response-${Date.now()}`,
              fromParticipant: false,
              text: data.message,
              tone: data.tone,
              timestamp: new Date().toISOString(),
            },
          ],
        };
      });
      // Refresh stakeholders to get updated trust signals
      queryClient.invalidateQueries({
        queryKey: ["stakeholders", sessionId],
      });
    },
  });

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [conversations]);

  const handleSend = useCallback(() => {
    const text = inputText.trim();
    if (!text || !selectedStakeholder || sendMutation.isPending) return;

    // Add participant message
    setConversations((prev) => {
      const stakeholderId = selectedStakeholder.id;
      const existing = prev[stakeholderId] ?? [];
      return {
        ...prev,
        [stakeholderId]: [
          ...existing,
          {
            id: `msg-${Date.now()}`,
            fromParticipant: true,
            text,
            timestamp: new Date().toISOString(),
          },
        ],
      };
    });

    setInputText("");
    sendMutation.mutate({
      stakeholderId: selectedStakeholder.id,
      message: text,
    });
  }, [inputText, selectedStakeholder, sendMutation]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const selectStakeholder = (s: StakeholderInfo) => {
    setSelectedStakeholder(s);
  };

  const currentMessages = selectedStakeholder
    ? conversations[selectedStakeholder.id] ?? []
    : [];

  // ── Render ─────────────────────────────────────────────────

  if (loadingStakeholders) {
    return (
      <div className="panel stakeholder-chat">
        <h3 className="panel-title">Stakeholders</h3>
        <p className="loading-text">Loading stakeholders...</p>
      </div>
    );
  }

  return (
    <div className="workspace-stakeholder-layout">
      {/* Left: stakeholder list */}
      <aside className="stakeholder-list-panel">
        <h3 className="panel-title">Stakeholders</h3>
        {stakeholders.length === 0 ? (
          <p className="empty-text">No stakeholders available.</p>
        ) : (
          <ul className="stakeholder-list">
            {stakeholders.map((s) => (
              <li key={s.id}>
                <button
                  className={`stakeholder-item ${
                    selectedStakeholder?.id === s.id ? "active" : ""
                  }`}
                  onClick={() => selectStakeholder(s)}
                >
                  <span className="stakeholder-name">{s.role}</span>
                  <span
                    className={`trust-badge ${
                      TRUST_COLORS[s.trust_signal] ?? ""
                    }`}
                  >
                    {TRUST_LABELS[s.trust_signal] ?? s.trust_signal}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </aside>

      {/* Right: conversation view */}
      <main className="stakeholder-conversation-panel">
        {selectedStakeholder ? (
          <>
            <header className="conversation-header">
              <h4>{selectedStakeholder.role}</h4>
              <span
                className={`trust-badge ${
                  TRUST_COLORS[selectedStakeholder.trust_signal] ?? ""
                }`}
              >
                {TRUST_LABELS[selectedStakeholder.trust_signal] ??
                  selectedStakeholder.trust_signal}
              </span>
            </header>

            <div className="conversation-messages">
              {currentMessages.length === 0 ? (
                <p className="empty-text">
                  Start a conversation with {selectedStakeholder.role}.
                </p>
              ) : (
                currentMessages.map((entry) => (
                  <div
                    key={entry.id}
                    className={`message-bubble ${
                      entry.fromParticipant
                        ? "message-participant"
                        : "message-stakeholder"
                    }`}
                  >
                    {!entry.fromParticipant && entry.tone && (
                      <span className="message-tone-badge">{entry.tone}</span>
                    )}
                    <p className="message-text">{entry.text}</p>
                  </div>
                ))
              )}
              <div ref={messagesEndRef} />
            </div>

            <div className="conversation-input">
              <textarea
                className="message-input"
                placeholder={`Message ${selectedStakeholder.role}...`}
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={handleKeyDown}
                rows={2}
                disabled={sendMutation.isPending}
              />
              <button
                className="btn-send"
                onClick={handleSend}
                disabled={!inputText.trim() || sendMutation.isPending}
              >
                {sendMutation.isPending ? "..." : "Send"}
              </button>
            </div>
          </>
        ) : (
          <div className="conversation-empty-state">
            <p>Select a stakeholder from the list to start a conversation.</p>
          </div>
        )}
      </main>
    </div>
  );
}
