export type AppPage =
  | "dashboard"
  | "chat"
  | "leave"
  | "requests"
  | "documents"
  | "audit"
  | "settings"
  | "manager"
  | "admin";

export type UserRole =
  | "admin"
  | "manager"
  | "employee";
export type MessageRole = "user" | "assistant";

export type Message = {
  id: number;
  role: MessageRole;
  content: string;
  source?: string;
  category?: string;
  created_at?: string;
};

export type Conversation = {
  id: number;
  title: string;
  messages: Message[];
  created_at?: string;
  updated_at?: string;
  message_count?: number;
};

export type ChatApiResponse = {
  answer: string;
  tools_used?: string[];
  conversation_id: number;
};

export type LeaveRequest = {
  employe_id: string;
  date_debut: string;
  date_fin: string;
  type_conge:
    | "conge_annuel"
    | "conge_maladie"
    | "conge_maternite"
    | "conge_paternite"
    | "conge_sans_solde"
    | "conge_formation"
    | "autre";
  motif: string;
};

export type LeaveApiResponse = {
  statut: string;
  message: string;
  demande_id: string;
};
export type LeaveRequestRecord = {
  demande_id: string;
  employe_id: string;
  type_conge: string;
  date_debut: string;
  date_fin: string;
  motif: string;
  statut: LeaveRequestStatus;
  message: string;
  created_at: string;
};

export type LeaveRequestStatus =
  | "pending"
  | "accepted"
  | "rejected";

export type ManagerLeaveRequest = LeaveRequestRecord & {
  user_uid: string;
  employee_email?: string;
};

export type AuditLogAction =
  | "CHAT_MESSAGE"
  | "DOCUMENT_UPLOAD"
  | "DOCUMENT_DELETE"
  | "LEAVE_CREATED"
  | "LEAVE_ACCEPTED"
  | "LEAVE_REJECTED";

export type AuditLogDetails =
  | Record<string, unknown>
  | string
  | null;

export type AuditLogItem = {
  id: number;
  user_uid: string;
  email: string | null;
  role: UserRole | string | null;
  action: AuditLogAction | string;
  resource: string;
  details: AuditLogDetails;
  created_at: string;
};

export type AuditLogResponse = {
  items: AuditLogItem[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
};

export type AuditLogFilters = {
  page?: number;
  page_size?: number;
  action?: string;
  role?: string;
  resource?: string;
  user?: string;
  date_from?: string;
  date_to?: string;
};
