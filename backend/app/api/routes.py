from __future__ import annotations

import psycopg
from fastapi import APIRouter, Depends, HTTPException

from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.models.schemas import (
    AnalyticsResponse,
    ApproveReplyRequest,
    ApproveReplyResponse,
    ConversationListResponse,
    ConversationResponse,
    GenerateReplyRequest,
    GenerateReplyResponse,
    HealthResponse,
    KnowledgeDocumentsResponse,
)
from app.repositories.conversations import (
    approve_reply_log,
    fetch_brand_analytics,
    fetch_conversation,
    fetch_conversation_by_slug,
    fetch_reply_log_context,
    insert_reply_log,
    list_conversations,
    list_knowledge_documents,
)
from app.services.guardrails import apply_policy_guardrail
from app.services.reply_generation import generate_reply_suggestion
from app.services.auth import authenticate_user
from app.models.schemas import AuthRequest
from fastapi import Depends, Header

router = APIRouter()


def _conversation_or_404(conversation: dict | None) -> dict:
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


def _conversation_response(conversation: dict) -> ConversationResponse:
    order = None
    if conversation["order_id"] is not None:
        order = {
            "id": conversation["order_id"],
            "external_id": conversation["order_external_id"],
            "item_name": conversation["order_item_name"],
            "quantity": conversation["order_quantity"],
            "total_amount": conversation["order_total_amount"],
            "currency": conversation["order_currency"],
            "status": conversation["order_status"],
            "delivered_at": conversation["order_delivered_at"],
        }
    return ConversationResponse(
        id=conversation["conversation_id"],
        slug=conversation["slug"],
        status=conversation["conversation_status"],
        created_at=conversation["conversation_created_at"],
        brand={
            "id": conversation["brand_id"],
            "name": conversation["brand_name"],
            "slug": conversation["brand_slug"],
        },
        customer={
            "id": conversation["customer_id"],
            "name": conversation["customer_name"],
            "email": conversation["customer_email"],
        },
        order=order,
        messages=conversation["messages"],
    )


@router.get("/health", response_model=HealthResponse)
async def health(connection: psycopg.AsyncConnection = Depends(get_db)) -> HealthResponse:
    async with connection.cursor() as cursor:
        await cursor.execute("SELECT 1")
        await cursor.fetchone()
    return HealthResponse(status="ok", database="connected")


@router.get("/api/conversations/by-slug/{slug}", response_model=ConversationResponse)
async def get_conversation_by_slug(
    slug: str,
    connection: psycopg.AsyncConnection = Depends(get_db),
) -> ConversationResponse:
    conversation = _conversation_or_404(await fetch_conversation_by_slug(connection, slug))
    return _conversation_response(conversation)


@router.get("/api/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: int,
    connection: psycopg.AsyncConnection = Depends(get_db),
) -> ConversationResponse:
    conversation = _conversation_or_404(await fetch_conversation(connection, conversation_id))
    return _conversation_response(conversation)


@router.get("/api/conversations", response_model=ConversationListResponse)
async def get_conversations(
    connection: psycopg.AsyncConnection = Depends(get_db),
) -> ConversationListResponse:
    conversations = await list_conversations(connection)
    return ConversationListResponse(items=conversations)


@router.get(
    "/api/brands/{brand_id}/knowledge-documents",
    response_model=KnowledgeDocumentsResponse,
)
async def get_knowledge_documents(
    brand_id: int,
    connection: psycopg.AsyncConnection = Depends(get_db),
) -> KnowledgeDocumentsResponse:
    brand_name, items = await list_knowledge_documents(connection, brand_id=brand_id)
    if brand_name is None:
        raise HTTPException(status_code=404, detail="Brand not found")
    return KnowledgeDocumentsResponse(brand_id=brand_id, brand_name=brand_name, items=items)


@router.get("/api/brands/{brand_id}/analytics", response_model=AnalyticsResponse)
async def get_brand_analytics(
    brand_id: int,
    connection: psycopg.AsyncConnection = Depends(get_db),
) -> AnalyticsResponse:
    analytics = await fetch_brand_analytics(connection, brand_id=brand_id)
    if analytics is None:
        raise HTTPException(status_code=404, detail="Brand not found")

    total_reply_logs = analytics["total_reply_logs"]
    approved_reply_logs = analytics["approved_reply_logs"]
    approval_rate = approved_reply_logs / total_reply_logs if total_reply_logs > 0 else 0.0

    return AnalyticsResponse(**analytics, approval_rate=round(approval_rate, 4))


