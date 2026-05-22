const searxngImage =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 240 150'%3E%3Crect width='240' height='150' rx='18' fill='%23eff6ff'/%3E%3Ccircle cx='92' cy='70' r='38' fill='none' stroke='%232563eb' stroke-width='12'/%3E%3Cpath d='M122 98l42 30' stroke='%230f766e' stroke-width='14' stroke-linecap='round'/%3E%3Cpath d='M70 69h44M92 47v44' stroke='%23b45309' stroke-width='8' stroke-linecap='round'/%3E%3Ctext x='120' y='132' text-anchor='middle' font-family='Arial' font-size='18' font-weight='700' fill='%230f172a'%3ESearXNG%3C/text%3E%3C/svg%3E";

const crawl4aiImage =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 240 150'%3E%3Crect width='240' height='150' rx='18' fill='%23ecfdf5'/%3E%3Cpath d='M58 100c24-55 80-64 124-37' fill='none' stroke='%230f766e' stroke-width='12' stroke-linecap='round'/%3E%3Cpath d='M64 104l28-2-16-23' fill='none' stroke='%230f766e' stroke-width='10' stroke-linecap='round' stroke-linejoin='round'/%3E%3Crect x='74' y='38' width='92' height='50' rx='10' fill='%23ffffff' stroke='%232563eb' stroke-width='5'/%3E%3Cpath d='M92 57h56M92 72h36' stroke='%23b45309' stroke-width='6' stroke-linecap='round'/%3E%3Ctext x='120' y='132' text-anchor='middle' font-family='Arial' font-size='18' font-weight='700' fill='%230f172a'%3ECrawl4AI%3C/text%3E%3C/svg%3E";

