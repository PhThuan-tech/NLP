"""Offline HTTP service for the VLSP document-level MT submission."""

from __future__ import annotations

import json
import math
import os
import re
import threading
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .config import ExperimentConfig
from .inference import (
    assemble_document,
    load_inference_model,
    markdown_structure_report,
    split_markdown_document,
    translate_chunks,
)


DIRECTIONS = {"en2vi", "vi2en"}
VI_MARKS_RE = re.compile(
    r"[ăâđêôơưĂÂĐÊÔƠƯàáảãạằắẳẵặầấẩẫậèéẻẽẹềếểễệ"
    r"ìíỉĩịòóỏõọồốổỗộờớởỡợùúủũụừứửữựỳýỷỹỵ]"
)
WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
VI_MARKERS = {
    "của", "và", "được", "theo", "điều", "khoản", "nghị", "định",
    "pháp", "luật", "người", "trong", "các", "không", "quyền",
}
EN_MARKERS = {
    "the", "and", "of", "shall", "article", "clause", "law", "decree",
    "person", "under", "rights", "must", "may", "not", "this", "within",
}


def detect_direction(text: str) -> str:
    """Detect the source language of a complete legal document."""

    if not text.strip():
        raise ValueError("The input document is empty")
    tokens = [token.casefold() for token in WORD_RE.findall(text)]
    if not tokens:
        raise ValueError("The input document has no language-bearing text")
    vi_score = sum(token in VI_MARKERS for token in tokens)
    en_score = sum(token in EN_MARKERS for token in tokens)
    marked = len(VI_MARKS_RE.findall(text))
    if vi_score > en_score:
        return "vi2en"
    if en_score > vi_score:
        return "en2vi"
    # For the task's two allowed languages, diacritic density is a useful
    # fallback. It also handles a short input such as "Điều 1" without a
    # fourth argument in the official wrapper contract.
    if marked >= max(1, math.ceil(len(tokens) * 0.1)):
        return "vi2en"
    if marked == 0:
        return "en2vi"
    raise ValueError(
        "Cannot determine translation direction; use /translate/en2vi, "
        "/translate/vi2en, ?direction=..., or X-Translation-Direction"
    )


def direction_from_request(path: str, header: str | None, text: str) -> str:
    parsed = urlparse(path)
    route_direction = parsed.path.rstrip("/").rsplit("/", 1)[-1]
    query_direction = parse_qs(parsed.query).get("direction", [None])[0]
    explicit = header or query_direction or (
        route_direction if route_direction in DIRECTIONS else None
    )
    if explicit is not None:
        value = explicit.strip().casefold().replace("->", "2").replace("→", "2")
        aliases = {"envi": "en2vi", "en-vi": "en2vi", "vien": "vi2en", "vi-en": "vi2en"}
        value = aliases.get(value, value)
        if value not in DIRECTIONS:
            raise ValueError(f"Unsupported translation direction: {explicit}")
        return value
    return detect_direction(text)


@dataclass(frozen=True)
class DirectionSettings:
    config: Path
    model_dir: Path


class TranslationRuntime:
    """Lazy-load one direction at a time to keep the VRAM footprint bounded."""

    def __init__(self) -> None:
        self.settings = {
            "en2vi": DirectionSettings(
                Path(os.environ.get("VINAI_EN2VI_CONFIG", "/app/configs/en2vi.json")),
                Path(os.environ.get("VINAI_EN2VI_MODEL_DIR", "/models/en2vi")),
            ),
            "vi2en": DirectionSettings(
                Path(os.environ.get("VINAI_VI2EN_CONFIG", "/app/configs/vi2en.json")),
                Path(os.environ.get("VINAI_VI2EN_MODEL_DIR", "/models/vi2en")),
            ),
        }
        self.batch_size = int(os.environ.get("VINAI_BATCH_SIZE", "8"))
        self.maximum_source_tokens = int(
            os.environ.get("VINAI_MAXIMUM_SOURCE_TOKENS", "448")
        )
        self.allow_cpu = os.environ.get("VINAI_ALLOW_CPU", "0") == "1"
        self._direction: str | None = None
        self._config: ExperimentConfig | None = None
        self._tokenizer: Any = None
        self._model: Any = None
        self.lock = threading.Lock()
        if self.batch_size < 1:
            raise ValueError("VINAI_BATCH_SIZE must be positive")
        if self.maximum_source_tokens < 32:
            raise ValueError("VINAI_MAXIMUM_SOURCE_TOKENS must be at least 32")

    def configured(self) -> dict[str, bool]:
        return {
            direction: setting.config.is_file()
            and setting.model_dir.is_dir()
            and (setting.model_dir / "config.json").is_file()
            for direction, setting in self.settings.items()
        }

    def _load(self, direction: str) -> None:
        if self._direction == direction:
            return
        setting = self.settings[direction]
        if not setting.config.is_file():
            raise FileNotFoundError(f"Missing {direction} config: {setting.config}")
        if not (setting.model_dir / "config.json").is_file():
            raise FileNotFoundError(
                f"Missing merged/offline {direction} model: {setting.model_dir}"
            )
        import torch

        if self._model is not None:
            del self._model
            self._model = None
            self._tokenizer = None
            self._config = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        config = ExperimentConfig.from_json(setting.config)
        if config.direction != direction:
            raise ValueError(
                f"Config direction {config.direction} does not match {direction}"
            )
        if self.allow_cpu:
            config.apply_overrides(allow_cpu=True)
        if config.training.require_cuda and not torch.cuda.is_available():
            raise RuntimeError("CUDA is required by the submission config")
        tokenizer, model = load_inference_model(
            config, saved_model_dir=setting.model_dir
        )
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        if device.type == "cuda" and config.training.fp16:
            model.to(device=device, dtype=torch.float16)
        elif device.type == "cuda" and config.training.bf16:
            model.to(device=device, dtype=torch.bfloat16)
        else:
            model.to(device)
        self._direction = direction
        self._config = config
        self._tokenizer = tokenizer
        self._model = model

    def translate(self, text: str, direction: str) -> tuple[str, dict[str, Any]]:
        if direction not in DIRECTIONS:
            raise ValueError(f"Unknown direction: {direction}")
        with self.lock:
            self._load(direction)
            import torch

            assert self._config is not None
            chunks = split_markdown_document(
                text,
                self._tokenizer,
                maximum_tokens=self.maximum_source_tokens,
            )
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            predictions, report = translate_chunks(
                chunks,
                tokenizer=self._tokenizer,
                model=self._model,
                config=self._config,
                batch_size=self.batch_size,
                device=device,
            )
            output = assemble_document(chunks, predictions)
            report["markdown_structure"] = markdown_structure_report(text, output)
            return output, report


