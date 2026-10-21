-- Schéma pro telemetrii vodoměrů.
-- Skript je idempotentní: založí tabulku v nové databázi a v existující
-- doplní sloupce přidané v novějších verzích. Docker Compose ho spouští
-- automaticky při prvním startu, ručně: psql -f db/init.sql

CREATE TABLE IF NOT EXISTS meter_readings (
    id                     BIGSERIAL PRIMARY KEY,
    meter_id               VARCHAR(64)    NOT NULL,
    timestamp              TIMESTAMPTZ    NOT NULL,
    cumulative_consumption NUMERIC(14, 4),
    battery_level          SMALLINT       NOT NULL CHECK (battery_level BETWEEN 0 AND 100),
    signal_strength        SMALLINT       NOT NULL,
    is_anomaly             BOOLEAN        NOT NULL DEFAULT FALSE,
    anomaly_reason         VARCHAR(32),
    received_at            TIMESTAMPTZ    NOT NULL DEFAULT now()
);

ALTER TABLE meter_readings ADD COLUMN IF NOT EXISTS is_anomaly     BOOLEAN     NOT NULL DEFAULT FALSE;
ALTER TABLE meter_readings ADD COLUMN IF NOT EXISTS anomaly_reason VARCHAR(32);
ALTER TABLE meter_readings ADD COLUMN IF NOT EXISTS received_at    TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE INDEX IF NOT EXISTS idx_meter_readings_meter_time
    ON meter_readings (meter_id, timestamp DESC);
