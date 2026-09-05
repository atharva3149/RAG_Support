from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.api.routes import get_db, get_settings
from app.core.config import Settings
from app.main import create_app
from app.services.reply_generation import ReplyGenerationResult


class DummyConnection:
    async def commit(self) -> None:
        return None


def test_generate_reply_exposes_reranked_and_semantic_scores(monkeypatch) -> None:
    app = create_app()

    async def override_db():
        yield DummyConnection()

    def override_settings() -> Settings:
        return Settings(openrouter_api_key=None)

    async def fake_fetch_conversation(connection: Any, conversation_id: int) -> dict[str, Any]:
        return {
            "conversation_id": conversation_id,
            "slug": "maya-patel-cancel-order",
            "conversation_status": "open",
            "conversation_created_at": "2026-09-04T10:00:00Z",
            "brand_id": 1,
            "brand_name": "HydroFlow",
            "brand_slug": "hydroflow",
            "customer_id": 1,
            "customer_name": "Maya Patel",
            "customer_email": "maya@example.com",
            "order_id": 1,
            "order_external_id": "HF-1001",
            "order_item_name": "HydroFlow Bottle",
            "order_quantity": 1,
            "order_total_amount": "39.00",
            "order_currency": "USD",
            "order_status": "pending",
            "order_delivered_at": None,
            "messages": [
                {
                    "id": 1,
                    "sender": "customer",
                    "body": "I want to cancel my order",
                    "created_at": "2026-09-04T10:00:00Z",
                }
            ],
        }

    async def fake_generate_reply_suggestion(connection: Any, *, conversation: dict[str, Any], customer_message_override: str | None, settings: Settings) -> ReplyGenerationResult:
        return ReplyGenerationResult(
            customer_message=customer_message_override or "I want to cancel my order",
            retrieved_context=[
                {
                    "id": 10,
                    "title": "Cancellation policy",
                    "content": "An order can be cancelled at no charge while it is still pending.",
                    "similarity": 0.47,
                    "semantic_similarity": 0.27,
                },
                {
                    "id": 11,
                    "title": "Shipping policy",
                    "content": "Tracking is emailed when the order leaves our warehouse.",
                    "similarity": 0.29,
                    "semantic_similarity": 0.29,
                },
            ],
            ai_response=None,
            draft_response="An order can be cancelled while it is still pending and has not entered warehouse processing.",
            confidence_flag="grounded",
            similarity_score=0.47,
            semantic_similarity_score=0.27,
            guardrail_applied=False,
            model_used=None,
        )

    async def fake_insert_reply_log(connection: Any, **_: Any) -> int:
        return 99

    monkeypatch.setattr("app.api.routes.fetch_conversation", fake_fetch_conversation)
    monkeypatch.setattr("app.api.routes.generate_reply_suggestion", fake_generate_reply_suggestion)
    monkeypatch.setattr("app.api.routes.insert_reply_log", fake_insert_reply_log)
    # stub authenticate_user so test client can call the protected route
    monkeypatch.setattr("app.api.routes.authenticate_user", lambda email, password: True)

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = override_settings

    with TestClient(app) as client:
        import base64
        creds = base64.b64encode(b"maya@example.com:password").decode()
        response = client.post(
            "/api/conversations/1/generate",
            json={"customer_message": "I want to cancel my order"},
            headers={"Authorization": f"Basic {creds}"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["similarity_score"] == 0.47
    assert payload["semantic_similarity_score"] == 0.27
    assert payload["retrieved_context"][0]["title"] == "Cancellation policy"
    assert payload["retrieved_context"][0]["similarity"] == 0.47
    assert payload["retrieved_context"][0]["semantic_similarity"] == 0.27