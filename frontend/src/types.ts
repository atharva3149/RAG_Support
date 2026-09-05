export type Sender = "customer" | "agent";
export type ConfidenceFlag = "grounded" | "insufficient_info" | "model_unavailable" | "review_required";

export interface Brand {
  id: number;
  name: string;
  slug: string;
}

export interface Customer {
  id: number;
  name: string;
  email: string;
}

export interface Order {
  id: number;
  external_id: string;
  item_name: string;
  quantity: number;
  total_amount: string;
  currency: string;
  status: string;
  delivered_at: string | null;
}

export interface Message {
  id: number;
  sender: Sender;
  body: string;
  created_at: string;
}

export interface Conversation {
  id: number;
  slug: string;
  status: string;
  created_at: string;
  brand: Brand;
  customer: Customer;
  order: Order | null;
  messages: Message[];
}

export interface ConversationListItem {
  id: number;
  slug: string;
  status: string;
  created_at: string;
  customer_name: string;
  customer_email: string;
  brand_name: string;
  message_count: number;
  latest_message_body: string | null;
  latest_message_sender: Sender | null;
  latest_message_at: string | null;
  order_external_id: string | null;
}

export interface ConversationListResponse {
  items: ConversationListItem[];
}

export interface KnowledgeDocument {
  id: number;
  title: string;
  content: string;
  chunk_count: number;
  created_at: string;
}

export interface KnowledgeDocumentsResponse {
  brand_id: number;
  brand_name: string;
  items: KnowledgeDocument[];
}

export interface ConfidenceBreakdown {
  confidence_flag: ConfidenceFlag;
  count: number;
}

export interface RecentReplyLog {
  reply_log_id: number;
  conversation_id: number;
  customer_name: string;
  confidence_flag: ConfidenceFlag;
  guardrail_applied: boolean;
  approved_at: string | null;
  timestamp: string;
}

export interface AnalyticsResponse {
  brand_id: number;
  brand_name: string;
  total_conversations: number;
  total_messages: number;
  total_reply_logs: number;
  approved_reply_logs: number;
  approval_rate: number;
  avg_similarity_score: number | null;
  confidence_breakdown: ConfidenceBreakdown[];
  recent_reply_logs: RecentReplyLog[];
}

export interface RetrievedChunk {
  id: number;
  title: string;
  content: string;
  similarity: number;
  semantic_similarity: number;
}

export interface GenerateReplyResponse {
  reply_log_id: number;
  customer_message: string;
  retrieved_context: RetrievedChunk[];
  ai_response: string | null;
  draft_response: string;
  confidence_flag: ConfidenceFlag;
  similarity_score: number | null;
  semantic_similarity_score: number | null;
  guardrail_applied: boolean;
  model_used: string | null;
}

export interface ApproveReplyResponse {
  reply_log_id: number;
  edited_response: string | null;
  final_response: string;
  approved_at: string;
}
