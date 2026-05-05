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
  const [query, setQuery] = useState("latest AI news in France");
  const [language, setLanguage] = useState("any");
  const [logLevel, setLogLevel] = useState("INFO");
  const [currentDate, setCurrentDate] = useState(todayIsoDate());
  const [processMessages, setProcessMessages] = useState([]);
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
    setAnswer("");
    setIsSubmitting(true);

    try {
      const response = await fetch("/api/research", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          query,
          search_language: language,
          log_level: logLevel,
          search_date: currentDate
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
        <h1>Deep Agent Frontend</h1>

        <form onSubmit={handleSubmit}>
          <label htmlFor="query">Query</label>
          <textarea
            id="query"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            rows={4}
            placeholder="Ask a research question..."
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
          </div>

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
