import { useMemo } from "react";
import clsx from "clsx";

const API_BASE = process.env.NEXT_PUBLIC_AGENT_API_URL || "http://localhost:8000";
const API_TOKEN = process.env.NEXT_PUBLIC_API_TOKEN;

export default function TaskList({ tasks, onSelectTask, isLoading, activeTaskId }) {
  const orderedTasks = useMemo(() => tasks ?? [], [tasks]);

  const openExport = (taskId, format) => {
    const url = new URL(`${API_BASE}/api/export/${taskId}`);
    url.searchParams.set("format", format);
    const headers = API_TOKEN ? { "X-API-Token": API_TOKEN } : undefined;
    if (headers) {
      fetch(url, { headers })
        .then((response) => response.blob())
        .then((blob) => {
          const downloadUrl = window.URL.createObjectURL(blob);
          const anchor = document.createElement("a");
          anchor.href = downloadUrl;
          anchor.download = `${taskId}.${format}`;
          document.body.appendChild(anchor);
          anchor.click();
          anchor.remove();
          window.URL.revokeObjectURL(downloadUrl);
        });
    } else {
      window.open(url.toString(), "_blank");
    }
  };

  return (
    <div className="history-list">
      <div className="history-list__header">
        <h2>Recent Tasks</h2>
        {isLoading && <span>Updating...</span>}
      </div>
      <div className="history-list__items">
        {orderedTasks.length === 0 && (
          <p className="history-list__empty">No tasks yet. Run your first command!</p>
        )}
        {orderedTasks.map((task) => {
          const isActive = task.id === activeTaskId;
          return (
            <div key={task.id} className={clsx("history-card", isActive && "history-card--active")}>
              <button
                type="button"
                onClick={() => onSelectTask(task.id)}
                className="history-card__main"
              >
                <span className="history-card__title">{task.command}</span>
                <span className="history-card__time">
                  {new Date(task.created_at).toLocaleString()}
                </span>
              </button>
              <div className="history-card__actions">
                <button type="button" onClick={() => openExport(task.id, "json")}>
                  JSON
                </button>
                <button type="button" onClick={() => openExport(task.id, "csv")}>
                  CSV
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
