from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import psycopg

from app.core.config import Settings
from app.repositories.conversations import retrieve_chunks, retrieve_chunks_by_terms
from app.services.embeddings import embed_text
from app.services.guardrails import apply_policy_guardrail, insufficient_info_response
from app.services.llm import LLMUnavailableError, generate_with_openrouter


POLICY_TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "cancellation": ("cancel", "cancellation", "cancelled", "canceled"),
    "refund": ("refund", "money back", "reimburse", "reimbursement"),
    "return": ("return", "returns", "send back"),
    "shipping": (
        "shipping",
        "ship",
        "shipped",
        "delivery",
        "delivered",
        "tracking",
        "dispatch",
        "carrier",
    ),
    "damage": ("broken", "damaged", "damage", "crack", "cracked"),
}


@dataclass(slots=True)
class ReplyGenerationResult:
    customer_message: str
    retrieved_context: list[dict[str, Any]]
    ai_response: str | None
    draft_response: str
    confidence_flag: str
    similarity_score: float | None
    semantic_similarity_score: float | None
    guardrail_applied: bool
    model_used: str | None


def latest_customer_message(conversation: dict[str, Any]) -> str:
    customer_messages = [message["body"] for message in conversation["messages"] if message["sender"] == "customer"]
    return customer_messages[-1] if customer_messages else ""


def infer_policy_topics(customer_message: str) -> set[str]:
    message = customer_message.lower()
    return {
        topic
        for topic, keywords in POLICY_TOPIC_KEYWORDS.items()
        if any(keyword in message for keyword in keywords)
    }


def policy_search_terms(customer_message: str) -> list[str]:
    topics = infer_policy_topics(customer_message)
    ordered_terms: list[str] = []
    for topic in POLICY_TOPIC_KEYWORDS:
        if topic not in topics:
            continue
        for keyword in POLICY_TOPIC_KEYWORDS[topic]:
            if keyword not in ordered_terms:
                ordered_terms.append(keyword)
    return ordered_terms


def chunk_matches_topic(chunk: dict[str, Any], topic: str) -> bool:
    title = chunk["title"].lower()
    content = chunk["content"].lower()
    return any(keyword in title or keyword in content for keyword in POLICY_TOPIC_KEYWORDS[topic])


