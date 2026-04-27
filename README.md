# Deep Research Agent (SearXNG + OpenAI)

Python script version of the notebook workflow for a deep research agent:
- Uses `deepagents` orchestration
- Uses OpenAI model (`gpt-4o-mini` by default)
- Uses SearXNG for web search and page fetching

## Project Files

- `deep_research_searxng.py`: main CLI script
- `research_agent/tools.py`: search and reflection tools
- `research_agent/prompts.py`: orchestration and researcher prompts
- `utils.py`: rich message formatting helpers

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
LOG_LEVEL=INFO
```

Notes:
- Leave `OPENAI_BASE_URL` empty for official OpenAI API.
- `research_agent/tools.py` expects SearXNG at `http://localhost:8080/search`.
- Set `SEARXNG_LANGUAGE=any` for multilingual results, or a specific code like `en`, `fr`, `ar`.
- For local (non-Docker) runs, set `SEARXNG_URL=http://localhost:8080/search`.
- For Docker Compose app service, `SEARXNG_URL=http://searxng:8080/search` is correct.

## Run

```bash
python deep_research_searxng.py --query "What are the latest OpenAI features compared to latest Gen AI updates?"
```

Useful options:
- `--model gpt-4o-mini`
- `--search-language any` (or `en`, `fr`, `ar`, ...)
- `--log-level DEBUG`
- `--max-concurrent-research-units 1`
- `--max-researcher-iterations 1`
- `--sources-json outputs/sources_history.json`

## Logging

Logging is enabled in:
- `deep_research_searxng.py` for app lifecycle events
- `research_agent/tools.py` for search/fetch operations

Set `LOG_LEVEL` to `DEBUG` for verbose traces.

## Saved Sources

For every request, sources are appended to:
- `outputs/sources_history.json`

Each entry contains:
- `query`
- `saved_at_utc`
- `count`
- `sources` (`title`, `url`, `snippet`)

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
docker compose run --rm app python deep_research_searxng.py --query "your query"
```
