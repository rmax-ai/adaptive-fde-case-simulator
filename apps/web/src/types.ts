// ─── Session ────────────────────────────────────────────────
export interface Session {
  session_id: string;
  case_id: string;
  participant_id: string | null;
  status: "active" | "completed" | "terminated";
  current_step: string;
  created_at: string;
  updated_at: string;
}

// ─── Visible State ───────────────────────────────────────────
export interface VisibleState {
  session_id: string;
  case_id: string;
  current_step: string;
  scenario_summary: string;
  status: string;
  visible_resources: Record<string, unknown>;
  registers: Registers;
  timestamp: string;
}

export interface Registers {
  assumptions: RegisterEntry[];
  risks: RegisterEntry[];
}

export interface RegisterEntry {
  id: string;
  description: string;
  severity?: "low" | "medium" | "high" | "critical";
  status: "open" | "resolved" | "mitigated";
  created_at: string;
}

// ─── Actions ─────────────────────────────────────────────────
export interface ActionSchema {
  action_type: string;
  label: string;
  description: string;
  params: ActionParam[];
  preconditions: string[];
}

export interface ActionParam {
  name: string;
  type: "string" | "number" | "boolean" | "select";
  label: string;
  required: boolean;
  options?: string[];
}

export interface ActionParams {
  [key: string]: string | number | boolean;
}

// ─── Events ──────────────────────────────────────────────────
export interface SimulationEvent {
  event_id: string;
  session_id: string;
  sequence: number;
  event_type: string;
  actor: string;
  action_type: string | null;
  payload: Record<string, unknown>;
  visible: boolean;
  timestamp: string;
}

// ─── Artifacts ───────────────────────────────────────────────
export interface Artifact {
  artifact_id: string;
  session_id: string;
  name: string;
  artifact_type: string;
  content: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

// ─── Stakeholders ───────────────────────────────────────────
export type TrustSignal =
  | "cooperative"
  | "hesitant"
  | "blocked"
  | "escalating"
  | "awaiting_evidence";

export interface StakeholderInfo {
  id: string;
  role: string;
  trust_signal: TrustSignal;
}

export interface StakeholderMessageRequest {
  message: string;
}

export interface StakeholderMessageResponse {
  stakeholder_id: string;
  message: string;
  tone: string;
  disclosed_fact_ids: string[];
}

export interface StakeholderConversation {
  stakeholder: StakeholderInfo;
  messages: MessageEntry[];
}

export interface MessageEntry {
  id: string;
  fromParticipant: boolean;
  text: string;
  tone?: string;
  timestamp: string;
}
