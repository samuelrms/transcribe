"""Main window: Nzila identity, audio queue and batch transcription."""

from __future__ import annotations

import logging
import queue
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from ..audio import filedialog_filetypes
from ..batch import Batch, Job, JobStatus, unique_path
from ..config import (
    DEFAULT_LANGUAGE_KEY,
    DEFAULT_MODEL,
    DEFAULT_WORKERS,
    HEAVY_MODELS,
    LANGUAGE_CHOICES,
    MODEL_CHOICES,
    MODEL_DOWNLOAD_SIZES,
    WORKER_CHOICES,
)
from ..desktop import reveal_in_file_manager
from ..device import cuda_available
from ..model_store import is_model_cached
from ..i18n import LANGUAGE_NAMES, available_languages, get_language, set_language, t
from ..paths import output_dir
from ..transcription import Transcriber, preload
from . import theme
from .theme import (
    CHARCOAL,
    ERROR,
    OK,
    SURFACE,
    TERRA_LIGHT,
    TEXT,
    TEXT_MUTED,
    WARNING,
    Fonts,
    apply_theme,
    text_widget_options,
    tracked,
)
from .widgets import Button, Card, PathLine
from .worker import (
    BatchDone,
    BatchWorker,
    JobCancelled,
    JobDone,
    JobFailed,
    JobProgress,
    JobStarted,
)

logger = logging.getLogger(__name__)

EVENT_POLL_MS = 80

STATE_COLORS = {
    JobStatus.PENDING: TEXT_MUTED,
    JobStatus.RUNNING: TERRA_LIGHT,
    JobStatus.DONE: OK,
    JobStatus.ERROR: ERROR,
    JobStatus.CANCELLED: TEXT_MUTED,
}

ACTION_KEYS = (
    "action.copy",
    "action.save_txt",
    "action.save_srt",
    "action.save_all",
    "action.open_folder",
    "action.clear",
)


