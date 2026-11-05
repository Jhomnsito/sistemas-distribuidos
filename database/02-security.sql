BEGIN;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS owner_id text;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS private_payload text;
ALTER TABLE orders ALTER COLUMN customer DROP NOT NULL;
ALTER TABLE orders ALTER COLUMN item DROP NOT NULL;
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'orders'::regclass AND conname = 'orders_private_fields') THEN
        ALTER TABLE orders ADD CONSTRAINT orders_private_fields CHECK (
            (private_payload IS NULL AND customer IS NOT NULL AND item IS NOT NULL)
            OR (private_payload IS NOT NULL AND customer IS NULL AND item IS NULL)
        );
    END IF;
END $$;
CREATE INDEX IF NOT EXISTS orders_owner_latest ON orders (owner_id, created_at DESC, id DESC);
ALTER TABLE request_log ADD COLUMN IF NOT EXISTS actor text NOT NULL DEFAULT 'admin';
CREATE TABLE IF NOT EXISTS order_audit (
    event_id uuid PRIMARY KEY,
    happened_at timestamptz NOT NULL DEFAULT now(),
    action text NOT NULL CHECK (action IN ('creado', 'editado', 'estado', 'eliminado')),
    from_status text,
    to_status text,
    actor_role text NOT NULL CHECK (actor_role IN ('admin', 'cliente'))
);
CREATE INDEX IF NOT EXISTS audit_latest ON order_audit (happened_at DESC);
GRANT SELECT, INSERT ON order_audit TO orders_app;
COMMIT;
