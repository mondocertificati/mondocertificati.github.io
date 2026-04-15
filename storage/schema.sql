-- Esegui questo SQL nell'SQL Editor di Supabase per creare le tabelle necessarie.

-- Edizioni della newsletter
CREATE TABLE IF NOT EXISTS newsletter_issues (
    id                      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    created_at              TIMESTAMPTZ DEFAULT now(),
    week_number             INT NOT NULL,
    year                    INT NOT NULL,
    beehiiv_post_id         TEXT,
    status                  TEXT DEFAULT 'draft',
    certificates_featured   JSONB,
    UNIQUE (week_number, year)
);

-- Storico certificati (per tracking nel tempo)
CREATE TABLE IF NOT EXISTS certificates_history (
    id                      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    isin                    TEXT NOT NULL,
    scraped_at              TIMESTAMPTZ DEFAULT now(),
    opportunity_score       NUMERIC,
    distanza_barriera_perc  NUMERIC,
    prezzo_attuale          NUMERIC
);

-- Indice per ricerche rapide per ISIN
CREATE INDEX IF NOT EXISTS idx_certificates_history_isin
    ON certificates_history (isin);

-- Indice per ricerche per data
CREATE INDEX IF NOT EXISTS idx_certificates_history_scraped_at
    ON certificates_history (scraped_at DESC);
