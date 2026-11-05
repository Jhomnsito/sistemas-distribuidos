CREATE TABLE orders (
    id uuid PRIMARY KEY,
    customer text NOT NULL CHECK (char_length(customer) BETWEEN 1 AND 100),
    item text NOT NULL CHECK (char_length(item) BETWEEN 1 AND 160),
    quantity integer NOT NULL CHECK (quantity BETWEEN 1 AND 999),
    status text NOT NULL CHECK (status IN ('pendiente','en_proceso','enviado','entregado')),
    version integer NOT NULL DEFAULT 1 CHECK (version >= 1),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX orders_latest ON orders (created_at DESC, id DESC);
CREATE TABLE request_log (
    key uuid PRIMARY KEY,
    fingerprint text NOT NULL,
    response jsonb
);
