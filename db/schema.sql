CREATE TABLE IF NOT EXISTS deep_agent_runs (
    id TEXT PRIMARY KEY,
    query TEXT NOT NULL,
    answer TEXT NOT NULL,
    search_language TEXT NOT NULL DEFAULT 'any',
    search_date TEXT,
    model_name TEXT,
    status TEXT NOT NULL DEFAULT 'completed',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS deep_agent_process_messages (
    id BIGSERIAL PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES deep_agent_runs(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    message_type TEXT NOT NULL,
    title TEXT NOT NULL,
    tool_name TEXT,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_deep_agent_runs_created_at
    ON deep_agent_runs(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_deep_agent_process_messages_run_id
    ON deep_agent_process_messages(run_id, position);
