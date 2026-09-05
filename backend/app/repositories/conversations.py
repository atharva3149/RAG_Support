from __future__ import annotations

import json
from typing import Any

import psycopg

from app.services.embeddings import vector_literal


async def _fetch_conversation(
    connection: psycopg.AsyncConnection,
    *,
    lookup_column: str,
    lookup_value: int | str,
) -> dict[str, Any] | None:
    async with connection.cursor() as cursor:
        await cursor.execute(
            f"""
            SELECT
                c.id AS conversation_id,
                c.slug,
                c.status AS conversation_status,
                c.created_at AS conversation_created_at,
                b.id AS brand_id,
                b.name AS brand_name,
                b.slug AS brand_slug,
                cu.id AS customer_id,
                cu.name AS customer_name,
                cu.email AS customer_email,
                o.id AS order_id,
                o.external_id AS order_external_id,
                o.item_name AS order_item_name,
                o.quantity AS order_quantity,
                o.total_amount AS order_total_amount,
                o.currency AS order_currency,
                o.status AS order_status,
                o.delivered_at AS order_delivered_at
            FROM conversations c
            JOIN brands b ON b.id = c.brand_id
            JOIN customers cu ON cu.id = c.customer_id AND cu.brand_id = c.brand_id
            LEFT JOIN orders o
              ON o.id = c.order_id
             AND o.brand_id = c.brand_id
             AND o.customer_id = c.customer_id
            WHERE c.{lookup_column} = %s
            """,
            (lookup_value,),
        )
        conversation = await cursor.fetchone()
        if conversation is None:
            return None

        await cursor.execute(
            """
            SELECT id, sender, body, created_at
            FROM messages
            WHERE conversation_id = %s AND brand_id = %s
            ORDER BY created_at ASC, id ASC
            """,
            (conversation["conversation_id"], conversation["brand_id"]),
        )
        conversation["messages"] = await cursor.fetchall()
    return conversation


async def fetch_conversation(
    connection: psycopg.AsyncConnection,
    conversation_id: int,
) -> dict[str, Any] | None:
    return await _fetch_conversation(connection, lookup_column="id", lookup_value=conversation_id)


async def fetch_conversation_by_slug(
    connection: psycopg.AsyncConnection,
    slug: str,
) -> dict[str, Any] | None:
    return await _fetch_conversation(connection, lookup_column="slug", lookup_value=slug)


async def list_conversations(connection: psycopg.AsyncConnection) -> list[dict[str, Any]]:
    async with connection.cursor() as cursor:
        await cursor.execute(
            """
            SELECT
                c.id,
                c.slug,
                c.status,
                c.created_at,
                cu.name AS customer_name,
                cu.email AS customer_email,
                b.name AS brand_name,
                o.external_id AS order_external_id,
                COUNT(m.id)::int AS message_count,
                lm.body AS latest_message_body,
                lm.sender AS latest_message_sender,
                lm.created_at AS latest_message_at
            FROM conversations c
            JOIN brands b ON b.id = c.brand_id
            JOIN customers cu
              ON cu.id = c.customer_id
             AND cu.brand_id = c.brand_id
            LEFT JOIN orders o
              ON o.id = c.order_id
             AND o.brand_id = c.brand_id
             AND o.customer_id = c.customer_id
            LEFT JOIN messages m
              ON m.conversation_id = c.id
             AND m.brand_id = c.brand_id
            LEFT JOIN LATERAL (
                SELECT body, sender, created_at
                FROM messages mx
                WHERE mx.conversation_id = c.id
                  AND mx.brand_id = c.brand_id
                ORDER BY mx.created_at DESC, mx.id DESC
                LIMIT 1
            ) lm ON TRUE
            GROUP BY
                c.id,
                c.slug,
                c.status,
                c.created_at,
                cu.name,
                cu.email,
                b.name,
                o.external_id,
                lm.body,
                lm.sender,
                lm.created_at
            ORDER BY c.created_at DESC, c.id DESC
            """
        )
        return await cursor.fetchall()


