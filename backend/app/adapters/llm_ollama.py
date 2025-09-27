from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import httpx


class OllamaError(RuntimeError):
    """Raised when an Ollama interaction fails."""


class OllamaClient:
    """Minimal Ollama client that prefers the HTTP API but can fall back to CLI."""

    def __init__(self, model: str, host: Optional[str] = None, timeout: float = 120.0) -> None:
        self.model = model
        self.host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.timeout = timeout
        self._session = httpx.Client(timeout=timeout)

    def is_available(self) -> bool:
        try:
            response = self._session.get(f"{self.host}/api/tags")
            response.raise_for_status()
            data = response.json()
            models = [item.get("name") for item in data.get("models", [])]
            return self.model in models if models else True
        except Exception:
            return self._cli_available()

    def generate(self, prompt: str) -> str:
        try:
            payload = {"model": self.model, "prompt": prompt, "stream": False}
            response = self._session.post(f"{self.host}/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()
            output = data.get("response")
            if not output:
                raise OllamaError("Empty response from Ollama HTTP API")
            return output
        except Exception:
            return self._generate_via_cli(prompt)

    def _generate_via_cli(self, prompt: str) -> str:
        if not self._cli_available():
            raise OllamaError(
                "Neither Ollama HTTP API nor CLI are available. Ensure Ollama is installed and running."
            )

        command = ["ollama", "run", self.model]
        try:
            process = subprocess.run(
                command,
                input=prompt.encode("utf-8"),
                capture_output=True,
                check=False,
            )
            if process.returncode != 0:
                raise OllamaError(
                    f"Ollama CLI exited with code {process.returncode}: {process.stderr.decode('utf-8', errors='ignore')}"
                )
            output = process.stdout.decode("utf-8", errors="ignore").strip()
            if not output:
                raise OllamaError("Empty response from Ollama CLI")
            return output
        except FileNotFoundError as exc:
            raise OllamaError("Ollama CLI not found on PATH") from exc

    @staticmethod
    def _cli_available() -> bool:
        return shutil.which("ollama") is not None


def detect_model_from_env(default: str = "llama3") -> str:
    return os.getenv("LLM_MODEL", default)


def load_prompt_template(prompt_path: Optional[Path]) -> str:
    if prompt_path and prompt_path.is_file():
        return prompt_path.read_text(encoding="utf-8")
    raise FileNotFoundError(f"Master prompt file not found at {prompt_path}")
