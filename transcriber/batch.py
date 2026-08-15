"""Batch model: file queue, per-job state and aggregate progress.

Pure logic with no threads and no Tkinter, which makes it fully testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Iterable

from .audio import is_supported_audio
from .i18n import t
from .transcription import TranscriptionResult


class JobStatus(Enum):
    """Where a single file is in its lifecycle."""

    PENDING = "state.pending"
    RUNNING = "state.running"
    DONE = "state.done"
    ERROR = "state.error"
    CANCELLED = "state.cancelled"

    @property
    def is_final(self) -> bool:
        return self in (JobStatus.DONE, JobStatus.ERROR, JobStatus.CANCELLED)

    @property
    def label(self) -> str:
        """Translated name, resolved at call time."""
        return t(self.value)


@dataclass
class Job:
    """One audio file inside the batch."""

    path: Path
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0
    message: str = ""
    result: TranscriptionResult | None = None
    error: str | None = None

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def text(self) -> str:
        return self.result.text if self.result else ""

    def start(self) -> None:
        self.status = JobStatus.RUNNING
        self.progress = 0.0
        self.message = ""
        self.error = None

    def finish(self, result: TranscriptionResult) -> None:
        self.status = JobStatus.DONE
        self.progress = 1.0
        self.result = result
        self.message = f"{result.elapsed:.1f}s"

    def fail(self, message: str) -> None:
        self.status = JobStatus.ERROR
        self.progress = 0.0
        self.error = message
        self.message = message

    def cancel(self) -> None:
        self.status = JobStatus.CANCELLED
        self.progress = 0.0
        self.message = ""


@dataclass
class Batch:
    """Ordered collection of jobs without duplicates."""

    jobs: list[Job] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.jobs)

    def __iter__(self):
        return iter(self.jobs)

    def add(self, paths: Iterable[str | Path]) -> int:
        """Add supported, not-yet-queued files. Returns how many were added."""
        known = {job.path for job in self.jobs}
        added = 0
        for raw in paths:
            path = Path(raw).expanduser()
            resolved = path.resolve() if path.exists() else path
            if resolved in known or not is_supported_audio(resolved):
                continue
            self.jobs.append(Job(path=resolved))
            known.add(resolved)
            added += 1
        return added

    def clear(self) -> None:
        self.jobs.clear()

    def remove(self, index: int) -> Job | None:
        """Drop one job by position. Returns it, or ``None`` when out of range."""
        if 0 <= index < len(self.jobs):
            return self.jobs.pop(index)
        return None

    def remove_finished(self) -> None:
        self.jobs = [job for job in self.jobs if not job.status.is_final]

    def pending(self) -> list[Job]:
        return [job for job in self.jobs if job.status is JobStatus.PENDING]

    def with_results(self) -> list[Job]:
        return [job for job in self.jobs if job.result is not None]

    def index_of(self, job: Job) -> int:
        return self.jobs.index(job)

    def count(self, status: JobStatus) -> int:
        return sum(1 for job in self.jobs if job.status is status)

    def overall_progress(self) -> float:
        """Average progress across every job, from 0 to 1."""
        if not self.jobs:
            return 0.0
        total = sum(1.0 if job.status is JobStatus.DONE else job.progress for job in self.jobs)
        return min(1.0, total / len(self.jobs))

    def summary_line(self) -> str:
        """For example ``3 concluído(s) · 1 transcrevendo · 2 na fila``."""
        counts = (
            ("count.done", self.count(JobStatus.DONE)),
            ("count.running", self.count(JobStatus.RUNNING)),
            ("count.pending", self.count(JobStatus.PENDING)),
            ("count.error", self.count(JobStatus.ERROR)),
            ("count.cancelled", self.count(JobStatus.CANCELLED)),
        )
        chunks = [t(key, count=value) for key, value in counts if value]
        return " · ".join(chunks) if chunks else t("queue.empty")


def unique_path(directory: Path, stem: str, extension: str) -> Path:
    """A free path inside ``directory``, appending ``-2``, ``-3``... if needed."""
    candidate = directory / f"{stem}{extension}"
    counter = 2
    while candidate.exists():
        candidate = directory / f"{stem}-{counter}{extension}"
        counter += 1
    return candidate