function DocsPage() {
  return (
    <main className="page doc-page">
      <section className="card doc-card">
        <header className="doc-header">
          <div>
            <p className="eyebrow">Documentation</p>
            <h1>Deep Search Research Agent</h1>
            <p className="subtitle">
              A research interface that combines model reasoning, SearXNG search,
              Crawl4AI page extraction, and Postgres history.
            </p>
          </div>
          <a className="doc-link" href="/">Open App</a>
        </header>

        <section className="doc-section">
          <h2>How It Works</h2>
          <p>
            The app takes a research question, lets the selected model plan the
            investigation, searches the web with SearXNG, extracts readable page
            content with Crawl4AI, then uses the gathered evidence to produce an
            answer. When an output schema is provided, the API validates the
            model answer and returns structured JSON. Research runs and
            discovered sources are saved to the database so the work can be
            reviewed later.
          </p>
          <div className="flow-strip" aria-label="System flow">
            <span>User query</span>
            <span>Model provider</span>
            <span>SearXNG</span>
            <span>Crawl4AI</span>
            <span>Postgres</span>
            <span>Answer / JSON</span>
          </div>
        </section>

        <section className="doc-section">
          <h2>Why The Deep Agent Matters</h2>
          <p>
            The deep agent is important because it does more than send one prompt
            to a model. It can plan a research path, search for relevant
            sources, read extracted page content, keep a visible process trace,
            and produce an answer grounded in gathered evidence. This makes the
            app better suited for research workflows where users need context,
            sources, and repeatable results instead of a quick isolated reply.
          </p>
        </section>

        <section className="doc-section">
          <h2>Services</h2>
          <div className="service-grid">
            <article className="service-card">
              <img src={searxngImage} alt="SearXNG search service" />
              <h3>SearXNG</h3>
              <p>
                SearXNG discovers candidate URLs for each research query and
                gives the agent a broad set of sources to inspect.
              </p>
            </article>

            <article className="service-card">
              <img src={crawl4aiImage} alt="Crawl4AI scraping service" />
              <h3>Crawl4AI Service</h3>
              <p>
                Crawl4AI fetches selected pages and returns clean markdown for
                the agent, making web pages easier for the model to read and
                cite.
              </p>
            </article>
          </div>
        </section>

        <section className="doc-section">
          <h2>Model Providers</h2>
          <div className="doc-grid two-col">
            <article className="info-panel">
              <h3>Local</h3>
              <p>
                Use this when running an OpenAI-compatible local model endpoint.
                The frontend sends <code>model_provider: "local"</code>.
              </p>
              <pre>{`MODEL_PROVIDER=local
CHAT_MODEL=qwen3.5:latest
BASE_URL=http://your-model-server/ollama-v2/api/v1
API_KEY=your_local_provider_key_here`}</pre>
            </article>

            <article className="info-panel">
              <h3>OpenAI</h3>
              <p>
                Use this when the user selects OpenAI in the app. The API
                requires <code>OPENAI_API_KEY</code> for this provider.
              </p>
              <pre>{`OPENAI_MODEL=gpt-4o-mini
OPENAI_API_KEY=
OPENAI_BASE_URL=`}</pre>
            </article>
          </div>
        </section>

        <section className="doc-section">
          <h2>Using The App</h2>
          <p>
            To use the app, first make sure SearXNG is running for web search.
            Then make sure the Crawl4AI service is running for page extraction.
            After those two services are ready, launch the Deep Search app and
            open the frontend to run your research request.
          </p>
          <ol className="doc-steps">
            <li>Select <strong>Local</strong> or <strong>OpenAI</strong>.</li>
            <li>Enter a research question in the query field.</li>
            <li>Choose search language, log level, source count, reflection rounds, and the date used in prompts.</li>
            <li>Optionally paste a JSON Schema generated from a Pydantic model to force a structured answer.</li>
            <li>Submit the request and wait for the answer plus process trace.</li>
          </ol>
        </section>

        <section className="doc-section">
          <h2>Runtime Controls</h2>
          <div className="doc-grid">
            <article className="info-panel">
              <h3>SearXNG Sources</h3>
              <p>
                <code>max_sources</code> controls how many SearXNG results are
                returned per search call. The API accepts values from
                <code> 1</code> to <code>20</code>.
              </p>
            </article>
            <article className="info-panel">
              <h3>Reflection Rounds</h3>
              <p>
                <code>researcher_iterations</code> controls how many delegation
                rounds the deep agent may use. The API accepts values from
                <code> 1</code> to <code>10</code>.
              </p>
            </article>
            <article className="info-panel">
              <h3>Structured Output</h3>
              <p>
                <code>output_schema</code> accepts JSON Schema, including schema
                generated by <code>BaseModel.model_json_schema()</code>. The API
                returns <code>structured_answer</code> when validation succeeds.
              </p>
            </article>
          </div>
        </section>

        <section className="doc-section">
          <h2>API Request</h2>
          <p>
            The frontend posts to <code>/api/research</code>. The provider
            choice is sent per request, so users can switch without restarting
            the app.
          </p>
          <pre>{`{
  "query": "latest AI news in France",
  "model_provider": "local",
  "search_language": "any",
  "log_level": "INFO",
  "search_date": "2026-05-06",
  "max_sources": 3,
  "researcher_iterations": 3,
  "output_schema": {
    "type": "object",
    "properties": {
      "summary": {"type": "string"},
      "sources": {"type": "array", "items": {"type": "string"}}
    },
    "required": ["summary", "sources"]
  }
}`}</pre>
          <p>
            Response JSON includes <code>report_content</code>,
            <code> answer</code>, <code>process</code>, and, when
            <code> output_schema</code> is provided, a validated
            <code> structured_answer</code>.
          </p>
        </section>

        <section className="doc-section">
          <h2>Saved Data</h2>
          <div className="doc-grid">
            <article className="info-panel">
              <h3>Research Runs</h3>
              <p>
                Completed answers and model/process metadata are saved in
                <code> deep_agent_runs</code> and
                <code> deep_agent_process_messages</code>.
              </p>
            </article>
            <article className="info-panel">
              <h3>Search Sources</h3>
              <p>
                SearXNG source candidates are saved in
                <code> deep_agent_searches</code> and
                <code> deep_agent_search_sources</code>.
              </p>
            </article>
            <article className="info-panel">
              <h3>Crawl4AI Results</h3>
              <p>
                Crawl4AI service results live in the shared Postgres database,
                using the service table <code>scrape_results</code>.
              </p>
            </article>
          </div>
        </section>

        <section className="doc-section">
          <h2>Quick Start Summary</h2>
          <p>
            To use this app correctly, you need three things ready: SearXNG for
            search, Crawl4AI for page extraction, and the Deep Search app for
            the API and frontend.
          </p>
          <div className="doc-grid">
            <article className="info-panel">
              <h3>Requirements</h3>
              <p>
                Docker Compose, a running Postgres database, SearXNG, Crawl4AI,
                and at least one model provider: local or OpenAI.
              </p>
            </article>
            <article className="info-panel">
              <h3>What Must Run</h3>
              <p>
                Start SearXNG first, start Crawl4AI second, then start this app.
                The frontend depends on the API, the API depends on search and
                scraping, and saved results depend on Postgres.
              </p>
            </article>
            <article className="info-panel">
              <h3>How To Run</h3>
              <pre>{`docker compose up -d

open http://localhost:5173
open http://localhost:5173/doc`}</pre>
            </article>
          </div>
        </section>

      </section>
    </main>
  );
}

export default DocsPage;
