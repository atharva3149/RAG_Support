-- Datastraw Part 1: CX reply assistant schema.
-- The vector dimension matches sentence-transformers/all-MiniLM-L6-v2.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS brands (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS customers (
    id BIGSERIAL PRIMARY KEY,
    brand_id BIGINT NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (brand_id, email),
    UNIQUE (brand_id, id)
);

CREATE TABLE IF NOT EXISTS orders (
    id BIGSERIAL PRIMARY KEY,
    brand_id BIGINT NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    customer_id BIGINT NOT NULL,
    external_id TEXT NOT NULL,
    item_name TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    total_amount NUMERIC(10, 2) NOT NULL CHECK (total_amount >= 0),
    currency CHAR(3) NOT NULL DEFAULT 'USD',
    status TEXT NOT NULL,
    delivered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (brand_id, external_id),
    UNIQUE (brand_id, id),
    UNIQUE (brand_id, id, customer_id),
    FOREIGN KEY (brand_id, customer_id)
        REFERENCES customers(brand_id, id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS conversations (
    id BIGSERIAL PRIMARY KEY,
    brand_id BIGINT NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    customer_id BIGINT NOT NULL,
    order_id BIGINT,
    slug TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'open',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (brand_id, id),
    FOREIGN KEY (brand_id, customer_id)
        REFERENCES customers(brand_id, id) ON DELETE CASCADE,
    FOREIGN KEY (brand_id, order_id, customer_id)
        REFERENCES orders(brand_id, id, customer_id)
        ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS messages (
    id BIGSERIAL PRIMARY KEY,
    brand_id BIGINT NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    conversation_id BIGINT NOT NULL,
    sender TEXT NOT NULL CHECK (sender IN ('customer', 'agent')),
    body TEXT NOT NULL,
    external_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (brand_id, external_id),
    FOREIGN KEY (brand_id, conversation_id)
        REFERENCES conversations(brand_id, id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS knowledge_documents (
    id BIGSERIAL PRIMARY KEY,
    brand_id BIGINT NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (brand_id, title),
    UNIQUE (brand_id, id)
);

CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id BIGSERIAL PRIMARY KEY,
    brand_id BIGINT NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    document_id BIGINT NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(384) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (document_id, chunk_index),
    FOREIGN KEY (brand_id, document_id)
        REFERENCES knowledge_documents(brand_id, id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS reply_logs (
    id BIGSERIAL PRIMARY KEY,
    brand_id BIGINT NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    conversation_id BIGINT NOT NULL,
    customer_message TEXT NOT NULL,
    retrieved_context JSONB NOT NULL DEFAULT '[]'::JSONB,
    ai_response TEXT,
    suggested_response TEXT,
    edited_response TEXT,
    final_response TEXT,
    confidence_flag TEXT NOT NULL CHECK (
        confidence_flag IN ('grounded', 'insufficient_info', 'model_unavailable', 'review_required')
    ),
    similarity_score DOUBLE PRECISION,
    guardrail_applied BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    approved_at TIMESTAMPTZ,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (brand_id, conversation_id)
        REFERENCES conversations(brand_id, id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS customers_brand_id_idx ON customers (brand_id);
CREATE INDEX IF NOT EXISTS orders_brand_id_idx ON orders (brand_id);
CREATE INDEX IF NOT EXISTS conversations_brand_id_idx ON conversations (brand_id);
CREATE INDEX IF NOT EXISTS messages_conversation_created_idx
    ON messages (conversation_id, created_at);
CREATE INDEX IF NOT EXISTS knowledge_chunks_brand_id_idx ON knowledge_chunks (brand_id);
CREATE INDEX IF NOT EXISTS reply_logs_conversation_created_idx
    ON reply_logs (conversation_id, timestamp DESC);

-- The tenant predicate remains mandatory even after adding this ANN index.
CREATE INDEX IF NOT EXISTS knowledge_chunks_embedding_idx
    ON knowledge_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10);
