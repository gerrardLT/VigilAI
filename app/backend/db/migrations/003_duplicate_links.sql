-- Migration 003: duplicate_links table
-- Supports the Cross-Domain Deduplicator service (Requirement 19)

CREATE TABLE IF NOT EXISTS duplicate_links (
    id TEXT PRIMARY KEY,
    source_domain TEXT NOT NULL,
    source_id TEXT NOT NULL,
    target_domain TEXT NOT NULL,
    target_id TEXT NOT NULL,
    similarity_score REAL,
    match_type TEXT NOT NULL,
    overridden BOOLEAN DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_duplicate_links_source
    ON duplicate_links(source_domain, source_id);

CREATE INDEX IF NOT EXISTS idx_duplicate_links_target
    ON duplicate_links(target_domain, target_id);

CREATE INDEX IF NOT EXISTS idx_duplicate_links_overridden
    ON duplicate_links(overridden);
