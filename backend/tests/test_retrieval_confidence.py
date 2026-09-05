from app.services.reply_generation import (
    deterministic_fallback_reply,
    has_confident_policy_topic_match,
    is_confident_retrieval,
    select_retrieved_chunks,
    rerank_retrieved_chunks,
)


def test_retrieval_rejects_below_threshold() -> None:
    assert is_confident_retrieval(
        best_similarity=0.34,
        second_similarity=0.20,
        threshold=0.35,
        min_margin=0.02,
        strong_match_threshold=0.55,
    ) is False


def test_retrieval_accepts_strong_match_even_small_margin() -> None:
    assert is_confident_retrieval(
        best_similarity=0.60,
        second_similarity=0.59,
        threshold=0.35,
        min_margin=0.02,
        strong_match_threshold=0.55,
    ) is True


def test_retrieval_accepts_when_margin_is_sufficient() -> None:
    assert is_confident_retrieval(
        best_similarity=0.42,
        second_similarity=0.36,
        threshold=0.35,
        min_margin=0.02,
        strong_match_threshold=0.55,
    ) is True


def test_retrieval_rejects_borderline_when_margin_is_too_small() -> None:
    assert is_confident_retrieval(
        best_similarity=0.41,
        second_similarity=0.40,
        threshold=0.35,
        min_margin=0.02,
        strong_match_threshold=0.55,
    ) is False


def test_retrieval_accepts_single_chunk_above_threshold() -> None:
    assert is_confident_retrieval(
        best_similarity=0.39,
        second_similarity=None,
        threshold=0.35,
        min_margin=0.02,
        strong_match_threshold=0.55,
    ) is True


def test_rerank_retrieved_chunks_prioritizes_cancellation_policy() -> None:
    chunks = [
        {
            "id": 1,
            "title": "Shipping policy",
            "content": "Tracking is emailed when the order leaves our warehouse.",
            "similarity": 0.29,
        },
        {
            "id": 2,
            "title": "Cancellation policy",
            "content": "An order can be cancelled at no charge while it is still pending.",
            "similarity": 0.27,
        },
        {
            "id": 3,
            "title": "Return policy",
            "content": "Unused products can be returned within 30 days of delivery.",
            "similarity": 0.26,
        },
    ]

    reranked = rerank_retrieved_chunks("I want to cancel my order", chunks)

    assert reranked[0]["title"] == "Cancellation policy"
    assert reranked[0]["similarity"] > reranked[1]["similarity"]


def test_rerank_retrieved_chunks_prioritizes_refund_policy() -> None:
    chunks = [
        {
            "id": 1,
            "title": "Shipping policy",
            "content": "Tracking is emailed when the order leaves our warehouse.",
            "similarity": 0.31,
        },
        {
            "id": 2,
            "title": "Refund policy",
            "content": "Refunds are only permitted within 7 days of delivery.",
            "similarity": 0.28,
        },
    ]

    reranked = rerank_retrieved_chunks("Can I get a refund for this?", chunks)

    assert reranked[0]["title"] == "Refund policy"


def test_reranked_cancellation_match_can_clear_confidence_threshold() -> None:
    chunks = [
        {
            "id": 1,
            "title": "Shipping policy",
            "content": "Tracking is emailed when the order leaves our warehouse.",
            "similarity": 0.29,
        },
        {
            "id": 2,
            "title": "Cancellation policy",
            "content": "An order can be cancelled at no charge while it is still pending.",
            "similarity": 0.27,
        },
    ]

    reranked = rerank_retrieved_chunks("I want to cancel my order", chunks)

    assert is_confident_retrieval(
        best_similarity=reranked[0]["similarity"],
        second_similarity=reranked[1]["similarity"],
        threshold=0.35,
        min_margin=0.02,
        strong_match_threshold=0.55,
    ) is True


def test_select_retrieved_chunks_covers_mixed_cancellation_and_refund_topics() -> None:
    chunks = [
        {
            "id": 1,
            "title": "Return policy",
            "content": "Returns are available for unused HydroFlow products within 30 days of delivery.",
            "similarity": 0.31,
        },
        {
            "id": 2,
            "title": "Cancellation policy",
            "content": "If a cancellation is approved, any refund is sent to the original payment method within 5 to 7 business days.",
            "similarity": 0.18,
        },
        {
            "id": 3,
            "title": "Refund policy",
            "content": "Refunds are only permitted within 7 days of delivery after the return or damage review is approved.",
            "similarity": 0.19,
        },
    ]

    selected = select_retrieved_chunks(
        "I cancelled my order and got approved for a refund — does the 7-day refund policy window apply to me too?",
        chunks,
    )

    assert selected[0]["title"] == "Cancellation policy"
    assert {chunk["title"] for chunk in selected[:2]} == {"Cancellation policy", "Refund policy"}


def test_direct_policy_topic_match_can_be_confident_for_mixed_intent() -> None:
    chunks = [
        {
            "id": 2,
            "title": "Cancellation policy",
            "content": "If a cancellation is approved, any refund is sent to the original payment method within 5 to 7 business days.",
            "similarity": 0.34,
        },
        {
            "id": 3,
            "title": "Refund policy",
            "content": "Refunds are only permitted within 7 days of delivery after the return or damage review is approved.",
            "similarity": 0.33,
        },
    ]

    assert has_confident_policy_topic_match(
        "I cancelled my order and got approved for a refund — does the 7-day refund policy window apply to me too?",
        chunks,
    ) is True


def test_mixed_cancel_refund_fallback_answers_from_policy() -> None:
    draft = deterministic_fallback_reply(
        customer_message="I cancelled my order and got approved for a refund — does the 7-day refund policy window apply to me too?",
        brand_name="HydroFlow",
        customer_name="Maya Patel",
        chunks=[],
    )

    assert "5 to 7 business days" in draft
    assert "approved cancellation refund" in draft
