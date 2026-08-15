"""Batch execution off the interface thread.

A thread pool drains the file queue and publishes events; the interface reads
them through ``root.after``, so no widget is ever touched outside the Tkinter
main thread.
"""

from __future__ import annotations

import logging
import queue
import threading
from dataclasses import dataclass
from pathlib import Path

from ..errors import AppError, TranscriptionCancelled
from ..i18n import t
from ..transcription import Transcriber, TranscriptionResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class JobStarted:
    index: int


@dataclass(frozen=True, slots=True)
class JobProgress:
    index: int
    fraction: float
    message: str


@dataclass(frozen=True, slots=True)
class JobDone:
    index: int
    result: TranscriptionResult


@dataclass(frozen=True, slots=True)
class JobFailed:
    index: int
    title: str
    detail: str


@dataclass(frozen=True, slots=True)
class JobCancelled:
    index: int


@dataclass(frozen=True, slots=True)
class BatchDone:
    pass


Event = JobStarted | JobProgress | JobDone | JobFailed | JobCancelled | BatchDone


class BatchWorker:
    """Transcription pool with cooperative cancellation.

    ``max_workers=1`` processes the queue one file at a time, which is the
    default because CTranslate2 already uses every core on a single file.
    """

    def __init__(self, transcriber: Transcriber) -> None:
        self._transcriber = transcriber
        self.events: queue.Queue[Event] = queue.Queue()
        self._cancel = threading.Event()
        self._threads: list[threading.Thread] = []
        self._queue: queue.Queue[tuple[int, Path]] = queue.Queue()

    @property
    def running(self) -> bool:
        return any(thread.is_alive() for thread in self._threads)

    def start(
        self,
        items: list[tuple[int, Path]],
        *,
        model_size: str,
        language: str | None,
        prefer_gpu: bool,
        max_workers: int = 1,
    ) -> None:
        if self.running:
            raise RuntimeError("A batch is already running.")
        if not items:
            self.events.put(BatchDone())
            return

        self._cancel.clear()
        self._queue = queue.Queue()
        for item in items:
            self._queue.put(item)

        workers = max(1, min(int(max_workers), len(items)))
        self._transcriber.set_num_workers(workers)

        self._threads = [
            threading.Thread(
                target=self._consume,
                args=(model_size, language, prefer_gpu),
                name=f"transcription-{i + 1}",
                daemon=True,
            )
            for i in range(workers)
        ]
        for thread in self._threads:
            thread.start()
        threading.Thread(target=self._await_end, name="batch-end", daemon=True).start()

    def cancel(self) -> None:
        self._cancel.set()

    # ----------------------------------------------------------------- internal

    def _await_end(self) -> None:
        for thread in self._threads:
            thread.join()
        self.events.put(BatchDone())

    def _consume(self, model_size: str, language: str | None, prefer_gpu: bool) -> None:
        while True:
            try:
                index, path = self._queue.get_nowait()
            except queue.Empty:
                return

            if self._cancel.is_set():
                self.events.put(JobCancelled(index))
                continue

            self.events.put(JobStarted(index))
            self._transcribe(index, path, model_size, language, prefer_gpu)

    def _transcribe(
        self, index: int, path: Path, model_size: str, language: str | None, prefer_gpu: bool
    ) -> None:
        try:
            result = self._transcriber.transcribe(
                path,
                model_size=model_size,
                language=language,
                prefer_gpu=prefer_gpu,
                progress=lambda fraction, message: self.events.put(
                    JobProgress(index, fraction, message)
                ),
                should_cancel=self._cancel.is_set,
            )
        except TranscriptionCancelled:
            self.events.put(JobCancelled(index))
        except AppError as exc:
            self.events.put(JobFailed(index, exc.message, exc.display()))
        except Exception as exc:  # safety net: never leak a traceback to the screen
            logger.exception("Unexpected error transcribing %s", path)
            self.events.put(
                JobFailed(
                    index,
                    t("error.unexpected"),
                    t("error.unexpected.detail", kind=type(exc).__name__)
                    + "\n\n"
                    + t("error.log_hint"),
                )
            )
        else:
            self.events.put(JobDone(index, result))