async def list_knowledge_documents(
    connection: psycopg.AsyncConnection,
    *,
    brand_id: int,
) -> tuple[str | None, list[dict[str, Any]]]:
    async with connection.cursor() as cursor:
        await cursor.execute("SELECT name FROM brands WHERE id = %s", (brand_id,))
        brand = await cursor.fetchone()
        if brand is None:
            return None, []

        await cursor.execute(
            """
            SELECT
                kd.id,
                kd.title,
                kd.content,
                kd.created_at,
                COUNT(kc.id)::int AS chunk_count
            FROM knowledge_documents kd
            LEFT JOIN knowledge_chunks kc
              ON kc.document_id = kd.id
             AND kc.brand_id = kd.brand_id
            WHERE kd.brand_id = %s
            GROUP BY kd.id, kd.title, kd.content, kd.created_at
            ORDER BY kd.title ASC
            """,
            (brand_id,),
        )
        return brand["name"], await cursor.fetchall()


async def fetch_brand_analytics(
    connection: psycopg.AsyncConnection,
    *,
    brand_id: int,
) -> dict[str, Any] | None:
    async with connection.cursor() as cursor:
        await cursor.execute(
            """
            SELECT
                b.id AS brand_id,
                b.name AS brand_name,
                (
                    SELECT COUNT(*)::int
                    FROM conversations c
                    WHERE c.brand_id = b.id
                ) AS total_conversations,
                (
                    SELECT COUNT(*)::int
                    FROM messages m
                    WHERE m.brand_id = b.id
                ) AS total_messages,
                (
                    SELECT COUNT(*)::int
                    FROM reply_logs rl
                    WHERE rl.brand_id = b.id
                ) AS total_reply_logs,
                (
                    SELECT COUNT(*)::int
                    FROM reply_logs rl
                    WHERE rl.brand_id = b.id
                      AND rl.approved_at IS NOT NULL
                ) AS approved_reply_logs,
                (
                    SELECT AVG(rl.similarity_score)::double precision
                    FROM reply_logs rl
                    WHERE rl.brand_id = b.id
                ) AS avg_similarity_score
            FROM brands b
            WHERE b.id = %s
            """,
            (brand_id,),
        )
        summary = await cursor.fetchone()
        if summary is None:
            return None

        await cursor.execute(
            """
            SELECT confidence_flag, COUNT(*)::int AS count
            FROM reply_logs
            WHERE brand_id = %s
            GROUP BY confidence_flag
            ORDER BY count DESC, confidence_flag ASC
            """,
            (brand_id,),
        )
        confidence_breakdown = await cursor.fetchall()

        await cursor.execute(
            """
            SELECT
                rl.id AS reply_log_id,
                rl.conversation_id,
                cu.name AS customer_name,
                rl.confidence_flag,
                rl.guardrail_applied,
                rl.approved_at,
                rl.timestamp
            FROM reply_logs rl
            JOIN conversations c
              ON c.id = rl.conversation_id
             AND c.brand_id = rl.brand_id
            JOIN customers cu
              ON cu.id = c.customer_id
             AND cu.brand_id = c.brand_id
            WHERE rl.brand_id = %s
            ORDER BY rl.timestamp DESC, rl.id DESC
            LIMIT 10
            """,
            (brand_id,),
        )
        recent_reply_logs = await cursor.fetchall()

    return {
        **summary,
        "confidence_breakdown": confidence_breakdown,
        "recent_reply_logs": recent_reply_logs,
    }


async def retrieve_chunks(
    connection: psycopg.AsyncConnection,
    *,
    brand_id: int,
    embedding: list[float],
    limit: int = 3,
) -> list[dict[str, Any]]:
    vector = vector_literal(embedding)
    async with connection.cursor() as cursor:
        await cursor.execute(
            """
            SELECT
                kc.id,
                kd.title,
                kc.content,
                1 - (kc.embedding <=> %s::vector) AS similarity
            FROM knowledge_chunks kc
            JOIN knowledge_documents kd
              ON kd.id = kc.document_id
             AND kd.brand_id = kc.brand_id
            WHERE kc.brand_id = %s
            ORDER BY kc.embedding <=> %s::vector ASC
            LIMIT %s
            """,
            (vector, brand_id, vector, limit),
        )
        return await cursor.fetchall()