class MainWindow(tk.Tk):
    """Single window: audio queue, options, progress and result."""

    def __init__(self) -> None:
        super().__init__()
        self.minsize(920, 780)
        self._fit_to_screen(1100, 960)

        self._transcriber = Transcriber()
        self._worker = BatchWorker(self._transcriber)
        self._batch = Batch()
        self._selected: int | None = None
        self._status_key = "status.ready"
        self._status_params: dict[str, object] = {}

        self._audio_language_key = tk.StringVar(value=DEFAULT_LANGUAGE_KEY)
        self._model = tk.StringVar(value=DEFAULT_MODEL)
        self._workers = tk.IntVar(value=DEFAULT_WORKERS)
        self._ui_language = tk.StringVar(value=get_language())
        self._use_gpu = tk.BooleanVar(value=cuda_available())  # no CUDA, no control shown
        self._status = tk.StringVar()

        apply_theme(self)
        self._build()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(EVENT_POLL_MS, self._drain_events)
        self.after(120, self._header_line.animate_in)

    def _fit_to_screen(self, width: int, height: int) -> None:
        """Open as large as asked, but never taller than the display."""
        max_height = max(760, self.winfo_screenheight() - 120)
        max_width = max(900, self.winfo_screenwidth() - 80)
        self.geometry(f"{min(width, max_width)}x{min(height, max_height)}")

    # ------------------------------------------------------------------ layout

    def _build(self) -> None:
        """Mount every widget. Re-runnable, which is how language switching works."""
        self.title(t("app.name"))
        self._status.set(t(self._status_key, **self._status_params))

        self._root_frame = tk.Frame(self, background=CHARCOAL)
        self._root_frame.pack(fill="both", expand=True, padx=theme.SPACE[8], pady=theme.SPACE[6])
        self._root_frame.columnconfigure(0, weight=1)
        # The queue and the result share the leftover height, the result taking
        # twice as much. Both have a floor: without one, a short window squeezes
        # the text box and its download buttons down to a single pixel.
        self._root_frame.rowconfigure(1, weight=1, minsize=150)
        self._root_frame.rowconfigure(4, weight=2, minsize=200)

        self._build_header().grid(row=0, column=0, sticky="ew")
        self._build_queue().grid(row=1, column=0, sticky="nsew", pady=(theme.SPACE[4], 0))
        self._build_options().grid(row=2, column=0, sticky="ew", pady=(theme.SPACE[4], 0))
        self._build_action().grid(row=3, column=0, sticky="ew", pady=(theme.SPACE[4], 0))
        self._build_result().grid(row=4, column=0, sticky="nsew", pady=(theme.SPACE[4], 0))
        self._build_footer().grid(row=5, column=0, sticky="ew", pady=(theme.SPACE[3], 0))

        self._refresh_list()
        if self._selected is not None:
            self._select(self._selected)
        self._refresh_buttons()

    def _rebuild(self) -> None:
        """Rebuild the whole tree, used after an interface language change."""
        self._root_frame.destroy()
        self._build()
        self._header_line.animate_in()

    def _build_header(self) -> tk.Widget:
        """Top band: the path line behind the display typography."""
        frame = tk.Frame(self._root_frame, background=CHARCOAL, height=104)
        frame.pack_propagate(False)

        self._header_line = PathLine(frame, height=104, thickness=2)
        self._header_line.pack(fill="both", expand=True)

        # Text is drawn on the line canvas itself: opaque labels on top would
        # chop the stroke, and the line is allowed to cross display type.
        self._header_line.create_text(
            2, 14, text=tracked(t("app.eyebrow")), anchor="w", fill=TEXT_MUTED, font=Fonts.label()
        )
        self._header_line.create_text(
            0, 50, text=t("app.title"), anchor="w", fill=TEXT, font=Fonts.display_m(34)
        )
        self._header_line.create_text(
            2, 88, text=t("app.tagline"), anchor="w", fill=TEXT_MUTED, font=Fonts.body_small()
        )
        return frame

    @staticmethod
    def _label(
        parent: tk.Misc, text: str, font: tuple, color: str, background: str = CHARCOAL, **kwargs
    ) -> tk.Label:
        return tk.Label(
            parent, text=text, font=font, foreground=color, background=background, **kwargs
        )

    def _build_queue(self) -> tk.Widget:
        card = Card(self._root_frame, padding=theme.SPACE[4])
        body = card.content
        body.columnconfigure(0, weight=1)
        body.rowconfigure(1, weight=1, minsize=64)

        top = tk.Frame(body, background=SURFACE)
        top.grid(row=0, column=0, columnspan=2, sticky="ew")
        top.columnconfigure(0, weight=1)
        self._label(
            top, tracked(t("queue.label")), Fonts.label(), TEXT_MUTED, SURFACE
        ).grid(row=0, column=0, sticky="w")
        Button(
            top,
            t("queue.add"),
            self._pick_files,
            variant="secondary",
            compact=True,
            background=SURFACE,
        ).grid(row=0, column=1, sticky="e")

        self._list = ttk.Treeview(
            body,
            columns=("file", "state", "time"),
            show="headings",
            height=4,
            style="Nz.Treeview",
            selectmode="browse",
        )
        self._list.heading("file", text=tracked(t("queue.column.file")), anchor="w")
        self._list.heading("state", text=tracked(t("queue.column.state")), anchor="w")
        self._list.heading("time", text=tracked(t("queue.column.time")), anchor="e")
        self._list.column("file", anchor="w", stretch=True)
        self._list.column("state", anchor="w", width=210, stretch=False)
        self._list.column("time", anchor="e", width=90, stretch=False)
        self._list.grid(row=1, column=0, sticky="nsew", pady=(theme.SPACE[3], 0))
        self._list.bind("<<TreeviewSelect>>", self._on_list_select)
        self._list.bind("<Delete>", lambda _event: self._remove_selected())
        self._list.bind("<BackSpace>", lambda _event: self._remove_selected())
        for status, color in STATE_COLORS.items():
            self._list.tag_configure(status.name, foreground=color)

        scrollbar = ttk.Scrollbar(
            body, orient="vertical", command=self._list.yview, style="Nz.Vertical.TScrollbar"
        )
        scrollbar.grid(row=1, column=1, sticky="ns", pady=(theme.SPACE[3], 0))
        self._list.configure(yscrollcommand=scrollbar.set)

        actions = tk.Frame(body, background=SURFACE)
        actions.grid(row=2, column=0, sticky="w", pady=(theme.SPACE[3], 0))
        self._remove_selected_button = Button(
            actions,
            t("queue.remove_selected"),
            self._remove_selected,
            variant="tertiary",
            compact=True,
            background=SURFACE,
        )
        self._remove_selected_button.pack(side="left", padx=(0, theme.SPACE[2]))
        self._remove_button = Button(
            actions,
            t("queue.remove_done"),
            self._remove_finished,
            variant="tertiary",
            compact=True,
            background=SURFACE,
        )
        self._remove_button.pack(side="left")
        self._clear_queue_button = Button(
            actions,
            t("queue.clear"),
            self._clear_queue,
            variant="tertiary",
            compact=True,
            background=SURFACE,
        )
        self._clear_queue_button.pack(side="left", padx=(theme.SPACE[2], 0))
        return card

    def _build_options(self) -> tk.Widget:
        frame = tk.Frame(self._root_frame, background=CHARCOAL)
        for column in (0, 1, 2, 3):
            frame.columnconfigure(column, weight=1)

        self._language_labels = {t(key): code for key, code in LANGUAGE_CHOICES}
        current_language = t(self._audio_language_key.get())
        self._language_display = tk.StringVar(value=current_language)
        self._combo(
            frame, "options.language", self._language_display, tuple(self._language_labels)
        ).grid(row=0, column=0, sticky="ew", padx=(0, theme.SPACE[4]))
        self._language_display.trace_add("write", lambda *_: self._on_audio_language_change())

        self._combo(frame, "options.model", self._model, MODEL_CHOICES).grid(
            row=0, column=1, sticky="ew", padx=(0, theme.SPACE[4])
        )

        self._worker_labels = {self._worker_label(n): n for n in WORKER_CHOICES}
        self._worker_display = tk.StringVar(value=self._worker_label(self._workers.get()))
        self._combo(
            frame, "options.parallel", self._worker_display, tuple(self._worker_labels)
        ).grid(row=0, column=2, sticky="ew", padx=(0, theme.SPACE[4]))
        self._worker_display.trace_add("write", lambda *_: self._on_workers_change())

        self._interface_labels = {LANGUAGE_NAMES[c]: c for c in available_languages()}
        self._interface_display = tk.StringVar(value=LANGUAGE_NAMES[get_language()])
        self._combo(
            frame, "options.interface", self._interface_display, tuple(self._interface_labels)
        ).grid(row=0, column=3, sticky="ew", padx=(0, theme.SPACE[4]))
        self._interface_display.trace_add("write", lambda *_: self._on_interface_language_change())

        # No CUDA, no control: a permanently disabled checkbox is just noise on
        # machines that can never use it, such as every Mac.
        if cuda_available():
            gpu = tk.Frame(frame, background=CHARCOAL)
            gpu.grid(row=0, column=4, sticky="e")
            self._label(gpu, tracked(t("options.gpu")), Fonts.label(), TEXT_MUTED).pack(anchor="w")
            ttk.Checkbutton(
                gpu,
                text=t("gpu.use"),
                variable=self._use_gpu,
                style="Nz.TCheckbutton",
            ).pack(anchor="w", pady=(8, 0))

        self._notice = self._label(
            frame, "", Fonts.body_small(), WARNING, anchor="w", justify="left"
        )
        self._notice.grid(row=1, column=0, columnspan=5, sticky="ew", pady=(theme.SPACE[2], 0))
        self._model.trace_add("write", lambda *_: self._refresh_notice())
        self._refresh_notice()
        return frame

    @staticmethod
    def _worker_label(count: int) -> str:
        return t("workers.queue") if count == 1 else t("workers.parallel", count=count)

    def _combo(
        self, parent: tk.Misc, label_key: str, variable: tk.StringVar, values: tuple[str, ...]
    ) -> tk.Widget:
        frame = tk.Frame(parent, background=CHARCOAL)
        self._label(frame, tracked(t(label_key)), Fonts.label(), TEXT_MUTED).pack(anchor="w")
        ttk.Combobox(
            frame,
            textvariable=variable,
            values=values,
            state="readonly",
            style="Nz.TCombobox",
            font=Fonts.body(),
        ).pack(anchor="w", fill="x", pady=(6, 0))
        return frame

    def _build_action(self) -> tk.Widget:
        frame = tk.Frame(self._root_frame, background=CHARCOAL)
        frame.columnconfigure(2, weight=1)

        self._transcribe_button = Button(
            frame, t("action.transcribe"), self._start, variant="primary", min_width=210
        )
        self._transcribe_button.grid(row=0, column=0, sticky="w")
        self._cancel_button = Button(
            frame, t("action.cancel"), self._cancel, variant="secondary"
        )
        self._cancel_button.grid(row=0, column=1, sticky="w", padx=(theme.SPACE[3], 0))

        progress = tk.Frame(frame, background=CHARCOAL)
        progress.grid(row=0, column=2, sticky="ew", padx=(theme.SPACE[6], 0))
        self._progress_line = PathLine(progress, height=34, thickness=2, track=True)
        self._progress_line.pack(fill="x")
        tk.Label(
            progress,
            textvariable=self._status,
            font=Fonts.body_small(),
            foreground=TEXT_MUTED,
            background=CHARCOAL,
            anchor="w",
        ).pack(fill="x", pady=(6, 0))
        self._progress_line.progress = self._batch.overall_progress()
        return frame

    def _build_result(self) -> tk.Widget:
        card = Card(self._root_frame, padding=theme.SPACE[4])
        body = card.content
        body.columnconfigure(0, weight=1)
        body.rowconfigure(1, weight=1, minsize=90)

        top = tk.Frame(body, background=SURFACE)
        top.grid(row=0, column=0, columnspan=2, sticky="ew")
        top.columnconfigure(0, weight=1)
        self._label(
            top, tracked(t("result.label")), Fonts.label(), TEXT_MUTED, SURFACE
        ).grid(row=0, column=0, sticky="w")
        self._summary = self._label(
            top, "", Fonts.body_small(), TEXT_MUTED, SURFACE, anchor="e", justify="right"
        )
        self._summary.grid(row=0, column=1, sticky="e")

        self._text = tk.Text(body, height=6, **text_widget_options())
        self._text.grid(row=1, column=0, sticky="nsew", pady=(theme.SPACE[3], 0))
        self._text.tag_configure("empty-title", font=Fonts.display_s(24), foreground=TEXT_MUTED)
        self._text.tag_configure("empty-body", font=Fonts.body(), foreground=TEXT_MUTED)

        scrollbar = ttk.Scrollbar(
            body, orient="vertical", command=self._text.yview, style="Nz.Vertical.TScrollbar"
        )
        scrollbar.grid(row=1, column=1, sticky="ns", pady=(theme.SPACE[3], 0))
        self._text.configure(yscrollcommand=scrollbar.set)

        actions = tk.Frame(body, background=SURFACE)
        actions.grid(row=2, column=0, columnspan=2, sticky="w", pady=(theme.SPACE[4], 0))
        commands = (
            self._copy,
            self._save_txt,
            self._save_srt,
            self._save_all,
            self._open_folder,
            self._clear_all,
        )
        self._action_buttons: dict[str, Button] = {}
        for key, command in zip(ACTION_KEYS, commands):
            button = Button(
                actions, t(key), command, variant="secondary", compact=True, background=SURFACE
            )
            button.pack(side="left", padx=(0, theme.SPACE[2]))
            self._action_buttons[key] = button
        self._show_empty_state()
        return card

    def _build_footer(self) -> tk.Widget:
        frame = tk.Frame(self._root_frame, background=CHARCOAL)
        self._label(frame, t("footer.privacy"), Fonts.body_small(), TEXT_MUTED).pack(anchor="w")
        return frame

    # ------------------------------------------------------------------- input

    def _on_audio_language_change(self) -> None:
        label = self._language_display.get()
        for key, _code in LANGUAGE_CHOICES:
            if t(key) == label:
                self._audio_language_key.set(key)
                return

    def _on_workers_change(self) -> None:
        self._workers.set(self._worker_labels.get(self._worker_display.get(), DEFAULT_WORKERS))
        self._refresh_notice()

    def _on_interface_language_change(self) -> None:
        code = self._interface_labels.get(self._interface_display.get())
        if code and code != get_language():
            set_language(code)
            self._rebuild()

    def _pick_files(self) -> None:
        chosen = filedialog.askopenfilenames(
            title=t("dialog.pick_audio"), filetypes=filedialog_filetypes()
        )
        if not chosen:
            return
        added = self._batch.add(chosen)
        ignored = len(chosen) - added
        self._refresh_list()
        self._refresh_buttons()
        parts = [t("queue.added", added=added)]
        if ignored:
            parts.append(t("queue.ignored", ignored=ignored))
        self._status.set(" · ".join(parts))

    def _refresh_notice(self) -> None:
        workers = self._workers.get()
        model = self._model.get()
        if workers > 1 and model in HEAVY_MODELS:
            self._notice.configure(text=t("warn.parallel_heavy", workers=workers, model=model))
        elif workers > 1:
            self._notice.configure(text=t("warn.parallel_cpu"))
        elif not is_model_cached(model):
            size = MODEL_DOWNLOAD_SIZES.get(model, "")
            self._notice.configure(text=t("hint.download", model=model, size=size) if size else "")
        else:
            # Already downloaded: nothing to warn about.
            self._notice.configure(text="")

    def _start(self) -> None:
        if self._worker.running:
            return
        pending = [(self._batch.index_of(job), job.path) for job in self._batch.pending()]
        if not pending:
            messagebox.showinfo(t("app.name"), t("dialog.need_queue"))
            return

        self._progress_line.progress = 0.0
        self._set_status("status.preparing")
        self.update_idletasks()

        try:
            # Importing faster_whisper builds a Tk root; doing it inside a worker
            # thread aborts the process on macOS, so it has to happen here.
            preload()
            self._worker.start(
                pending,
                model_size=self._model.get(),
                language=dict(LANGUAGE_CHOICES)[self._audio_language_key.get()],
                prefer_gpu=self._use_gpu.get(),
                max_workers=self._workers.get(),
            )
        except Exception as exc:
            logger.exception("Could not start the batch")
            detail = getattr(exc, "display", None)
            self._error(t("error.start_failed"), detail() if callable(detail) else str(exc))
            return
        self._refresh_buttons()

    def _cancel(self) -> None:
        if self._worker.running:
            self._worker.cancel()
            self._set_status("status.cancelling")
            self._cancel_button.set_enabled(False)

    # ------------------------------------------------------------------ events

    def _drain_events(self) -> None:
        try:
            while True:
                try:
                    event = self._worker.events.get_nowait()
                except queue.Empty:
                    break
                self._handle_event(event)
        except Exception:
            logger.exception("Failed to process a batch event")
        finally:
            self.after(EVENT_POLL_MS, self._drain_events)

    def _handle_event(self, event: object) -> None:
        if isinstance(event, JobStarted):
            job = self._job(event.index)
            job.start()
            self._set_status("status.transcribing_file", name=job.name)
        elif isinstance(event, JobProgress):
            job = self._job(event.index)
            job.progress = event.fraction
            job.message = event.message
        elif isinstance(event, JobDone):
            self._job(event.index).finish(event.result)
            if self._selected is None:
                self._select(event.index)
        elif isinstance(event, JobFailed):
            job = self._job(event.index)
            job.fail(event.title)
            logger.warning("Error on %s: %s", job.name, event.title)
        elif isinstance(event, JobCancelled):
            self._job(event.index).cancel()
        elif isinstance(event, BatchDone):
            self._finish_batch()

        self._progress_line.progress = self._batch.overall_progress()
        self._refresh_list(keep_selection=True)
        self._refresh_buttons()

    def _finish_batch(self) -> None:
        self._status.set(self._batch.summary_line())
        self._status_key, self._status_params = "status.ready", {}
        if self._selected is None and self._batch.with_results():
            self._select(self._batch.index_of(self._batch.with_results()[0]))

    def _job(self, index: int) -> Job:
        return self._batch.jobs[index]

    def _set_status(self, key: str, **params: object) -> None:
        self._status_key, self._status_params = key, params
        self._status.set(t(key, **params))

    # -------------------------------------------------------------------- list

    def _refresh_list(self, *, keep_selection: bool = False) -> None:
        selected = self._selected if keep_selection else None
        self._list.delete(*self._list.get_children())
        for index, job in enumerate(self._batch):
            state = job.status.label
            if job.status is JobStatus.RUNNING:
                state = f"{state} · {job.progress:.0%}"
            elif job.status is JobStatus.ERROR and job.error:
                state = f"{state} · {job.error[:40]}"
            self._list.insert(
                "",
                "end",
                iid=str(index),
                values=(job.name, state, job.message if job.status is JobStatus.DONE else ""),
                tags=(job.status.name,),
            )
        if selected is not None:
            self._mark_in_list(selected)

    def _on_list_select(self, _event: object = None) -> None:
        selection = self._list.selection()
        if not selection:
            return
        index = int(selection[0])
        # Tk delivers <<TreeviewSelect>> asynchronously; without this guard,
        # selecting back would feed the event into an endless loop.
        if index != self._selected:
            self._select(index)

    def _select(self, index: int) -> None:
        self._selected = index
        job = self._job(index)
        if job.result is not None:
            self._set_text(job.text)
            self._summary.configure(text=job.result.short_summary())
        else:
            self._show_empty_state()
            self._summary.configure(text="")
        self._mark_in_list(index)
        self._refresh_buttons()

    def _mark_in_list(self, index: int) -> None:
        """Select the row only when it is not selected already."""
        target = str(index)
        if target not in self._list.get_children() or self._list.selection() == (target,):
            return
        self._list.selection_set(target)

    # ----------------------------------------------------------------- actions

    def _selected_job(self) -> Job | None:
        if self._selected is None or self._selected >= len(self._batch):
            return None
        return self._job(self._selected)

    def _copy(self) -> None:
        job = self._selected_job()
        if job is None or not job.text:
            return
        self.clipboard_clear()
        self.clipboard_append(job.text)
        self._set_status("status.copied")

    def _save_txt(self) -> None:
        job = self._selected_job()
        if job and job.result:
            self._save(job, ".txt", job.result.to_txt(), t("dialog.kind_text"))

    def _save_srt(self) -> None:
        job = self._selected_job()
        if job and job.result:
            self._save(job, ".srt", job.result.to_srt(), t("dialog.kind_subtitle"))

    def _save(self, job: Job, extension: str, content: str, kind: str) -> None:
        if not content.strip():
            messagebox.showinfo(t("app.name"), t("dialog.nothing_to_save"))
            return
        target = filedialog.asksaveasfilename(
            title=t("dialog.save", kind=kind),
            defaultextension=extension,
            initialfile=f"{job.path.stem}{extension}",
            initialdir=str(output_dir()),
            filetypes=[(kind, f"*{extension}"), (t("dialog.all_files"), "*.*")],
        )
        if not target:
            return
        try:
            Path(target).write_text(content, encoding="utf-8")
        except OSError as exc:
            logger.exception("Could not save %s", target)
            self._error(
                t("error.save_failed"),
                t("error.save_failed.detail", path=target, reason=exc.strerror or exc),
            )
            return
        self._set_status("status.saved", path=target)

    def _save_all(self) -> None:
        """Export TXT and SRT for every finished job into a single folder."""
        finished = self._batch.with_results()
        if not finished:
            messagebox.showinfo(t("app.name"), t("dialog.nothing_done"))
            return
        folder = filedialog.askdirectory(title=t("dialog.save_all"), initialdir=str(output_dir()))
        if not folder:
            return

        destination = Path(folder)
        written = 0
        failures: list[str] = []
        for job in finished:
            assert job.result is not None
            for extension, content in ((".txt", job.result.to_txt()), (".srt", job.result.to_srt())):
                try:
                    unique_path(destination, job.path.stem, extension).write_text(
                        content, encoding="utf-8"
                    )
                    written += 1
                except OSError as exc:
                    logger.exception("Could not export %s", job.name)
                    failures.append(f"{job.name}: {exc.strerror or exc}")

        if failures:
            self._error(
                t("error.save_some_failed"),
                t(
                    "error.save_some_failed.detail",
                    count=written,
                    failures="\n".join(failures),
                ),
            )
            return
        self._set_status("status.saved_many", count=written, path=destination)

    def _open_folder(self) -> None:
        job = self._selected_job()
        if job is None:
            messagebox.showinfo(t("app.name"), t("dialog.need_selection"))
            return
        try:
            reveal_in_file_manager(job.path)
        except Exception as exc:
            logger.exception("Could not open the folder")
            self._error(
                t("error.open_folder"),
                t("error.open_folder.detail", path=job.path, reason=exc),
            )

    def _remove_selected(self) -> None:
        """Drop the highlighted file from the queue, keeping the rest untouched."""
        index = self._selected
        if index is None or index >= len(self._batch):
            messagebox.showinfo(t("app.name"), t("dialog.need_selection"))
            return
        if self._job(index).status is JobStatus.RUNNING:
            messagebox.showinfo(t("app.name"), t("dialog.cannot_remove_running"))
            return
        if self._guard_busy(t("queue.busy")):
            return

        self._batch.remove(index)
        self._selected = min(index, len(self._batch) - 1) if len(self._batch) else None
        self._refresh_list()
        if self._selected is None:
            self._show_empty_state()
            self._summary.configure(text="")
            self._progress_line.progress = self._batch.overall_progress()
        else:
            self._select(self._selected)
        self._refresh_buttons()

    def _remove_finished(self) -> None:
        if self._guard_busy(t("queue.busy")):
            return
        self._batch.remove_finished()
        self._selected = None
        self._show_empty_state()
        self._summary.configure(text="")
        self._refresh_list()
        self._refresh_buttons()

    def _clear_queue(self) -> None:
        if self._guard_busy(t("queue.busy")):
            return
        self._batch.clear()
        self._clear_all()

    def _clear_all(self) -> None:
        if self._guard_busy(t("dialog.busy_clear")):
            return
        self._selected = None
        self._show_empty_state()
        self._summary.configure(text="")
        self._progress_line.reset()
        self._set_status("status.ready")
        self._refresh_list()
        self._refresh_buttons()

    def _guard_busy(self, message: str) -> bool:
        if self._worker.running:
            messagebox.showinfo(t("app.name"), message)
            return True
        return False

    # ------------------------------------------------------------------ states

    def _set_text(self, value: str) -> None:
        self._text.delete("1.0", "end")
        if value:
            self._text.insert("1.0", value)

    def _show_empty_state(self) -> None:
        """The empty state is an invitation, and where the brand voice shows up."""
        self._text.delete("1.0", "end")
        self._text.insert("1.0", t("result.empty_title") + "\n", "empty-title")
        self._text.insert("end", t("result.empty_body"), "empty-body")

    def _refresh_buttons(self) -> None:
        busy = self._worker.running
        job = self._selected_job()
        has_text = bool(job and job.text)
        has_result = bool(job and job.result)

        self._transcribe_button.set_enabled(not busy and bool(self._batch.pending()))
        self._cancel_button.set_enabled(busy)
        self._remove_selected_button.set_enabled(not busy and job is not None)
        self._remove_button.set_enabled(not busy and len(self._batch) > 0)
        self._clear_queue_button.set_enabled(not busy and len(self._batch) > 0)

        enabled = {
            "action.copy": has_text,
            "action.save_txt": has_result,
            "action.save_srt": has_result,
            "action.save_all": bool(self._batch.with_results()),
            "action.open_folder": job is not None,
            "action.clear": not busy,
        }
        for key, is_enabled in enabled.items():
            self._action_buttons[key].set_enabled(is_enabled)

    def _error(self, title: str, detail: str) -> None:
        messagebox.showerror(t("app.name"), detail)
        self._status.set(title)

    def _on_close(self) -> None:
        if self._worker.running:
            if not messagebox.askyesno(t("app.name"), t("dialog.confirm_close")):
                return
            self._worker.cancel()
        self.destroy()


def run() -> int:
    window = MainWindow()
    window.mainloop()
    return 0
