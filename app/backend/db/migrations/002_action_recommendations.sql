-- Migration 002: action_recommendations table
-- Supports the Action Automator service (Requirement 17)

CREATE TABLE IF NOT EXISTS action_recommendations (
    id TEXT PRIMARY KEY,
    activity_id TEXT NOT NULL,
    action_type TEXT NOT NULL,
    label TEXT NOT NULL,
    deadline TEXT,
    status TEXT DEFAULT 'pending',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    executed_at TEXT,
    FOREIGN KEY (activity_id) REFERENCES activities(id)
);

CREATE INDEX IF NOT EXISTS idx_action_recommendations_activity
    ON action_recommendations(activity_id);

CREATE INDEX IF NOT EXISTS idx_action_recommendations_status
    ON action_recommendations(status);
