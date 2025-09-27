export function startVoiceRecognition({ onResult, onError, onStart, onEnd } = {}) {
  if (typeof window === "undefined") {
    onError?.("Voice recognition is only available in the browser");
    return null;
  }

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    onError?.("Speech recognition is not supported in this browser");
    return null;
  }

  const recognition = new SpeechRecognition();
  recognition.lang = "en-US";
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;

  recognition.onstart = () => {
    onStart?.();
  };

  recognition.onresult = (event) => {
    const transcript = event.results?.[0]?.[0]?.transcript;
    if (transcript) {
      onResult?.(transcript);
    }
  };

  recognition.onerror = (event) => {
    onError?.(event.error || "Unknown speech recognition error");
  };

  recognition.onend = () => {
    onEnd?.();
  };

  recognition.start();
  return () => recognition.stop();
}
