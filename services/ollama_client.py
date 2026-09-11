from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from urllib.parse import urlparse
import time
from dataclasses import dataclass
from typing import Any

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "qwen3:1.7b")
EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")


class OllamaError(RuntimeError):
    pass

_STATUS_CACHE: tuple[float, "OllamaStatus"] | None = None




def _validate_local_base_url() -> None:
    parsed = urlparse(OLLAMA_BASE_URL)
    host = (parsed.hostname or "").casefold()
    if parsed.scheme not in {"http", "https"} or host not in {"127.0.0.1", "localhost", "::1"}:
        raise OllamaError(
            "VaultComply blocks non-local Ollama endpoints in this prototype. "
            f"Configured OLLAMA_BASE_URL={OLLAMA_BASE_URL!r}"
        )

@dataclass(frozen=True)
class OllamaStatus:
    online: bool
    models: tuple[str, ...] = ()
    chat_model_ready: bool = False
    embed_model_ready: bool = False
    message: str = ""


def _request(path: str, payload: dict[str, Any] | None = None, *, timeout: int = 30) -> dict[str, Any]:
    _validate_local_base_url()
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{OLLAMA_BASE_URL}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST" if data is not None else "GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        raise OllamaError(f"Ollama HTTP {exc.code}: {body[:300]}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise OllamaError(f"Could not reach local Ollama at {OLLAMA_BASE_URL}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise OllamaError("Ollama returned invalid JSON") from exc


def status(*, refresh: bool = False) -> OllamaStatus:
    global _STATUS_CACHE
    now = time.monotonic()
    if not refresh and _STATUS_CACHE and now - _STATUS_CACHE[0] < 5:
        return _STATUS_CACHE[1]
    try:
        result = _request("/api/tags", timeout=3)
        names = tuple(m.get("name", "") for m in result.get("models", []) if m.get("name"))
        def _ready(configured: str) -> bool:
            configured_base = configured.removesuffix(":latest")
            return any(
                name == configured
                or name == configured + ":latest"
                or name.removesuffix(":latest") == configured_base
                for name in names
            )

        result_status = OllamaStatus(
            online=True,
            models=names,
            chat_model_ready=_ready(CHAT_MODEL),
            embed_model_ready=_ready(EMBED_MODEL),
            message="Local Ollama is online",
        )
        _STATUS_CACHE = (now, result_status)
        return result_status
    except OllamaError as exc:
        result_status = OllamaStatus(online=False, message=str(exc))
        _STATUS_CACHE = (now, result_status)
        return result_status


def chat(
    messages: list[dict[str, str]],
    *,
    model: str = CHAT_MODEL,
    json_format: bool = False,
    timeout: int = 600,
    num_ctx: int = 4096,
    num_predict: int = 1600,
) -> str:
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
        "think": False,
        "options": {
            "temperature": 0,
            "num_ctx": num_ctx,
            "num_predict": num_predict,
        },
    }
    if json_format:
        payload["format"] = "json"
    result = _request("/api/chat", payload, timeout=timeout)
    message = result.get("message") or {}
    content = str(message.get("content") or "").strip()
    if not content:
        reason = result.get("done_reason", "unknown")
        thinking = str(message.get("thinking") or "").strip()
        if thinking:
            raise OllamaError(f"Ollama produced reasoning but no final response (done_reason={reason})")
        raise OllamaError(f"Ollama returned an empty response (done_reason={reason})")
    return content


def chat_json(messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any] | list[Any]:
    raw = chat(messages, json_format=True, **kwargs)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise OllamaError(f"Ollama returned non-JSON content: {raw[:300]}") from exc


def embed_texts(texts: list[str], *, model: str = EMBED_MODEL, timeout: int = 180) -> list[list[float]]:
    if not texts:
        return []
    try:
        payload = {"model": model, "input": texts}
        result = _request("/api/embed", payload, timeout=timeout)
        embeddings = result.get("embeddings")
        if isinstance(embeddings, list) and len(embeddings) == len(texts):
            return [[float(v) for v in row] for row in embeddings]
    except OllamaError as primary_exc:
        # Compatibility fallback for older Ollama versions that expose only
        # /api/embeddings and accept one prompt at a time.
        vectors: list[list[float]] = []
        try:
            for text in texts:
                item = _request("/api/embeddings", {"model": model, "prompt": text}, timeout=timeout)
                vector = item.get("embedding")
                if not isinstance(vector, list):
                    raise OllamaError("Legacy Ollama embedding response did not contain an embedding")
                vectors.append([float(v) for v in vector])
            return vectors
        except OllamaError:
            raise primary_exc
    raise OllamaError("Ollama embedding response did not contain the expected embeddings")
