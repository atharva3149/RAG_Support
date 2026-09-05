from __future__ import annotations

import sys
from pathlib import Path

import psycopg

# Allow `python scripts/seed.py` from the backend directory as well as
# `python -m scripts.seed`.
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings  # noqa: E402
from app.services.embeddings import embed_text, vector_literal  # noqa: E402


POLICIES = [
    {
        "title": "Return policy",
        "content": (
            "Returns are available for unused HydroFlow products within 30 days of delivery. "
            "The item must be in its original packaging with all accessories included.\n\n"
            "For a product that arrives damaged or broken, contact support within 7 days of delivery "
            "with the order number and clear photos of the packaging and product. We will review the "
            "evidence and provide the next step.\n\n"
            "Approved returns receive a prepaid return label when HydroFlow is responsible for the issue. "
            "Please do not mail an item back until support has confirmed the return instructions."
        ),
    },
    {
        "title": "Refund policy",
        "content": (
            "Refunds are only permitted within 7 days of delivery, after the return or damage review is "
            "approved. The 7-day window is measured from the carrier delivery date, not the date the "
            "request is submitted.\n\n"
            "If approved, the refund is issued to the original payment method within 5 to 7 business days "
            "after HydroFlow receives the returned item, or after a damaged-delivery review is completed. "
            "Shipping fees are refundable only when the product arrived damaged or HydroFlow made an error.\n\n"
            "Requests outside the 7-day refund window are not automatically eligible. Support may review "
            "the circumstances, but agents must not promise a refund before that review is complete."
        ),
    },
    {
        "title": "Shipping policy",
        "content": (
            "Standard orders are processed within 1 to 2 business days and usually arrive within 3 to 5 "
            "business days after dispatch. Tracking is emailed when the order leaves our warehouse.\n\n"
            "If tracking has not updated for 3 business days, or an order is marked delivered but cannot be "
            "found, contact support with the order number so the carrier investigation can be started.\n\n"
            "Customers should report visible delivery damage within 7 days of delivery and keep the shipping "
            "box and product until support confirms whether they are needed for the review."
        ),
    },
    {
        "title": "Cancellation policy",
        "content": (
            "An order can be cancelled at no charge while it is still pending and has not entered warehouse "
            "processing. Contact support as soon as possible with the order number.\n\n"
            "Once an order has shipped, it cannot be cancelled. The customer may request a return after "
            "delivery under the return policy, and should wait for support's instructions before sending it.\n\n"
            "If a cancellation is approved, any refund is sent to the original payment method within 5 to 7 "
            "business days."
        ),
    },
]


SCENARIOS = [
    {
        "customer_name": "Maya Patel",
        "customer_email": "maya.patel@example.com",
        "order_external_id": "HF-10482",
        "order_item_name": "FlowSip Insulated Bottle",
        "order_quantity": 1,
        "order_total_amount": 34.00,
        "order_currency": "USD",
        "order_status": "Delivered",
        "order_delivered_days": 2,
        "conversation_slug": "maya-patel-broken-bottle",
        "conversation_status": "open",
        "messages": [
            {
                "sender": "customer",
                "body": "Hi, I need help with my recent order.",
                "external_id": "seed-msg-1",
                "created_minutes": 240,
            },
            {
                "sender": "agent",
                "body": "Of course, Maya. What went wrong with the order?",
                "external_id": "seed-msg-2",
                "created_minutes": 180,
            },
            {
                "sender": "customer",
                "body": "My order was delivered but the bottle is broken. What can I do?",
                "external_id": "seed-msg-3",
                "created_minutes": 120,
            },
        ],
    },
    {
        "customer_name": "Arjun Mehta",
        "customer_email": "arjun.mehta@example.com",
        "order_external_id": "HF-10991",
        "order_item_name": "HydroFlow Travel Flask",
        "order_quantity": 1,
        "order_total_amount": 42.00,
        "order_currency": "USD",
        "order_status": "Delivered",
        "order_delivered_days": 20,
        "conversation_slug": "arjun-mehta-refund-after-20-days",
        "conversation_status": "open",
        "messages": [
            {
                "sender": "customer",
                "body": "I received this 20 days ago. Can I get a refund?",
                "external_id": "seed-msg-4",
                "created_minutes": 90,
            }
        ],
    },
    {
        "customer_name": "Sara Kim",
        "customer_email": "sara.kim@example.com",
        "order_external_id": "HF-11008",
        "order_item_name": "HydroFlow Starter Set",
        "order_quantity": 2,
        "order_total_amount": 68.00,
        "order_currency": "USD",
        "order_status": "Pending",
        "order_delivered_days": 0,
        "conversation_slug": "sara-kim-ship-to-canada",
        "conversation_status": "open",
        "messages": [
            {
                "sender": "customer",
                "body": "Do you ship to Canada?",
                "external_id": "seed-msg-5",
                "created_minutes": 70,
            }
        ],
    },
    {
        "customer_name": "Leo Fernandez",
        "customer_email": "leo.fernandez@example.com",
        "order_external_id": "HF-11021",
        "order_item_name": "HydroFlow Gift Bundle",
        "order_quantity": 1,
        "order_total_amount": 55.00,
        "order_currency": "USD",
        "order_status": "Pending",
        "order_delivered_days": 0,
        "conversation_slug": "leo-fernandez-gift-wrapping",
        "conversation_status": "open",
        "messages": [
            {
                "sender": "customer",
                "body": "What is your policy on gift wrapping?",
                "external_id": "seed-msg-6",
                "created_minutes": 50,
            }
        ],
    },
]


