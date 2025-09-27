import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import clsx from "clsx";
import useSWR from "swr";

import ChatBox from "../components/ChatBox";
import TaskList from "../components/TaskList";

const API_BASE = process.env.NEXT_PUBLIC_AGENT_API_URL || "http://localhost:8000";
const API_TOKEN = process.env.NEXT_PUBLIC_API_TOKEN;

const fetcher = async (url) => {
  const headers = { "Content-Type": "application/json" };
  if (API_TOKEN) {
    headers["X-API-Token"] = API_TOKEN;
  }
  const response = await fetch(url, { headers });
  if (!response.ok) {
    throw new Error(`Request failed with ${response.status}`);
  }
  return response.json();
};

const makeMessageId = () => `${Date.now()}-${Math.random().toString(16).slice(2)}`;

export default function Home() {
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);
  const [selectedTask, setSelectedTask] = useState(null);
  const [activeTaskId, setActiveTaskId] = useState(null);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [conversation, setConversation] = useState([]);
  const chatScrollRef = useRef(null);

  const { data: tasksData, mutate: refreshTasks } = useSWR(
    `${API_BASE}/api/tasks`,
    fetcher,
    { refreshInterval: 60000 }
  );

  const tasks = useMemo(() => tasksData?.tasks ?? [], [tasksData]);

  const appendMessage = useCallback((message) => {
    setConversation((prev) => [...prev, { id: makeMessageId(), ...message }]);
  }, []);

  useEffect(() => {
    if (!chatScrollRef.current) {
      return;
    }

    chatScrollRef.current.scrollTo({
      top: chatScrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [conversation, selectedTask]);

  const handleSelectTask = useCallback(async (taskId) => {
    setErrorMessage(null);
    try {
      const headers = {};
      if (API_TOKEN) {
        headers["X-API-Token"] = API_TOKEN;
      }
      const response = await fetch(`${API_BASE}/api/task/${taskId}`, { headers });
      if (!response.ok) {
        throw new Error("Failed to fetch task details");
      }
      const data = await response.json();
      setSelectedTask(data);
      setActiveTaskId(taskId);
      setIsHistoryOpen(true);
    } catch (error) {
      setErrorMessage(error.message);
    }
  }, []);

  const handleSend = useCallback(
    async (command, options) => {
      const timestamp = new Date().toISOString();
      appendMessage({
        role: "user",
        content: command,
        timestamp,
      });

      setIsLoading(true);
      setErrorMessage(null);
      try {
        const headers = { "Content-Type": "application/json" };
        if (API_TOKEN) {
          headers["X-API-Token"] = API_TOKEN;
        }
        const payload = {
          command,
          headless: options?.headless ?? true,
          record_screenshots: options?.recordScreenshots ?? false,
        };
        const response = await fetch(`${API_BASE}/api/command`, {
          method: "POST",
          headers,
          body: JSON.stringify(payload),
        });
        const data = await response.json();
        refreshTasks();

        if (!response.ok || !data.success) {
          const errorText = data.errors?.join("\n") || "Command failed";
          appendMessage({
            role: "assistant",
            tone: "error",
            content: errorText,
            details: data,
            timestamp: new Date().toISOString(),
          });
          setErrorMessage(errorText);
          return;
        }

        appendMessage({
          role: "assistant",
          tone: "success",
          content: formatResultsSummary(data.results),
          details: data,
          timestamp: new Date().toISOString(),
        });

        if (data.task_id) {
          setActiveTaskId(data.task_id);
          await handleSelectTask(data.task_id);
        } else {
          setSelectedTask(null);
        }

        setIsHistoryOpen(true);
      } catch (error) {
        appendMessage({
          role: "assistant",
          tone: "error",
          content: error.message,
          timestamp: new Date().toISOString(),
        });
        setErrorMessage(error.message);
      } finally {
        setIsLoading(false);
      }
    },
    [appendMessage, handleSelectTask, refreshTasks]
  );

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="header-inner">
          <div className="header-text">
            <h1>Web Navigator AI Agent</h1>
            <p className="small-text">
              Ask the agent to browse, search, and collect information. Responses appear in seconds.
            </p>
          </div>
          <button
            type="button"
            className="history-toggle"
            onClick={() => setIsHistoryOpen((prev) => !prev)}
          >
            {isHistoryOpen ? "Hide history" : "Show history"}
          </button>
        </div>
      </header>

      <main className={clsx("chat-layout", isHistoryOpen && "chat-layout--history-open")}>
        <section className="chat-pane">
          <div
            ref={chatScrollRef}
            className="chat-scroll"
            role="log"
            aria-live="polite"
          >
            {conversation.length === 0 && (
              <div className="chat-placeholder">
                <h2>Ready when you are</h2>
                <p>Describe what you want to do. The agent will plan the steps and run them for you.</p>
              </div>
            )}

            {conversation.map((message) => (
              <article
                key={message.id}
                className={clsx(
                  "chat-message",
                  message.role === "user" ? "chat-message--user" : "chat-message--assistant",
                  message.tone === "error" && "chat-message--error"
                )}
              >
                <header>
                  <span className="chat-message__role">
                    {message.role === "user" ? "You" : "Agent"}
                  </span>
                  <span className="chat-message__time">
                    {new Date(message.timestamp).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                </header>
                <div className="chat-message__body">
                  <p>{message.content}</p>
                  {message.details?.results && message.tone !== "error" && (
                    <div className="chat-message__structured">
                      <h4>Structured results</h4>
                      {renderStructuredValue(message.details.results)}
                    </div>
                  )}
                  {message.details?.logs && message.details.logs.length > 0 && (
                    <details className="chat-message__details">
                      <summary>Execution logs</summary>
                      <pre>{message.details.logs.join("\n")}</pre>
                    </details>
                  )}
                </div>
              </article>
            ))}

            {selectedTask && (
              <article className="chat-message chat-message--assistant chat-message--task">
                <header>
                  <span className="chat-message__role">Saved task</span>
                  <span className="chat-message__time">
                    {new Date(selectedTask.created_at).toLocaleString()}
                  </span>
                </header>
                <div className="chat-message__body">
                  <p>{selectedTask.command}</p>
                  <div className="chat-message__structured">
                    <h4>Result snapshot</h4>
                    {renderStructuredValue(
                      selectedTask.result?.results ?? selectedTask.result ?? {}
                    )}
                  </div>
                </div>
              </article>
            )}
          </div>

          <div className="chat-input-shell">
            {errorMessage && <p className="error-banner">{errorMessage}</p>}
            <ChatBox onSend={handleSend} isLoading={isLoading} />
          </div>
        </section>

        <aside className={clsx("history-pane", isHistoryOpen && "history-pane--open")}>
          <TaskList
            tasks={tasks}
            onSelectTask={handleSelectTask}
            isLoading={isLoading}
            activeTaskId={activeTaskId}
          />
          {selectedTask && (
            <div className="history-detail">
              <h3>Task details</h3>
              <div className="history-detail__meta">
                <span>ID: {selectedTask.id}</span>
                <span>Run at: {new Date(selectedTask.created_at).toLocaleString()}</span>
              </div>
              <div className="history-detail__section">
                <h4>Plan</h4>
                <pre>{JSON.stringify(selectedTask.plan?.steps ?? selectedTask.plan, null, 2)}</pre>
              </div>
              <div className="history-detail__section">
                <h4>Results</h4>
                {renderStructuredValue(
                  selectedTask.result?.results ?? selectedTask.result ?? {}
                )}
              </div>
              {selectedTask.result?.logs?.length > 0 && (
                <div className="history-detail__section">
                  <h4>Logs</h4>
                  <pre>{selectedTask.result.logs.join("\n")}</pre>
                </div>
              )}
            </div>
          )}
        </aside>
      </main>
    </div>
  );
}

function renderStructuredValue(value, path = "root") {
  if (value === null || value === undefined) {
    return <span className="structured-leaf">Not provided</span>;
  }

  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return <span className="structured-leaf">{String(value)}</span>;
  }

  if (Array.isArray(value)) {
    if (value.length === 0) {
      return <span className="structured-leaf">No items returned</span>;
    }
    return (
      <ol className="structured-list">
        {value.map((entry, index) => (
          <li key={`${path}-${index}`}>{renderStructuredValue(entry, `${path}-${index}`)}</li>
        ))}
      </ol>
    );
  }

  if (typeof value === "object") {
    const entries = Object.entries(value);
    if (entries.length === 0) {
      return <span className="structured-leaf">No fields returned</span>;
    }
    return (
      <div className="structured-object">
        {entries.map(([key, entry]) => (
          <div key={`${path}-${key}`} className="structured-entry">
            <span className="structured-key">{key}</span>
            <div className="structured-value">{renderStructuredValue(entry, `${path}-${key}`)}</div>
          </div>
        ))}
      </div>
    );
  }

  return <span className="structured-leaf">{JSON.stringify(value)}</span>;
}

function formatResultsSummary(results) {
  if (!results || Object.keys(results).length === 0) {
    return "The agent finished without returning structured results.";
  }

  const fragments = [];
  Object.entries(results).forEach(([key, value]) => {
    if (typeof value === "string") {
      fragments.push(`${key}: ${value}`);
    } else if (typeof value === "number" || typeof value === "boolean") {
      fragments.push(`${key}: ${String(value)}`);
    } else if (Array.isArray(value)) {
      fragments.push(`${key}: ${value.length} item${value.length === 1 ? "" : "s"}`);
    } else if (value && typeof value === "object") {
      const size = Object.keys(value).length;
      fragments.push(`${key}: ${size} field${size === 1 ? "" : "s"}`);
    }
  });

  if (fragments.length === 0) {
    return "The agent completed successfully.";
  }

  return fragments.join(" • ");
}
