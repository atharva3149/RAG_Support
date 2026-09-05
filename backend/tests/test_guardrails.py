from datetime import datetime, timezone

from app.services.guardrails import (
    apply_policy_guardrail,
    contains_confident_refund_promise,
    days_since_delivery,
    insufficient_info_response,
)


def test_extracts_delivery_age_from_refund_question() -> None:
    assert days_since_delivery("I received this 20 days ago, can I get a refund?") == 20
    assert days_since_delivery("Can I request a refund 20 days after delivery?") == 20


def test_twenty_day_refund_request_never_promises_refund() -> None:
    draft, applied, confidence_flag = apply_policy_guardrail(
        "I received this 20 days ago, can I get a refund?",
        "Absolutely, we will refund your order right away.",
    )

    assert applied is True
    assert confidence_flag == "review_required"
    assert "promise a refund" in draft
    assert contains_confident_refund_promise(draft) is False


def test_in_window_damage_request_can_remain_grounded() -> None:
    draft, applied, confidence_flag = apply_policy_guardrail(
        "My bottle arrived broken yesterday. What should I do?",
        "Please send photos of the damaged bottle and packaging for our review.",
    )

    assert applied is False
    assert confidence_flag == "grounded"
    assert "photos" in draft


def test_persisted_delivery_date_wins_over_a_customer_claim() -> None:
    draft, applied, confidence_flag = apply_policy_guardrail(
        "I received this yesterday, can I get a refund?",
        "Your refund will be processed today.",
        delivered_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        now=datetime(2025, 1, 21, tzinfo=timezone.utc),
    )

    assert applied is True
    assert confidence_flag == "review_required"
    assert "cannot promise a refund" in draft


def test_common_refund_promise_phrasings_are_detected() -> None:
    assert contains_confident_refund_promise("We can refund your order today.") is True
    assert contains_confident_refund_promise("You will get your money back shortly.") is True
    assert contains_confident_refund_promise("Your refund will be processed in 5 days.") is True


def test_insufficient_info_for_gift_wrapping_is_specific() -> None:
    response = insufficient_info_response(
        "HydroFlow",
        customer_message="What's your policy on gift wrapping?",
        customer_name="Maya",
    )

    assert "gift-wrapping policy" in response
    assert "Maya" in response


def test_insufficient_info_for_shipping_destination_is_specific() -> None:
    response = insufficient_info_response(
        "HydroFlow",
        customer_message="Do you ship to Canada?",
    )

    assert "shipping-destination policy" in response
    assert "HydroFlow" in response