def merge_chunk_candidates(*candidate_groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen_ids: set[int] = set()
    for candidates in candidate_groups:
        for chunk in candidates:
            chunk_id = int(chunk["id"])
            if chunk_id in seen_ids:
                continue
            seen_ids.add(chunk_id)
            merged.append(chunk)
    return merged


def select_retrieved_chunks(customer_message: str, chunks: list[dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
    reranked = rerank_retrieved_chunks(customer_message, chunks)
    topics = infer_policy_topics(customer_message)
    if not topics:
        return reranked[:limit]

    selected: list[dict[str, Any]] = []
    seen_ids: set[int] = set()

    for topic in POLICY_TOPIC_KEYWORDS:
        if topic not in topics:
            continue
        for chunk in reranked:
            chunk_id = int(chunk["id"])
            if chunk_id in seen_ids:
                continue
            if chunk_matches_topic(chunk, topic):
                selected.append(chunk)
                seen_ids.add(chunk_id)
                break

    for chunk in reranked:
        if len(selected) >= limit:
            break
        chunk_id = int(chunk["id"])
        if chunk_id in seen_ids:
            continue
        selected.append(chunk)
        seen_ids.add(chunk_id)

    return selected[:limit]


def has_confident_policy_topic_match(customer_message: str, chunks: list[dict[str, Any]]) -> bool:
    topics = infer_policy_topics(customer_message)
    if not topics or not chunks:
        return False

    matched_topics = sum(1 for topic in topics if any(chunk_matches_topic(chunk, topic) for chunk in chunks[:3]))
    top_chunk_matches = any(chunk_matches_topic(chunks[0], topic) for topic in topics)
    return top_chunk_matches and matched_topics >= min(len(topics), 2)


def rerank_retrieved_chunks(
    customer_message: str,
    chunks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    topics = infer_policy_topics(customer_message)
    if not topics or not chunks:
        return chunks

    scored_chunks: list[dict[str, Any]] = []
    for index, chunk in enumerate(chunks):
        title = chunk["title"].lower()
        content = chunk["content"].lower()
        base_similarity = float(chunk["similarity"])
        matched_topics = 0
        title_matches = 0
        adjusted_similarity = base_similarity

        for topic in topics:
            keywords = POLICY_TOPIC_KEYWORDS[topic]
            title_match = any(keyword in title for keyword in keywords)
            content_match = any(keyword in content for keyword in keywords)
            if title_match:
                adjusted_similarity += 0.16
                matched_topics += 1
                title_matches += 1
            elif content_match:
                adjusted_similarity += 0.08
                matched_topics += 1

        if matched_topics == len(topics):
            adjusted_similarity += 0.04

        scored_chunks.append(
            {
                **chunk,
                "similarity": adjusted_similarity,
                "semantic_similarity": base_similarity,
                "_matched_topics": matched_topics,
                "_title_matches": title_matches,
                "_original_index": index,
            }
        )

    scored_chunks.sort(
        key=lambda chunk: (
            float(chunk["similarity"]),
            int(chunk["_title_matches"]),
            int(chunk["_matched_topics"]),
            float(chunk["semantic_similarity"]),
            -int(chunk["_original_index"]),
        ),
        reverse=True,
    )
    return scored_chunks


def deterministic_fallback_reply(
    *,
    customer_message: str,
    brand_name: str,
    customer_name: str,
    chunks: list[dict[str, Any]],
) -> str:
    message = customer_message.lower()
    mentions_damage = any(term in message for term in ("broken", "damaged", "damage", "crack", "cracked"))
    mentions_cancel = any(term in message for term in ("cancel", "cancellation", "cancelled", "canceled"))
    mentions_refund = any(term in message for term in ("refund", "money back", "reimburse"))
    mentions_return = any(term in message for term in ("return", "returns", "send back"))
    mentions_shipping = any(
        term in message for term in ("shipping", "ship", "shipped", "delivery", "tracking", "dispatch")
    )

    if mentions_damage:
        return (
            f"I'm sorry this arrived damaged, {customer_name}. Based on {brand_name}'s policy, "
            "please share your order number and clear photos of the product and packaging within "
            "7 days of delivery. Our support team will review the details and confirm the next step."
        )

    if mentions_cancel and mentions_refund:
        return (
            f"Thanks for checking, {customer_name}. Based on {brand_name}'s policies, if a cancellation "
            "is approved, the refund is sent to the original payment method within 5 to 7 business days. "
            "The separate 7-day refund window applies to refund requests after delivery under the return or "
            "damage-review process, not to an approved cancellation refund."
        )

    if mentions_cancel:
        return (
            f"Thanks for reaching out, {customer_name}. Based on {brand_name}'s cancellation policy, "
            "an order can be cancelled at no charge while it is still pending and has not entered "
            "warehouse processing. Please share your order number as soon as possible so support can "
            "check the status. If the order has already shipped, it cannot be cancelled, but support "
            "can guide you through the return process after delivery."
        )

    if mentions_refund:
        return (
            f"Thanks for reaching out, {customer_name}. I want to make sure we apply {brand_name}'s "
            "refund policy correctly. Please share your order number and delivery date so our support "
            "team can review eligibility and confirm the next step."
        )

    if mentions_return:
        return (
            f"Thanks for contacting {brand_name}, {customer_name}. Based on the return policy, unused "
            "products can be returned within 30 days of delivery in their original packaging with all "
            "accessories included. Please share your order number and support will confirm the return "
            "instructions before anything is mailed back."
        )

    if mentions_shipping:
        return (
            f"Thanks for checking, {customer_name}. Based on {brand_name}'s shipping policy, standard "
            "orders are usually processed within 1 to 2 business days and arrive within 3 to 5 business "
            "days after dispatch. If tracking has not updated for 3 business days, please share your "
            "order number so support can start a carrier review."
        )

    if chunks:
        first_title = chunks[0]["title"]
        return (
            f"Thanks for contacting {brand_name}, {customer_name}. I reviewed our {first_title.lower()} "
            "guidance and want to confirm the right next step for your case. Please share your order "
            "number and any relevant details so support can review and respond accurately."
        )

    return (
        f"Thanks for contacting {brand_name}. I could not complete an automated draft, so please share "
        "your order number and any relevant details with our support team for a careful review."
    )


def is_confident_retrieval(
    *,
    best_similarity: float | None,
    second_similarity: float | None,
    threshold: float,
    min_margin: float,
    strong_match_threshold: float,
) -> bool:
    if best_similarity is None:
        return False
    if best_similarity < threshold:
        return False
    if best_similarity >= strong_match_threshold:
        return True
    if second_similarity is None:
        return True
    return (best_similarity - second_similarity) >= min_margin


async def generate_reply_suggestion(
    connection: psycopg.AsyncConnection,
    *,
    conversation: dict[str, Any],
    customer_message_override: str | None,
    settings: Settings,
) -> ReplyGenerationResult:
    customer_message = customer_message_override or latest_customer_message(conversation)
    customer_message = customer_message.strip()
    if not customer_message:
        raise ValueError("A customer message is required")

    query_embedding = embed_text(customer_message)
    semantic_chunks = await retrieve_chunks(
        connection,
        brand_id=conversation["brand_id"],
        embedding=query_embedding,
        limit=12,
    )
    lexical_chunks = await retrieve_chunks_by_terms(
        connection,
        brand_id=conversation["brand_id"],
        terms=policy_search_terms(customer_message),
        limit=8,
    )
    chunks = select_retrieved_chunks(
        customer_message,
        merge_chunk_candidates(lexical_chunks, semantic_chunks),
        limit=3,
    )
    serialized_chunks = [
        {
            "id": chunk["id"],
            "title": chunk["title"],
            "content": chunk["content"],
            "similarity": round(float(chunk["similarity"]), 4),
            "semantic_similarity": round(float(chunk.get("semantic_similarity", chunk["similarity"])), 4),
        }
        for chunk in chunks
    ]
    best_similarity_raw = float(chunks[0]["similarity"]) if chunks else None
    second_similarity_raw = float(chunks[1]["similarity"]) if len(chunks) > 1 else None
    best_similarity = serialized_chunks[0]["similarity"] if serialized_chunks else None
    best_semantic_similarity = serialized_chunks[0]["semantic_similarity"] if serialized_chunks else None

    ai_response: str | None = None
    guardrail_applied = False
    confidence_flag = "insufficient_info"
    model_used: str | None = None

    if has_confident_policy_topic_match(customer_message, chunks) or is_confident_retrieval(
        best_similarity=best_similarity_raw,
        second_similarity=second_similarity_raw,
        threshold=settings.similarity_threshold,
        min_margin=settings.similarity_min_margin,
        strong_match_threshold=settings.similarity_strong_match_threshold,
    ):
        context = "\n\n".join(f"[{chunk['title']}]\n{chunk['content']}" for chunk in serialized_chunks)
        try:
            ai_response = await generate_with_openrouter(
                settings,
                brand_name=conversation["brand_name"],
                customer_message=customer_message,
                context=context,
            )
            model_used = settings.openrouter_model
            draft_response, guardrail_applied, confidence_flag = apply_policy_guardrail(
                customer_message,
                ai_response,
                brand_name=conversation["brand_name"],
                customer_name=conversation["customer_name"],
                delivered_at=conversation["order_delivered_at"],
            )
        except LLMUnavailableError:
            draft_response = deterministic_fallback_reply(
                customer_message=customer_message,
                brand_name=conversation["brand_name"],
                customer_name=conversation["customer_name"],
                chunks=serialized_chunks,
            )
            draft_response, guardrail_applied, guarded_flag = apply_policy_guardrail(
                customer_message,
                draft_response,
                brand_name=conversation["brand_name"],
                customer_name=conversation["customer_name"],
                delivered_at=conversation["order_delivered_at"],
            )
            confidence_flag = guarded_flag if guardrail_applied else "model_unavailable"
    else:
        draft_response = insufficient_info_response(
            conversation["brand_name"],
            customer_message=customer_message,
            customer_name=conversation["customer_name"],
        )

    return ReplyGenerationResult(
        customer_message=customer_message,
        retrieved_context=serialized_chunks,
        ai_response=ai_response,
        draft_response=draft_response,
        confidence_flag=confidence_flag,
        similarity_score=best_similarity,
        semantic_similarity_score=best_semantic_similarity,
        guardrail_applied=guardrail_applied,
        model_used=model_used,
    )