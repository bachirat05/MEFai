import type {
  AuditLogFilters,
  AuditLogResponse,
  ChatApiResponse,
  Conversation,
  LeaveApiResponse,
  LeaveRequest,
  LeaveRequestRecord,
  LeaveRequestStatus,
  ManagerLeaveRequest,
} from "../types";


const API_BASE_URL = "http://127.0.0.1:8000";

export async function sendChatMessage(
  token: string,
  message: string,
  conversationId: number | null
): Promise<ChatApiResponse> {
  const response = await fetch(`${API_BASE_URL}/api/chat`, {
    method: "POST",

    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },

    body: JSON.stringify({
      message,
      conversation_id: conversationId,
    }),
  });

  if (!response.ok) {
    let errorMessage = `HTTP ${response.status}`;

    try {
      const errorData: unknown = await response.json();

      if (
        typeof errorData === "object" &&
        errorData !== null &&
        "detail" in errorData
      ) {
        const detail = (errorData as { detail?: unknown }).detail;

        if (typeof detail === "string") {
          errorMessage = detail;
        }
      }
    } catch {
      // Le serveur n'a pas retourné de JSON.
    }

    throw new Error(errorMessage);
  }

  return (await response.json()) as ChatApiResponse;
}

export async function getConversations(
  token: string
): Promise<Conversation[]> {
  const response = await fetch(
    `${API_BASE_URL}/api/conversations`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );

  if (!response.ok) {
    throw new Error(await getErrorMessage(response));
  }

  const summaries = (await response.json()) as Array<
    Omit<Conversation, "messages">
  >;

  return summaries.map((conversation) => ({
    ...conversation,
    messages: [],
  }));
}

export async function createConversation(
  token: string
): Promise<Conversation> {
  const response = await fetch(
    `${API_BASE_URL}/api/conversations`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );

  if (!response.ok) {
    throw new Error(await getErrorMessage(response));
  }

  return (await response.json()) as Conversation;
}

export async function getConversation(
  token: string,
  conversationId: number
): Promise<Conversation> {
  const response = await fetch(
    `${API_BASE_URL}/api/conversations/${conversationId}`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );

  if (!response.ok) {
    throw new Error(await getErrorMessage(response));
  }

  return (await response.json()) as Conversation;
}

export async function deleteConversation(
  token: string,
  conversationId: number
): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/api/conversations/${conversationId}`,
    {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );

  if (!response.ok) {
    throw new Error(await getErrorMessage(response));
  }
}
export async function submitLeaveRequest(
  token: string,
  request: LeaveRequest
): Promise<LeaveApiResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/conges`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(request),
    }
  );

  if (!response.ok) {
    let errorMessage =
      `HTTP ${response.status}`;

    try {
      const errorData: unknown =
        await response.json();

      if (
        typeof errorData === "object" &&
        errorData !== null &&
        "detail" in errorData
      ) {
        const detail = (
          errorData as {
            detail?: unknown;
          }
        ).detail;

        if (
          typeof detail === "string"
        ) {
          errorMessage = detail;
        }
      }
    } catch {
      // Pas de réponse JSON.
    }

    throw new Error(
      errorMessage
    );
  }

  return (
    await response.json()
  ) as LeaveApiResponse;
}
export async function getMyLeaveRequests(
  token: string
): Promise<LeaveRequestRecord[]> {
  const response = await fetch(
    `${API_BASE_URL}/api/conges`,
    {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );

  if (!response.ok) {
    let errorMessage =
      `HTTP ${response.status}`;

    try {
      const errorData: unknown =
        await response.json();

      if (
        typeof errorData === "object" &&
        errorData !== null &&
        "detail" in errorData
      ) {
        const detail = (
          errorData as {
            detail?: unknown;
          }
        ).detail;

        if (
          typeof detail === "string"
        ) {
          errorMessage = detail;
        }
      }
    } catch {
      // No JSON response.
    }

    throw new Error(
      errorMessage
    );
  }

  return (
    await response.json()
  ) as LeaveRequestRecord[];
}

export async function getManagerLeaveRequests(
  token: string
): Promise<ManagerLeaveRequest[]> {
  const response = await fetch(
    `${API_BASE_URL}/api/manager/conges`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );

  if (!response.ok) {
    throw new Error(await getErrorMessage(response));
  }

  return (await response.json()) as ManagerLeaveRequest[];
}

export async function updateLeaveRequestStatus(
  token: string,
  demandeId: string,
  statut: Extract<LeaveRequestStatus, "accepted" | "rejected">
): Promise<ManagerLeaveRequest> {
  const response = await fetch(
    `${API_BASE_URL}/api/manager/conges/${demandeId}`,
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ statut }),
    }
  );

  if (!response.ok) {
    throw new Error(await getErrorMessage(response));
  }

  return (await response.json()) as ManagerLeaveRequest;
}

