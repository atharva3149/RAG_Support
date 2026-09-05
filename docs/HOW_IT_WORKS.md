# How It Works

This document explains the runtime flow of the Datastraw CX Reply Assistant.

## User flow

1. A support agent opens a conversation in the frontend.
2. The frontend loads conversation details from the backend.
3. When the agent clicks `Generate reply`, the backend:
   - resolves the conversation and brand from PostgreSQL,
   - embeds the latest customer message locally,
   - retrieves the most relevant brand knowledge chunks,
   - checks retrieval confidence,
   - calls OpenRouter only when retrieval is confident,
   - applies guardrails before returning the draft,
   - logs the generation attempt to `reply_logs`.
4. The agent can edit the draft and approve it.
5. Approval stores the final response and approval timestamp.

## Backend layers

- `app/api/`: FastAPI route handlers.
- `app/core/`: configuration and database connection helpers.
- `app/models/`: Pydantic request/response models.
- `app/repositories/`: SQL queries and persistence.
- `app/services/`: embeddings, retrieval confidence, guardrails, and LLM orchestration.

## Retrieval and generation rules

The backend does not send every message directly to the LLM.

It first retrieves policy chunks and then checks confidence with three rules:

- top similarity must be at least `SIMILARITY_THRESHOLD`
- top similarity minus second similarity must be at least `SIMILARITY_MIN_MARGIN`
- or the top similarity must exceed `SIMILARITY_STRONG_MATCH_THRESHOLD`

If retrieval is weak, the backend returns an `insufficient_info` response instead of asking the model to guess.

## Guardrails

The assistant must not promise refunds outside policy windows.

Examples:

- `I received this 20 days ago. Can I get a refund?`
  - retrieval should find refund policy
  - guardrail forces `review_required`
  - draft avoids promising a refund

- `What is your policy on gift wrapping?`
  - no matching knowledge exists
  - retrieval stays below threshold
  - backend returns a topic-specific fallback asking for review

## Fallback behavior

If OpenRouter is unavailable, rate-limited, or the selected model is invalid, the backend does not fail the request.

Instead it returns:

- `model_unavailable`
- a deterministic local draft based on known policy context

This keeps the demo usable even when external model access is unreliable.