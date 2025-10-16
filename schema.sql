-- Merchants (negocios)
CREATE TABLE IF NOT EXISTS merchants (
id UUID PRIMARY KEY,
name TEXT NOT NULL,
mp_access_token_enc TEXT NOT NULL, -- token cifrado con Fernet
created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
plan TEXT DEFAULT 'basic'
);


-- Devices (dispositivos ESP32)
CREATE TABLE IF NOT EXISTS devices (
id UUID PRIMARY KEY,
merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
device_serial TEXT NOT NULL UNIQUE,
device_api_key_hash TEXT NOT NULL,
status TEXT NOT NULL DEFAULT 'active', -- active | blocked | suspended
last_seen TIMESTAMPTZ,
ip_last INET
);


-- Payments (pagos/transferencias)
CREATE TABLE IF NOT EXISTS payments (
id TEXT PRIMARY KEY, -- id de MP
merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
amount NUMERIC(12,2) NOT NULL,
payer_name TEXT,
status TEXT NOT NULL,
date_created TIMESTAMPTZ NOT NULL,
created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- Índices útiles
CREATE INDEX IF NOT EXISTS idx_payments_merchant_date ON payments(merchant_id, date_created DESC);
CREATE INDEX IF NOT EXISTS idx_devices_merchant ON devices(merchant_id);