async def retrieve_chunks_by_terms(
    connection: psycopg.AsyncConnection,
    *,
    brand_id: int,
    terms: list[str],
    limit: int = 6,
) -> list[dict[str, Any]]:
    if not terms:
        return []

    async with connection.cursor() as cursor:
        await cursor.execute(
            """
            SELECT
                kc.id,
                kd.title,
                kc.content,
                0.0 AS similarity
            FROM knowledge_chunks kc
            JOIN knowledge_documents kd
              ON kd.id = kc.document_id
             AND kd.brand_id = kc.brand_id
            WHERE kc.brand_id = %s
            ORDER BY kc.id ASC
            """,
            (brand_id,),
        )
        rows = await cursor.fetchall()

    scored_rows: list[dict[str, Any]] = []
    for row in rows:
        title = row["title"].lower()
        content = row["content"].lower()
        title_score = 0.0
        content_score = 0.0

        for term in terms:
            normalized = term.lower()
            if normalized in title:
                title_score += 0.34
            if normalized in content:
                content_score += 0.26

        similarity = max(title_score, content_score)
        if similarity > 0:
            scored_rows.append({**row, "similarity": similarity})

    scored_rows.sort(key=lambda row: (float(row["similarity"]), -int(row["id"])), reverse=True)
    return scored_rows[:limit]


async def insert_reply_log(
    connection: psycopg.AsyncConnection,
    *,
    brand_id: int,
    conversation_id: int,
    customer_message: str,
    retrieved_context: list[dict[str, Any]],
    ai_response: str | None,
    suggested_response: str,
    confidence_flag: str,
    similarity_score: float | None,
    guardrail_applied: bool,
) -> int:
    async with connection.cursor() as cursor:
        await cursor.execute(
            """
            INSERT INTO reply_logs (
                brand_id, conversation_id, customer_message, retrieved_context,
                ai_response, suggested_response, confidence_flag,
                similarity_score, guardrail_applied, timestamp
            )
            VALUES (%s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s, NOW())
            RETURNING id
            """,
            (
                brand_id,
                conversation_id,
                customer_message,
                json.dumps(retrieved_context),
                ai_response,
                suggested_response,
                confidence_flag,
                similarity_score,
                guardrail_applied,
            ),
        )
        row = await cursor.fetchone()
    return row["id"]


async def approve_reply_log(
    connection: psycopg.AsyncConnection,
    *,
    log_id: int,
    conversation_id: int,
    edited_response: str | None,
    final_response: str,
    confidence_flag: str,
    guardrail_applied: bool,
) -> dict[str, Any] | None:
    async with connection.cursor() as cursor:
        await cursor.execute(
            """
            UPDATE reply_logs
            SET edited_response = %s,
                final_response = %s,
                confidence_flag = %s,
                guardrail_applied = guardrail_applied OR %s,
                approved_at = NOW()
            WHERE id = %s AND conversation_id = %s
            RETURNING id AS reply_log_id, edited_response, final_response, approved_at
            """,
            (
                edited_response,
                final_response,
                confidence_flag,
                guardrail_applied,
                log_id,
                conversation_id,
            ),
        )
        return await cursor.fetchone()


async def fetch_reply_log_context(
    connection: psycopg.AsyncConnection,
    *,
    log_id: int,
    conversation_id: int,
) -> dict[str, Any] | None:
    async with connection.cursor() as cursor:
        await cursor.execute(
            """
            SELECT
                rl.customer_message,
                c.brand_id,
                b.name AS brand_name,
                cu.name AS customer_name,
                rl.confidence_flag,
                rl.guardrail_applied,
                o.delivered_at AS order_delivered_at
            FROM reply_logs rl
            JOIN conversations c
              ON c.id = rl.conversation_id
             AND c.brand_id = rl.brand_id
            JOIN brands b ON b.id = c.brand_id
            JOIN customers cu
              ON cu.id = c.customer_id
             AND cu.brand_id = c.brand_id
            LEFT JOIN orders o
              ON o.id = c.order_id
             AND o.brand_id = c.brand_id
             AND o.customer_id = c.customer_id
            WHERE rl.id = %s
              AND rl.conversation_id = %s
              AND rl.brand_id = c.brand_id
            """,
            (log_id, conversation_id),
        )
        return await cursor.fetchone()