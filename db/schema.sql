CREATE TABLE IF NOT EXISTS deep_agent_runs (
    id TEXT PRIMARY KEY,
    query TEXT NOT NULL,
    answer TEXT NOT NULL,
    report_content TEXT,
    search_language TEXT NOT NULL DEFAULT 'any',
    search_date TEXT,
    model_name TEXT,
    status TEXT NOT NULL DEFAULT 'completed',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE deep_agent_runs
    ADD COLUMN IF NOT EXISTS report_content TEXT;

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

CREATE TABLE IF NOT EXISTS deep_agent_searches (
    id TEXT PRIMARY KEY,
    run_id TEXT REFERENCES deep_agent_runs(id) ON DELETE CASCADE,
    position INTEGER NOT NULL DEFAULT 0,
    query TEXT NOT NULL,
    max_results INTEGER,
    source_count INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE deep_agent_searches
    ADD COLUMN IF NOT EXISTS run_id TEXT REFERENCES deep_agent_runs(id) ON DELETE CASCADE;

ALTER TABLE deep_agent_searches
    ADD COLUMN IF NOT EXISTS position INTEGER NOT NULL DEFAULT 0;

ALTER TABLE deep_agent_searches
    ADD COLUMN IF NOT EXISTS max_results INTEGER;

ALTER TABLE deep_agent_searches
    ADD COLUMN IF NOT EXISTS source_count INTEGER;

CREATE TABLE IF NOT EXISTS deep_agent_search_sources (
    id BIGSERIAL PRIMARY KEY,
    search_id TEXT NOT NULL REFERENCES deep_agent_searches(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    snippet TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE deep_agent_search_sources
    ADD COLUMN IF NOT EXISTS snippet TEXT NOT NULL DEFAULT '';

CREATE INDEX IF NOT EXISTS idx_deep_agent_searches_run_id
    ON deep_agent_searches(run_id, position);

CREATE INDEX IF NOT EXISTS idx_deep_agent_search_sources_search_id
    ON deep_agent_search_sources(search_id, position);
