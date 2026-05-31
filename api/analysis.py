"""Background analysis sessions with cancel and SSE streaming."""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from dataclasses import asdict
from typing import Iterator

logger = logging.getLogger(__name__)

from board import Board
from eval import evaluate
from search import AnalysisUpdate, analyze

ANALYSIS_TIMEOUT_SECONDS = 300


class AnalysisSessionManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cancel_flags: dict[str, threading.Event] = {}

    def ensure_session(self, session_id: str) -> None:
        with self._lock:
            if session_id not in self._cancel_flags:
                self._cancel_flags[session_id] = threading.Event()

    def start_session(self) -> str:
        session_id = str(uuid.uuid4())
        self.ensure_session(session_id)
        return session_id

    def cancel(self, session_id: str) -> bool:
        with self._lock:
            flag = self._cancel_flags.get(session_id)
            if flag is None:
                return False
            flag.set()
            return True

    def _cleanup(self, session_id: str) -> None:
        with self._lock:
            self._cancel_flags.pop(session_id, None)

    def _is_cancelled(self, session_id: str) -> bool:
        with self._lock:
            flag = self._cancel_flags.get(session_id)
            return flag is None or flag.is_set()

    def stream_analysis(self, fen: str, session_id: str) -> Iterator[str]:
        try:
            board = Board.from_fen(fen)
        except ValueError as error:
            yield _sse_event("error", {"detail": str(error)})
            return

        deadline = time.monotonic() + ANALYSIS_TIMEOUT_SECONDS
        updates: list[AnalysisUpdate] = []
        logs: list[str] = []
        done = threading.Event()
        started_at = time.monotonic()

        logger.info("Session %s started for fen=%s", session_id, fen)
        logs.append("Analysis session started")

        def run_search() -> None:
            try:
                analyze(
                    board,
                    deadline=deadline,
                    on_update=lambda update: updates.append(update),
                    on_progress=logs.append,
                )
            finally:
                done.set()

        thread = threading.Thread(target=run_search, daemon=True)
        thread.start()

        last_count = 0
        last_log_count = 0
        while not done.is_set():
            if self._is_cancelled(session_id):
                logger.info("Session %s cancelled", session_id)
                yield _sse_event("cancelled", {"session": session_id})
                return
            if time.monotonic() >= deadline:
                break
            while last_log_count < len(logs):
                message = logs[last_log_count]
                yield _sse_event("log", {"message": message})
                last_log_count += 1
            while last_count < len(updates):
                payload = _update_payload(updates[last_count])
                logger.info(
                    "Session %s depth %d (%dms)",
                    session_id,
                    payload["depth"],
                    payload["elapsed_ms"],
                )
                yield _sse_event("update", payload)
                last_count += 1
            elapsed_ms = int((time.monotonic() - started_at) * 1000)
            yield _sse_event("tick", {"elapsed_ms": elapsed_ms})
            time.sleep(1.0)

        thread.join(timeout=1.0)
        while last_log_count < len(logs):
            yield _sse_event("log", {"message": logs[last_log_count]})
            last_log_count += 1
        while last_count < len(updates):
            payload = _update_payload(updates[last_count])
            yield _sse_event("update", payload)
            last_count += 1

        if self._is_cancelled(session_id):
            logger.info("Session %s cancelled", session_id)
            yield _sse_event("cancelled", {"session": session_id})
            return

        elapsed_ms = int((time.monotonic() - started_at) * 1000)
        logger.info("Session %s done in %dms", session_id, elapsed_ms)
        yield _sse_event(
            "done",
            {
                "session": session_id,
                "elapsed_ms": elapsed_ms,
            },
        )


def static_eval(fen: str) -> dict:
    board = Board.from_fen(fen)
    return {"fen": fen, "static_eval": evaluate(board)}


def _update_payload(update: AnalysisUpdate) -> dict:
    return {
        "depth": update.depth,
        "static_eval": update.static_eval,
        "elapsed_ms": update.elapsed_ms,
        "top_moves": [asdict(move) for move in update.top_moves],
    }


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


session_manager = AnalysisSessionManager()
