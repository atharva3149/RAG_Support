import type {
  AnalyticsResponse,
  ApproveReplyResponse,
  ConversationListResponse,
  Conversation,
  GenerateReplyResponse,
  KnowledgeDocumentsResponse,
} from "./types";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const email = localStorage.getItem("ds_email");
  const password = localStorage.getItem("ds_password");
  const headers = new Headers(init?.headers as HeadersInit);
  headers.set("Content-Type", "application/json");
  if (email && password) {
    headers.set("Authorization", `Basic ${btoa(`${email}:${password}`)}`);
  }
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
  });
  // If the server returns 401, clear stored credentials and reload to show login.
  if (response.status === 401) {
    localStorage.removeItem("ds_email");
    localStorage.removeItem("ds_password");
    // reload the app so the UI shows the sign-in screen.
    if (typeof window !== "undefined") window.location.reload();
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail || "Unauthorized");
  }

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export async function login(email: string, password: string): Promise<string> {
  const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail || `Request failed (${response.status})`);
  }
  await response.json().catch(() => null);
  // store credentials locally for Basic auth on subsequent requests (dev only)
  localStorage.setItem("ds_email", email);
  localStorage.setItem("ds_password", password);
  return "ok";
}

export function getConversation(conversationId: number): Promise<Conversation> {
  return request<Conversation>(`/api/conversations/${conversationId}`);
}

export function getConversationBySlug(slug: string): Promise<Conversation> {
  return request<Conversation>(`/api/conversations/by-slug/${encodeURIComponent(slug)}`);
}

export function getConversations(): Promise<ConversationListResponse> {
  return request<ConversationListResponse>("/api/conversations");
}

export function getKnowledgeDocuments(brandId: number): Promise<KnowledgeDocumentsResponse> {
  return request<KnowledgeDocumentsResponse>(`/api/brands/${brandId}/knowledge-documents`);
}

export function getAnalytics(brandId: number): Promise<AnalyticsResponse> {
  return request<AnalyticsResponse>(`/api/brands/${brandId}/analytics`);
}

export function generateReply(
  conversationId: number,
  customerMessage?: string,
): Promise<GenerateReplyResponse> {
  return request<GenerateReplyResponse>(`/api/conversations/${conversationId}/generate`, {
    method: "POST",
    body: JSON.stringify(customerMessage === undefined ? {} : { customer_message: customerMessage }),
  });
}

export function approveReply(
  conversationId: number,
  logId: number,
  editedResponse: string,
): Promise<ApproveReplyResponse> {
  return request<ApproveReplyResponse>(
    `/api/conversations/${conversationId}/reply-logs/${logId}/approve`,
    {
      method: "POST",
      body: JSON.stringify({ edited_response: editedResponse }),
    },
  );
}

export function logout(): void {
  localStorage.removeItem("ds_email");
  localStorage.removeItem("ds_password");
}
