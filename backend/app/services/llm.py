from __future__ import annotations

import httpx

from app.core.config import Settings


class LLMUnavailableError(RuntimeError):
    """Raised when generation cannot be completed by OpenRouter."""


async def generate_with_openrouter(
    settings: Settings,
    *,
    brand_name: str,
    customer_message: str,
    context: str,
) -> str:
    if not settings.openrouter_api_key:
        raise LLMUnavailableError("OPENROUTER_API_KEY is not configured")

    system_prompt = f"""You are a careful customer-support reply assistant for {brand_name}.

Answer only from the policy context supplied below. Do not invent policy details, exceptions,
refund approvals, delivery dates, compensation, or actions that are not in the context.
If the context does not fully cover the customer's specific situation, say that plainly and
recommend human review instead of promising an outcome. Treat dates and eligibility windows
as hard conditions. In particular, never promise a refund when the customer's request is
outside a stated refund window. Write a concise, empathetic reply addressed to the customer.
Do not mention that you are an AI or refer to "the context" in the customer-facing reply.

POLICY CONTEXT:
{context}"""
    user_prompt = f"Customer message:\n{customer_message}\n\nDraft the safest accurate reply."

    payload = {
        "model": settings.openrouter_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 280,
    }
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://datastraw-cx-reply-assistant.vercel.app",
        "X-Title": "Datastraw CX Reply Assistant",
    }

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(45.0, connect=10.0)) as client:
            response = await client.post(
                f"{settings.openrouter_base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise LLMUnavailableError("OpenRouter generation failed") from exc

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMUnavailableError("OpenRouter returned an invalid response") from exc

    if not isinstance(content, str) or not content.strip():
        raise LLMUnavailableError("OpenRouter returned an empty response")
    return content.strip()