class SubmissionHandler(BaseHTTPRequestHandler):
    runtime: TranslationRuntime
    maximum_request_bytes = int(
        os.environ.get("VINAI_MAXIMUM_REQUEST_BYTES", str(32 * 1024 * 1024))
    )
    server_version = "VLSPDocumentMT/1.0"

    def _send(self, status: int, body: bytes, content_type: str, headers=None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for name, value in (headers or {}).items():
            self.send_header(name, str(value))
        self.end_headers()
        self.wfile.write(body)

    def _error(self, status: int, message: str) -> None:
        body = json.dumps({"error": message}, ensure_ascii=False).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8")

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        if urlparse(self.path).path != "/health":
            self._error(404, "Not found")
            return
        configured = self.runtime.configured()
        payload = {
            "status": "ready" if all(configured.values()) else "incomplete",
            "configured": configured,
            "loaded_direction": self.runtime._direction,
        }
        self._send(
            200 if payload["status"] == "ready" else 503,
            json.dumps(payload).encode("utf-8"),
            "application/json; charset=utf-8",
        )

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
        if urlparse(self.path).path not in {
            "/translate", "/translate/en2vi", "/translate/vi2en"
        }:
            self._error(404, "Not found")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 1:
                raise ValueError("Request body is empty")
            if length > self.maximum_request_bytes:
                self._error(413, "Input document exceeds the request limit")
                return
            raw = self.rfile.read(length)
            content_type = self.headers.get("Content-Type", "").casefold()
            requested_direction = self.headers.get("X-Translation-Direction")
            if "application/json" in content_type:
                payload = json.loads(raw.decode("utf-8"))
                text = str(payload.get("text", ""))
                requested_direction = payload.get("direction", requested_direction)
            else:
                text = raw.decode("utf-8")
            direction = direction_from_request(
                self.path, requested_direction, text
            )
            started = time.perf_counter()
            output, report = self.runtime.translate(text, direction)
            elapsed = time.perf_counter() - started
            input_words = len(text.split())
            stats = {
                "direction": direction,
                "runtime_seconds": round(elapsed, 3),
                "chunks": report["chunks"],
                "input_words": input_words,
                "words_per_second": round(input_words / max(elapsed, 1e-9), 3),
            }
            print(json.dumps(stats, ensure_ascii=False), flush=True)
            self._send(
                200,
                output.encode("utf-8"),
                "text/markdown; charset=utf-8",
                {
                    "X-Translation-Direction": direction,
                    "X-Runtime-Seconds": f"{elapsed:.3f}",
                    "X-Chunk-Count": report["chunks"],
                },
            )
        except UnicodeDecodeError:
            self._error(400, "Input must be UTF-8")
        except ValueError as error:
            self._error(400, str(error))
        except Exception as error:  # preserve traceback in container logs
            self.log_error("Translation failed: %r", error)
            self._error(500, str(error))

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"HTTP {self.address_string()} {fmt % args}", flush=True)


def main() -> None:
    host = os.environ.get("VINAI_HOST", "0.0.0.0")
    port = int(os.environ.get("VINAI_PORT", "8000"))
    SubmissionHandler.runtime = TranslationRuntime()
    server = ThreadingHTTPServer((host, port), SubmissionHandler)
    print(
        json.dumps(
            {
                "event": "ready",
                "host": host,
                "port": port,
                "configured": SubmissionHandler.runtime.configured(),
            }
        ),
        flush=True,
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