def split_into_chunks(content: str, max_words: int = 70, overlap_words: int = 10) -> list[str]:
    """Keep policy paragraphs intact where possible and overlap long boundaries slightly."""
    paragraphs = [paragraph.strip() for paragraph in content.split("\n\n") if paragraph.strip()]
    chunks: list[str] = []

    for paragraph in paragraphs:
        words = paragraph.split()
        if len(words) <= max_words:
            current = paragraph
            if chunks:
                current = " ".join(chunks[-1].split()[-overlap_words:] + words)
            chunks.append(current)
            continue

        start = 0
        while start < len(words):
            end = min(start + max_words, len(words))
            current_words = words[start:end]
            if chunks and start == 0:
                current_words = chunks[-1].split()[-overlap_words:] + current_words
            chunks.append(" ".join(current_words))
            if end == len(words):
                break
            start = end - overlap_words

    return chunks


def seed() -> None:
    settings = get_settings()
    print("Loading local embedding model...")
    # Load once up front so a missing model fails before a partial transaction.
    embed_text("HydroFlow return policy")

    with psycopg.connect(settings.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO brands (name, slug)
                VALUES (%s, %s)
                ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name
                RETURNING id
                """,
                ("HydroFlow", "hydroflow"),
            )
            brand_id = cursor.fetchone()[0]

            for scenario in SCENARIOS:
                cursor.execute(
                    """
                    INSERT INTO customers (brand_id, name, email)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (brand_id, email) DO UPDATE SET name = EXCLUDED.name
                    RETURNING id
                    """,
                    (brand_id, scenario["customer_name"], scenario["customer_email"]),
                )
                customer_id = cursor.fetchone()[0]

                cursor.execute(
                    """
                    INSERT INTO orders (
                        brand_id, customer_id, external_id, item_name, quantity,
                        total_amount, currency, status, delivered_at
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s,
                        NOW() - (%s::text || ' days')::interval
                    )
                    ON CONFLICT (brand_id, external_id) DO UPDATE SET
                        customer_id = EXCLUDED.customer_id,
                        item_name = EXCLUDED.item_name,
                        quantity = EXCLUDED.quantity,
                        total_amount = EXCLUDED.total_amount,
                        currency = EXCLUDED.currency,
                        status = EXCLUDED.status,
                        delivered_at = EXCLUDED.delivered_at
                    RETURNING id
                    """,
                    (
                        brand_id,
                        customer_id,
                        scenario["order_external_id"],
                        scenario["order_item_name"],
                        scenario["order_quantity"],
                        scenario["order_total_amount"],
                        scenario["order_currency"],
                        scenario["order_status"],
                        scenario["order_delivered_days"],
                    ),
                )
                order_id = cursor.fetchone()[0]

                cursor.execute(
                    """
                    INSERT INTO conversations (brand_id, customer_id, order_id, slug, status)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (slug) DO UPDATE SET
                        brand_id = EXCLUDED.brand_id,
                        customer_id = EXCLUDED.customer_id,
                        order_id = EXCLUDED.order_id,
                        status = EXCLUDED.status
                    RETURNING id
                    """,
                    (
                        brand_id,
                        customer_id,
                        order_id,
                        scenario["conversation_slug"],
                        scenario["conversation_status"],
                    ),
                )
                conversation_id = cursor.fetchone()[0]

                for message in scenario["messages"]:
                    cursor.execute(
                        """
                        INSERT INTO messages (brand_id, conversation_id, sender, body, external_id, created_at)
                        VALUES (%s, %s, %s, %s, %s, NOW() - (%s::text || ' minutes')::interval)
                        ON CONFLICT (brand_id, external_id) DO UPDATE SET
                            conversation_id = EXCLUDED.conversation_id,
                            body = EXCLUDED.body,
                            created_at = EXCLUDED.created_at
                        """,
                        (
                            brand_id,
                            conversation_id,
                            message["sender"],
                            message["body"],
                            message["external_id"],
                            message["created_minutes"],
                        ),
                    )

            total_chunks = 0
            for policy in POLICIES:
                cursor.execute(
                    """
                    INSERT INTO knowledge_documents (brand_id, title, content)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (brand_id, title) DO UPDATE SET content = EXCLUDED.content
                    RETURNING id
                    """,
                    (brand_id, policy["title"], policy["content"]),
                )
                document_id = cursor.fetchone()[0]
                cursor.execute("DELETE FROM knowledge_chunks WHERE document_id = %s", (document_id,))

                for index, chunk in enumerate(split_into_chunks(policy["content"])):
                    embedding = vector_literal(embed_text(chunk))
                    cursor.execute(
                        """
                        INSERT INTO knowledge_chunks (
                            brand_id, document_id, chunk_index, content, embedding
                        )
                        VALUES (%s, %s, %s, %s, %s::vector)
                        """,
                        (brand_id, document_id, index, chunk, embedding),
                    )
                    total_chunks += 1

        connection.commit()

    print(f"Seeded HydroFlow with {total_chunks} policy chunks.")


if __name__ == "__main__":
    seed()
