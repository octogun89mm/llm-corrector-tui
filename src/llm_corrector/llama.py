from __future__ import annotations

import json
import os
import shlex
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass


SYSTEM_PROMPT = """You are a text correction engine.
Return only the corrected text, with no preface and no explanation.
Preserve the user's meaning, tone, formatting, and language.
Fix spelling, grammar, punctuation, agreement errors, and obvious typos.
If the text contains mistakes, rewrite it with those mistakes corrected.

Examples:
Input: this are a test agaisnt the model
Output: This is a test against the model.

Input: i will send this tomorow
Output: I will send this tomorrow.
"""


@dataclass(frozen=True)
class LlamaClient:
    base_url: str
    model: str | None
    start_cmd: str
    start_timeout: float
    temperature: float
    max_tokens: int

    @classmethod
    def from_env(cls) -> "LlamaClient":
        raw_model = os.environ.get("LLM_CORRECTOR_MODEL", "auto").strip()
        return cls(
            base_url=os.environ.get("LLM_CORRECTOR_BASE_URL", "http://127.0.0.1:8080/v1").rstrip("/"),
            model=None if raw_model in {"", "auto"} else raw_model,
            start_cmd=os.environ.get("LLM_CORRECTOR_START_CMD", "systemctl --user start llama.service"),
            start_timeout=float(os.environ.get("LLM_CORRECTOR_START_TIMEOUT", "45")),
            temperature=float(os.environ.get("LLM_CORRECTOR_TEMPERATURE", "0.1")),
            max_tokens=int(os.environ.get("LLM_CORRECTOR_MAX_TOKENS", "512")),
        )

    def correct(self, text: str) -> str:
        stripped = text.strip()
        if not stripped:
            return ""

        self.ensure_server()
        model = self.model or self.first_model()
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Input: {stripped}\nOutput:"},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False,
        }
        data = self.post_json("/chat/completions", body, timeout=120)
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return clean_model_output(content) or stripped

    def ensure_server(self) -> None:
        if self.is_ready():
            return
        if self.start_cmd.strip():
            subprocess.Popen(
                shlex.split(self.start_cmd),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        deadline = time.monotonic() + self.start_timeout
        while time.monotonic() < deadline:
            if self.is_ready():
                return
            time.sleep(0.5)
        raise RuntimeError(f"llama.cpp server is not reachable at {self.base_url}")

    def is_ready(self) -> bool:
        try:
            self.get_json("/models", timeout=1.0)
            return True
        except Exception:
            return False

    def first_model(self) -> str:
        data = self.get_json("/models", timeout=5)
        models = data.get("data") or data.get("models") or []
        if not models:
            raise RuntimeError("llama.cpp returned no models")
        first = models[0]
        if isinstance(first, dict):
            return str(first.get("id") or first.get("model") or first.get("name"))
        return str(first)

    def get_json(self, path: str, timeout: float) -> dict:
        with urllib.request.urlopen(self.base_url + path, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def post_json(self, path: str, body: dict, timeout: float) -> dict:
        request = urllib.request.Request(
            self.base_url + path,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"llama.cpp HTTP {exc.code}: {detail}") from exc


def clean_model_output(text: str) -> str:
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
        text = text[1:-1].strip()
    return text
