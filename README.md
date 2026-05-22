# Deep Research Agent (SearXNG + OpenAI)

Python script version of the notebook workflow for a deep research agent:
- Uses `deepagents` orchestration
- Uses OpenAI model (`gpt-4o-mini` by default)
- Uses SearXNG for web search and page fetching

## Project Files

- `config/`: shared application configuration helpers
- `api/`: FastAPI app, research execution, and structured output handling
- `cli/`: command-line entrypoints
- `research_agent/core/`: agent factory and core assembly
- `research_agent/tools/`: search, scraping, tracing, and reflection tools
- `research_agent/prompts/`: orchestration and researcher prompts
- `research_agent/utils/`: message formatting helpers

## Setup

1. Create/activate your virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure environment variables in `.env`:

```env
OPENAI_MODEL=gpt-4o-mini
OPENAI_API_KEY=your_openai_key_here
OPENAI_BASE_URL=
SEARXNG_LANGUAGE=any
MAX_CONCURRENT_RESEARCH_UNITS=1
MAX_RESEARCHER_ITERATIONS=1
AGENT_TIMEOUT_SECONDS=0
LOG_LEVEL=INFO
DEEP_AGENT_DB_ENABLED=false
DEEP_AGENT_DB_HOST=host.docker.internal
DEEP_AGENT_DB_PORT=5433
DEEP_AGENT_DB_USER=postgres
DEEP_AGENT_DB_PASSWORD=08012025
DEEP_AGENT_DB_NAME=crawl4ai_results
```

Notes:
- Leave `OPENAI_BASE_URL` empty for official OpenAI API.
- `research_agent/tools/` expects SearXNG at `http://localhost:8080/search`.
- Set `SEARXNG_LANGUAGE=any` for multilingual results, or a specific code like `en`, `fr`, `ar`.
- For local (non-Docker) runs, set `SEARXNG_URL=http://localhost:8080/search`.
- For Docker Compose app service, `SEARXNG_URL=http://searxng:8080/search` is correct.
- Set `AGENT_TIMEOUT_SECONDS=0` or leave it unset to allow API research requests to run without a fixed timeout.
- Set `DEEP_AGENT_DB_ENABLED=true` to save each completed API research run and its process/tool messages to Postgres.

## Run

```bash
python -m cli.deep_research --query "What are the latest OpenAI features compared to latest Gen AI updates?"
```

The compatibility wrapper inside the CLI package also works:

```bash
python -m cli.deep_research_searxng --query "What are the latest OpenAI features compared to latest Gen AI updates?"
```

Useful options:
- `--model gpt-4o-mini`
- `--search-language any` (or `en`, `fr`, `ar`, ...)
- `--log-level DEBUG`
- `--max-concurrent-research-units 1`
- `--max-researcher-iterations 1`

## Logging

Logging is enabled in:
- `cli/deep_research.py` for CLI lifecycle events
- `research_agent/tools/` for search/fetch operations

Set `LOG_LEVEL` to `DEBUG` for verbose traces.

## Saved Sources

Research results are saved to Postgres when `DEEP_AGENT_DB_ENABLED=true`.

## Postgres Run History

Create the deep-agent tables in the existing Crawl4AI database:

```bash
python3 db/init_db.py --host localhost --port 5433 --user postgres --password 08012025 --database crawl4ai_results
```

The API stores completed runs in:
- `deep_agent_runs`
- `deep_agent_process_messages`

When the API runs in Docker, use `DEEP_AGENT_DB_HOST=host.docker.internal` for a Postgres service exposed on your host at `localhost:5433`.

## Run With Docker Image

This project is published as:
- `elbouhdidi2001/deep-agent:latest`

setup:

```bash
cp .env.example .env
# set OPENAI_API_KEY in .env
docker compose pull
docker compose up
```

Run a custom query:

```bash
docker compose run --rm app python -m cli.deep_research --query "your query"
```
