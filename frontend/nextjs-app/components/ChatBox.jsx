import { useCallback, useState } from "react";
import clsx from "clsx";

import { startVoiceRecognition } from "../utils/voice";

export default function ChatBox({ onSend, isLoading }) {
  const [command, setCommand] = useState("");
  const [headless, setHeadless] = useState(true);
  const [recordScreenshots, setRecordScreenshots] = useState(false);
  const [voiceError, setVoiceError] = useState(null);
  const [listening, setListening] = useState(false);

  const executeSend = useCallback(async () => {
    if (!command.trim()) {
      setVoiceError("Enter a command first");
      return;
    }
    setVoiceError(null);
    try {
      await onSend(command.trim(), { headless, recordScreenshots });
      setCommand("");
    } catch (error) {
      setVoiceError(error.message ?? "Failed to send command");
    }
  }, [command, headless, recordScreenshots, onSend]);

  const handleSubmit = useCallback(
    (event) => {
      event.preventDefault();
      executeSend();
    },
    [executeSend]
  );

  const handleKeyDown = useCallback(
    (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        executeSend();
      }
    },
    [executeSend]
  );

  const handleVoiceClick = useCallback(() => {
    setVoiceError(null);
    const stop = startVoiceRecognition({
      onResult: (text) => {
        setCommand(text);
      },
      onError: (error) => {
        setVoiceError(error);
      },
      onStart: () => {
        setListening(true);
      },
      onEnd: () => {
        setListening(false);
      },
    });

    if (stop) {
      setTimeout(() => {
        stop();
        setListening(false);
      }, 8000);
    }
  }, []);

  return (
    <form onSubmit={handleSubmit} className="chat-composer">
      <div className="chat-composer__input">
        <textarea
          id="command"
          className="chat-composer__textarea"
          placeholder="Send a command, for example: Search laptops under 50000 and list the best five"
          value={command}
          onChange={(event) => setCommand(event.target.value)}
          onKeyDown={handleKeyDown}
          rows={1}
        />
        <button
          type="button"
          onClick={handleVoiceClick}
          className={clsx("chat-composer__icon", listening && "chat-composer__icon--active")}
          aria-label="Voice input"
        >
          {listening ? "●" : "🎙"}
        </button>
      </div>

      <div className="chat-composer__footer">
        <div className="chat-composer__toggles">
          <label>
            <input
              type="checkbox"
              checked={headless}
              onChange={(event) => setHeadless(event.target.checked)}
            />
            Headless mode
          </label>
          <label>
            <input
              type="checkbox"
              checked={recordScreenshots}
              onChange={(event) => setRecordScreenshots(event.target.checked)}
            />
            Record screenshots
          </label>
        </div>

        <button type="submit" disabled={isLoading} className="chat-composer__send">
          {isLoading ? "Running..." : "Send"}
        </button>
      </div>

      {voiceError && <p className="chat-composer__error">{voiceError}</p>}
    </form>
  );
}