@router.post("/api/conversations/{conversation_id}/generate", response_model=GenerateReplyResponse)
async def generate_reply(
    conversation_id: int,
    request: GenerateReplyRequest | None = None,
    connection: psycopg.AsyncConnection = Depends(get_db),
    app_settings: Settings = Depends(get_settings),
    authorization: str | None = Header(default=None),
) -> GenerateReplyResponse:
    conversation = _conversation_or_404(await fetch_conversation(connection, conversation_id))
    customer_message_override = request.customer_message if request is not None else None

    # Simple Basic auth: require Authorization: Basic <base64 email:password>
    if authorization is None:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    if not authorization.lower().startswith("basic "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header")
    import base64

    try:
        creds = base64.b64decode(authorization.split(" ", 1)[1]).decode()
        email, password = creds.split(":", 1)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid Authorization header")
    if not authenticate_user(email, password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    try:
        result = await generate_reply_suggestion(
            connection,
            conversation=conversation,
            customer_message_override=customer_message_override,
            settings=app_settings,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise
        if isinstance(exc, (RuntimeError, ValueError)) and "embedding" in str(exc).lower():
            raise HTTPException(
                status_code=503,
                detail="The local embedding model could not be loaded. Run the seed setup and retry.",
            ) from exc
        raise

    log_id = await insert_reply_log(
        connection,
        brand_id=conversation["brand_id"],
        conversation_id=conversation_id,
        customer_message=result.customer_message,
        retrieved_context=result.retrieved_context,
        ai_response=result.ai_response,
        suggested_response=result.draft_response,
        confidence_flag=result.confidence_flag,
        similarity_score=result.similarity_score,
        guardrail_applied=result.guardrail_applied,
    )
    await connection.commit()

    return GenerateReplyResponse(
        reply_log_id=log_id,
        customer_message=result.customer_message,
        retrieved_context=result.retrieved_context,
        ai_response=result.ai_response,
        draft_response=result.draft_response,
        confidence_flag=result.confidence_flag,
        similarity_score=result.similarity_score,
        semantic_similarity_score=result.semantic_similarity_score,
        guardrail_applied=result.guardrail_applied,
        model_used=result.model_used,
    )


@router.post("/api/auth/login")
async def login(request: AuthRequest, app_settings: Settings = Depends(get_settings)) -> dict:
    if not authenticate_user(request.email, request.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"status": "ok"}


@router.post(
    "/api/conversations/{conversation_id}/reply-logs/{log_id}/approve",
    response_model=ApproveReplyResponse,
)
async def approve_reply(
    conversation_id: int,
    log_id: int,
    request: ApproveReplyRequest,
    connection: psycopg.AsyncConnection = Depends(get_db),
) -> ApproveReplyResponse:
    edited_response = request.edited_response.strip() if request.edited_response else None
    if not edited_response:
        raise HTTPException(status_code=422, detail="An approved response cannot be empty")
    log_context = await fetch_reply_log_context(connection, log_id=log_id, conversation_id=conversation_id)
    if log_context is None:
        raise HTTPException(status_code=404, detail="Reply draft not found for this conversation")
    guarded_response, guardrail_applied, confidence_flag = apply_policy_guardrail(
        log_context["customer_message"],
        edited_response,
        brand_name=log_context["brand_name"],
        customer_name=log_context["customer_name"],
        delivered_at=log_context["order_delivered_at"],
    )
    final_response = guarded_response if guardrail_applied else edited_response
    final_confidence_flag = confidence_flag if guardrail_applied else log_context["confidence_flag"]
    result = await approve_reply_log(
        connection,
        log_id=log_id,
        conversation_id=conversation_id,
        edited_response=edited_response,
        final_response=final_response,
        confidence_flag=final_confidence_flag,
        guardrail_applied=guardrail_applied,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Reply draft not found for this conversation")
    await connection.commit()
    return ApproveReplyResponse(**result)