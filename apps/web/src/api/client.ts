import type {
  Session,
  VisibleState,
  ActionSchema,
  SimulationEvent,
  Artifact,
  ActionParams,
  StakeholderInfo,
  StakeholderMessageResponse,
  EvaluationResponse,
  ReportResponse,
} from "../types";

const BASE_URL = "/api/v1";

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const headers: Record<string, string> = {
    Accept: "application/json",
  };
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  const res = await fetch(url, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new ApiError(
      `API ${method} ${path} returned ${res.status}: ${text}`,
      res.status,
    );
  }
  return (await res.json()) as T;
}

// ─── Session API ─────────────────────────────────────────────

export function createSession(
  caseId: string,
  participantId?: string,
): Promise<Session> {
  return request<Session>("POST", "/sessions", {
    case_id: caseId,
    participant_id: participantId,
  });
}

export function getSession(sessionId: string): Promise<Session> {
  return request<Session>("GET", `/sessions/${sessionId}`);
}

// ─── State API ───────────────────────────────────────────────

export function getState(sessionId: string): Promise<VisibleState> {
  return request<VisibleState>("GET", `/sessions/${sessionId}/state`);
}

// ─── Action API ──────────────────────────────────────────────

export function getAvailableActions(
  sessionId: string,
): Promise<ActionSchema[]> {
  return request<ActionSchema[]>(
    "GET",
    `/sessions/${sessionId}/actions`,
  );
}

export function executeAction(
  sessionId: string,
  actionType: string,
  params: ActionParams,
): Promise<SimulationEvent> {
  return request<SimulationEvent>("POST", `/sessions/${sessionId}/actions`, {
    action_type: actionType,
    params,
  });
}

// ─── Event API ───────────────────────────────────────────────

export function getEvents(
  sessionId: string,
  fromSequence?: number,
  limit?: number,
): Promise<SimulationEvent[]> {
  const params = new URLSearchParams();
  if (fromSequence !== undefined) params.set("from_sequence", String(fromSequence));
  if (limit !== undefined) params.set("limit", String(limit));
  const qs = params.toString();
  return request<SimulationEvent[]>(
    "GET",
    `/sessions/${sessionId}/events${qs ? `?${qs}` : ""}`,
  );
}

// ─── Artifact API ────────────────────────────────────────────

export function getArtifacts(sessionId: string): Promise<Artifact[]> {
  return request<Artifact[]>("GET", `/sessions/${sessionId}/artifacts`);
}

export function getArtifact(
  sessionId: string,
  artifactId: string,
): Promise<Artifact> {
  return request<Artifact>(
    "GET",
    `/sessions/${sessionId}/artifacts/${artifactId}`,
  );
}

// ─── Recommendation API ──────────────────────────────────────

export function submitFinalRecommendation(
  sessionId: string,
  recommendation: string,
): Promise<SimulationEvent> {
  return request<SimulationEvent>(
    "POST",
    `/sessions/${sessionId}/recommendation`,
    { recommendation },
  );
}

// ─── Evaluation & Report API ──────────────────────────────────

export function getEvaluation(sessionId: string): Promise<EvaluationResponse> {
  return request<EvaluationResponse>(
    "GET",
    `/sessions/${sessionId}/evaluation`,
  );
}

export function getReport(sessionId: string): Promise<ReportResponse> {
  return request<ReportResponse>(
    "GET",
    `/sessions/${sessionId}/report`,
  );
}

// ─── Stakeholder API ─────────────────────────────────────────

export function getStakeholders(
  sessionId: string,
): Promise<{ stakeholders: StakeholderInfo[] }> {
  return request<{ stakeholders: StakeholderInfo[] }>(
    "GET",
    `/sessions/${sessionId}/stakeholders`,
  );
}

export function sendStakeholderMessage(
  sessionId: string,
  stakeholderId: string,
  message: string,
): Promise<StakeholderMessageResponse> {
  return request<StakeholderMessageResponse>(
    "POST",
    `/sessions/${sessionId}/stakeholders/${stakeholderId}/messages`,
    { message },
  );
}
