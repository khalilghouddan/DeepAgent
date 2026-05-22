import { useState } from "react";

function todayIsoDate() {
  return new Date().toISOString().slice(0, 10);
}

function responseErrorMessage(response, data) {
  const detail = data.detail || data.error || data.raw;
  if (!detail) {
    return `Request failed with status ${response.status}`;
  }
  if (typeof detail === "string") {
    return detail;
  }
  return JSON.stringify(detail);
}

function App() {
  const [query, setQuery] = useState("");
  const [modelProvider, setModelProvider] = useState("local");
  const [language, setLanguage] = useState("any");
  const [logLevel, setLogLevel] = useState("INFO");
  const [currentDate, setCurrentDate] = useState(todayIsoDate());
  const [maxSources, setMaxSources] = useState(3);
  const [researcherIterations, setResearcherIterations] = useState(3);
  const [outputSchema, setOutputSchema] = useState("");
  const [processMessages, setProcessMessages] = useState([]);
  const [reportContent, setReportContent] = useState("");
  const [answer, setAnswer] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  function messageClass(type) {
    const normalized = (type || "").toLowerCase();
    if (normalized === "human") return "process-human";
    if (normalized === "ai") return "process-ai";
    if (normalized === "tool") return "process-tool";
    return "process-other";
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setProcessMessages([]);
    setReportContent("");
    setAnswer("");
    setIsSubmitting(true);

    try {
      let parsedOutputSchema;
      if (outputSchema.trim()) {
        try {
          parsedOutputSchema = JSON.parse(outputSchema);
        } catch {
          throw new Error("Output JSON Schema must be valid JSON.");
        }
      }

      const response = await fetch("/api/research", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          query,
          model_provider: modelProvider,
          search_language: language,
          log_level: logLevel,
          search_date: currentDate,
          max_sources: Number(maxSources),
          researcher_iterations: Number(researcherIterations),
          output_schema: parsedOutputSchema
        })
      });

      const rawBody = await response.text();
      let data = {};
      if (rawBody) {
        try {
          data = JSON.parse(rawBody);
        } catch {
          data = { raw: rawBody };
        }
      }

      if (!response.ok) {
        throw new Error(responseErrorMessage(response, data));
      }

      setReportContent(
        data.report_content && data.report_content !== data.answer
          ? data.report_content
          : ""
      );
      setAnswer(data.answer || "");
      setProcessMessages(Array.isArray(data.process) ? data.process : []);
    } catch (submitError) {
      setError(submitError.message || "Unknown error");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="page">
      <section className="card">
        <header className="app-header">
          <h1>Deep Agent Frontend</h1>
          <a className="doc-link" href="/doc">Documentation</a>
        </header>

        <form onSubmit={handleSubmit}>
          <label htmlFor="model-provider-local">Model Provider</label>
          <div className="provider-toggle" role="group" aria-label="Model Provider">
            <button
              id="model-provider-local"
              type="button"
              className={modelProvider === "local" ? "active" : ""}
              aria-pressed={modelProvider === "local"}
              onClick={() => setModelProvider("local")}
            >
              Local
            </button>
            <button
              type="button"
              className={modelProvider === "openai" ? "active" : ""}
              aria-pressed={modelProvider === "openai"}
              onClick={() => setModelProvider("openai")}
            >
              OpenAI
            </button>
          </div>

          <label htmlFor="query">Query</label>
          <textarea
            id="query"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            rows={4}
            placeholder="Enter your query here..."
          />

          <div className="row">
            <div className="field">
              <label htmlFor="language">Search Language</label>
              <select
                id="language"
                value={language}
                onChange={(event) => setLanguage(event.target.value)}
              >
                <option value="any">any</option>
                <option value="en">en</option>
                <option value="fr">fr</option>
                <option value="ar">ar</option>
              </select>
            </div>

            <div className="field">
              <label htmlFor="log-level">Log Level</label>
              <select
                id="log-level"
                value={logLevel}
                onChange={(event) => setLogLevel(event.target.value)}
              >
                <option value="DEBUG">DEBUG</option>
                <option value="INFO">INFO</option>
                <option value="WARNING">WARNING</option>
                <option value="ERROR">ERROR</option>
              </select>
            </div>

            <div className="field">
              <label htmlFor="search-date">Search Date</label>
              <input
                id="search-date"
                type="date"
                value={currentDate}
                onChange={(event) => setCurrentDate(event.target.value)}
              />
            </div>

            <div className="field">
              <label htmlFor="max-sources">SearXNG Sources</label>
              <input
                id="max-sources"
                type="number"
                min="1"
                max="20"
                value={maxSources}
                onChange={(event) => setMaxSources(event.target.value)}
              />
            </div>

            <div className="field">
              <label htmlFor="researcher-iterations">Reflection Rounds</label>
              <input
                id="researcher-iterations"
                type="number"
                min="1"
                max="10"
                value={researcherIterations}
                onChange={(event) => setResearcherIterations(event.target.value)}
              />
            </div>
          </div>

          <label htmlFor="output-schema">Output JSON Schema</label>
          <textarea
            id="output-schema"
            value={outputSchema}
            onChange={(event) => setOutputSchema(event.target.value)}
            rows={8}
            placeholder='{"type":"object","properties":{"summary":{"type":"string"},"sources":{"type":"array","items":{"type":"string"}}},"required":["summary","sources"]}'
          />

          <button className="submit" type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Running..." : "Submit"}
          </button>

          {isSubmitting ? (
            <p className="status-block">
              Research is running. This can take a while for broad queries.
            </p>
          ) : null}
        </form>

        {error ? (
          <>
            <label htmlFor="error">Error</label>
            <pre id="error" className="error-block">
              {error}
            </pre>
          </>
        ) : null}

        {reportContent ? (
          <>
            <label htmlFor="report-content">Report Content</label>
            <pre id="report-content" className="report-block">
              {reportContent}
            </pre>
          </>
        ) : null}

        {answer ? (
          <>
            <label htmlFor="answer">Answer</label>
            <pre id="answer" className="answer-block">
              {answer}
            </pre>
          </>
        ) : null}

        {processMessages.length ? (
          <>
            <label htmlFor="process">Process</label>
            <section id="process" className="process-list">
              {processMessages.map((message, index) => (
                <article
                  key={`${message.type}-${index}`}
                  className={`process-item ${messageClass(message.type)}`}
                >
                  <h3>{message.title || message.type || "Message"}</h3>
                  <pre>{message.content}</pre>
                </article>
              ))}
            </section>
          </>
        ) : null}

      </section>
    </main>
  );
}

export default App;
