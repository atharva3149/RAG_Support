from __future__ import annotations

import re
from datetime import datetime, timezone


def _infer_policy_topic(customer_message: str) -> str | None:
    message = customer_message.lower()
    if any(term in message for term in ("gift wrap", "gift-wrap", "gift wrapping", "gift packaging")):
        return "gift_wrapping"
    if (
        "ship" in message
        and any(term in message for term in ("canada", "international", "outside", "country", "abroad"))
    ):
        return "shipping_destination"
    if any(term in message for term in ("warranty", "guarantee", "replacement period")):
        return "warranty"
    return None


def insufficient_info_response(
    brand_name: str,
    *,
    customer_message: str | None = None,
    customer_name: str | None = None,
) -> str:
    greeting = f"Thanks for checking, {customer_name}. " if customer_name else ""
    if customer_message:
        topic = _infer_policy_topic(customer_message)
        if topic == "gift_wrapping":
            return (
                f"{greeting}I could not find a confirmed gift-wrapping policy in {brand_name}'s current "
                "knowledge base, so I do not want to promise this yet. Please share your order number "
                "and our support team will confirm whether gift wrapping is available for your order."
            )
        if topic == "shipping_destination":
            return (
                f"{greeting}I could not find a confirmed shipping-destination policy in {brand_name}'s "
                "current knowledge base, so I do not want to give an incorrect promise. Please share "
                "your destination and order details, and support will confirm availability and next steps."
            )
        if topic == "warranty":
            return (
                f"{greeting}I could not find a confirmed warranty policy in {brand_name}'s current "
                "knowledge base. Please share your order number and the product issue so support can "
                "review eligibility and confirm the correct next step."
            )

    return (
        f"{greeting}I want to make sure we give you the right next step. I could not find enough "
        f"confirmed information in {brand_name}'s policies for this situation, so a support "
        "specialist will need to review it before we promise a resolution."
    )


_DAY_PATTERNS = (
    re.compile(r"\b(\d+)\s*(?:calendar\s*)?days?\s*(?:ago|old)\b", re.IGNORECASE),
    re.compile(r"\b(\d+)\s*days?\s*(?:since|after)\s+(?:delivery|receipt)\b", re.IGNORECASE),
    re.compile(r"\b(?:received|delivered|arrived)\b[^.?!\n]{0,80}?\b(\d+)\s*days?\b", re.IGNORECASE),
)


def days_since_delivery(message: str) -> int | None:
    for pattern in _DAY_PATTERNS:
        match = pattern.search(message)
        if match:
            return int(match.group(1))
    return None


def contains_confident_refund_promise(response: str) -> bool:
    lowered = response.lower()
    promise_patterns = (
        r"\bwe(?:'ll| will) refund\b",
        r"\bwe can refund\b",
        r"\bwe(?:'ll| will| can) reimburse\b",
        r"\bwe(?:'ll| will) issue (?:your )?refund\b",
        r"\byou(?:'ll| will) receive a refund\b",
        r"\byou(?:'ll| will) get (?:your )?money back\b",
        r"\b(?:your )?refund will be processed\b",
        r"\byour refund (?:has been|is) approved\b",
        r"\bapproved (?:for|a) refund\b",
        r"\beligible for a refund\b",
        r"\bwe can issue your refund\b",
        r"\bwe have issued your refund\b",
    )
    return any(re.search(pattern, lowered) for pattern in promise_patterns)


def _review_response(brand_name: str, customer_name: str | None = None) -> str:
    greeting = f"Thanks for flagging this, {customer_name}." if customer_name else "Thanks for flagging this."
    return (
        f"{greeting} {brand_name}'s policy allows automatic refund review within 7 days of delivery. "
        "Because this request is outside that window, I cannot promise a refund here. Please share "
        "your order number and photos of the damaged bottle and packaging so our support team can "
        "review the circumstances and confirm the next step."
    )


def _order_age_in_days(delivered_at: datetime | None, now: datetime | None = None) -> int | None:
    if delivered_at is None:
        return None
    current = now or datetime.now(timezone.utc)
    if delivered_at.tzinfo is None:
        delivered_at = delivered_at.replace(tzinfo=timezone.utc)
    return max(0, (current - delivered_at).days)


def apply_policy_guardrail(
    customer_message: str,
    response: str,
    *,
    brand_name: str = "HydroFlow",
    customer_name: str | None = None,
    delivered_at: datetime | None = None,
    now: datetime | None = None,
) -> tuple[str, bool, str]:
    message_age = days_since_delivery(customer_message)
    order_age = _order_age_in_days(delivered_at, now)
    refund_requested = any(
        keyword in customer_message.lower() for keyword in ("refund", "money back", "reimburse")
    )
    outside_window = (message_age is not None and message_age > 7) or (order_age is not None and order_age > 7)
    conflicting_age = (
        message_age is not None
        and order_age is not None
        and abs(message_age - order_age) > 1
    )
    if refund_requested and (outside_window or conflicting_age):
        return _review_response(brand_name, customer_name), True, "review_required"
    if contains_confident_refund_promise(response):
        return (
            "I do not want to promise an outcome before the order details are reviewed. "
            "Please share your order number and the delivery date so our support team can "
            "confirm whether the refund policy applies.",
            True,
            "review_required",
        )
    return response.strip(), False, "grounded"