async function getErrorMessage(response: Response): Promise<string> {
  let errorMessage = `HTTP ${response.status}`;

  try {
    const errorData: unknown = await response.json();
    if (
      typeof errorData === "object" &&
      errorData !== null &&
      "detail" in errorData &&
      typeof (errorData as { detail?: unknown }).detail === "string"
    ) {
      errorMessage = (errorData as { detail: string }).detail;
    }
  } catch {
    // No JSON response.
  }

  return errorMessage;
}
export type RagDocument = {
  name: string;
  type: string;
  size: number;
};

export async function getDocuments(
  token: string
): Promise<RagDocument[]> {
  const response = await fetch(
    `${API_BASE_URL}/api/documents`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(response)
    );
  }

  return response.json();
}

export type UploadDocumentResponse = {
  message: string;
  name: string;
  type: string;
  size: number;
  chunks: number;
  rag_ingested: boolean;
};

export async function uploadDocument(
  token: string,
  file: File
): Promise<UploadDocumentResponse> {
  const formData = new FormData();
  formData.append(
    "file",
    file
  );

  const response = await fetch(
    `${API_BASE_URL}/api/documents/upload`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
    }
  );

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(response)
    );
  }

  return (
    await response.json()
  ) as UploadDocumentResponse;
}

export type DeleteDocumentResponse = {
  message: string;
  name: string;
  chunks_deleted: number;
};

export async function deleteDocument(
  token: string,
  filename: string
): Promise<DeleteDocumentResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/documents/${encodeURIComponent(filename)}`,
    {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(response)
    );
  }

  return (
    await response.json()
  ) as DeleteDocumentResponse;
}
export type SystemStatus = {
  ollama: "online" | "offline";
  rag: "ready" | "unavailable";
  n8n: "configured" | "not_configured";
  documents: number;
  embedding_model: string;
  rag_collection: string;
};

export type DailyActivity = {
  date: string;
  chat_messages: number;
  documents: number;
  leave_requests: number;
  manager_actions: number;
};

export type RecentActivity = {
  action: string;
  resource: string;
  email: string | null;
  role: string | null;
  created_at: string;
  details?: Record<string, unknown> | string | null;
};

export type ActivitySummary = {
  days: number;
  totals: {
    chat_messages: number;
    documents_uploaded: number;
    documents_deleted: number;
    leave_created: number;
    leave_accepted: number;
    leave_rejected: number;
  };
  daily: DailyActivity[];
  recent: RecentActivity[];
};

export async function getSystemStatus(
  token: string
): Promise<SystemStatus> {
  const response = await fetch(
    `${API_BASE_URL}/api/admin/system-status`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );

  if (!response.ok) {
    throw new Error(
      "Impossible de charger l'état du système."
    );
  }

  return response.json();
}

export async function getAdminActivity(
  token: string,
  days = 7
): Promise<ActivitySummary> {
  const response = await fetch(
    `${API_BASE_URL}/api/admin/activity?days=${encodeURIComponent(days)}`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(response)
    );
  }

  return (
    await response.json()
  ) as ActivitySummary;
}

export async function getAuditLogs(
  token: string,
  filters: AuditLogFilters = {}
): Promise<AuditLogResponse> {
  const params = new URLSearchParams();

  Object.entries(filters).forEach(([key, value]) => {
    if (
      value === undefined ||
      value === null ||
      value === ""
    ) {
      return;
    }

    params.set(
      key,
      String(value)
    );
  });

  const query = params.toString();

  const response = await fetch(
    `${API_BASE_URL}/api/admin/audit-logs${query ? `?${query}` : ""}`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(response)
    );
  }

  return (
    await response.json()
  ) as AuditLogResponse;
}
