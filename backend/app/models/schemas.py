from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ConfidenceFlag = Literal["grounded", "insufficient_info", "model_unavailable", "review_required"]


class BrandResponse(BaseModel):
    id: int
    name: str
    slug: str


class CustomerResponse(BaseModel):
    id: int
    name: str
    email: str


class OrderResponse(BaseModel):
    id: int
    external_id: str
    item_name: str
    quantity: int
    total_amount: Decimal
    currency: str
    status: str
    delivered_at: datetime | None = None


class MessageResponse(BaseModel):
    id: int
    sender: str
    body: str
    created_at: datetime


class ConversationResponse(BaseModel):
    id: int
    slug: str
    status: str
    created_at: datetime
    brand: BrandResponse
    customer: CustomerResponse
    order: OrderResponse | None = None
    messages: list[MessageResponse]


class ConversationListItemResponse(BaseModel):
    id: int
    slug: str
    status: str
    created_at: datetime
    customer_name: str
    customer_email: str
    brand_name: str
    message_count: int
    latest_message_body: str | None = None
    latest_message_sender: str | None = None
    latest_message_at: datetime | None = None
    order_external_id: str | None = None


class ConversationListResponse(BaseModel):
    items: list[ConversationListItemResponse]


class KnowledgeDocumentResponse(BaseModel):
    id: int
    title: str
    content: str
    chunk_count: int
    created_at: datetime


class KnowledgeDocumentsResponse(BaseModel):
    brand_id: int
    brand_name: str
    items: list[KnowledgeDocumentResponse]


class ConfidenceBreakdownResponse(BaseModel):
    confidence_flag: ConfidenceFlag
    count: int


class RecentReplyLogResponse(BaseModel):
    reply_log_id: int
    conversation_id: int
    customer_name: str
    confidence_flag: ConfidenceFlag
    guardrail_applied: bool
    approved_at: datetime | None = None
    timestamp: datetime


class AnalyticsResponse(BaseModel):
    brand_id: int
    brand_name: str
    total_conversations: int
    total_messages: int
    total_reply_logs: int
    approved_reply_logs: int
    approval_rate: float
    avg_similarity_score: float | None = None
    confidence_breakdown: list[ConfidenceBreakdownResponse]
    recent_reply_logs: list[RecentReplyLogResponse]


class GenerateReplyRequest(BaseModel):
    customer_message: str | None = Field(default=None, max_length=4000)


class AuthRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    access_token: str


class RetrievedChunk(BaseModel):
    id: int
    title: str
    content: str
    similarity: float
    semantic_similarity: float


class GenerateReplyResponse(BaseModel):
    reply_log_id: int
    customer_message: str
    retrieved_context: list[RetrievedChunk]
    ai_response: str | None
    draft_response: str
    confidence_flag: ConfidenceFlag
    similarity_score: float | None
    semantic_similarity_score: float | None
    guardrail_applied: bool
    model_used: str | None = None


class ApproveReplyRequest(BaseModel):
    edited_response: str | None = Field(default=None, max_length=8000)


class ApproveReplyResponse(BaseModel):
    reply_log_id: int
    edited_response: str | None
    final_response: str
    approved_at: datetime


class HealthResponse(BaseModel):
    status: str
    database: str


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    detail: str