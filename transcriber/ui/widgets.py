"""Nzila widgets that Tkinter does not provide.

Holds the *path line* (the brand signature), buttons with radius and states,
and cards with rounded corners drawn on a ``Canvas``.
"""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import font as tkfont
from typing import Callable, Literal

from .theme import (
    BORDER,
    BORDER_SUBTLE,
    CHARCOAL,
    ERROR,
    LINE_DURATION,
    PAPER,
    RADIUS_CARD,
    RADIUS_CONTROL,
    SURFACE,
    TERRA,
    TERRA_LIGHT,
    TEXT,
    TEXT_MUTED,
    Fonts,
)

# The canonical brand curve in 0-100 coordinates: it enters top-left and
# leaves bottom-right. Never mirror it, never flip it.
CURVE = ((7.0, 0.0), (7.0, 38.0), (96.0, 60.0), (95.0, 100.0))
SEGMENTS = 72
STROKE_TAG = "path-line"


def reduced_motion() -> bool:
    """Allow the entry animation to be switched off (``NZ_REDUCED_MOTION=1``)."""
    return os.environ.get("NZ_REDUCED_MOTION", "").strip() not in ("", "0", "false")


def _blend(color_a: str, color_b: str, ratio: float) -> str:
    """Interpolate two ``#RRGGBB`` colours - used by the line gradient."""
    start = tuple(int(color_a[i : i + 2], 16) for i in (1, 3, 5))
    end = tuple(int(color_b[i : i + 2], 16) for i in (1, 3, 5))
    channels = tuple(round(x + (y - x) * ratio) for x, y in zip(start, end))
    return "#%02X%02X%02X" % channels


def _bezier(t: float) -> tuple[float, float]:
    """Point on the cubic Bezier of the canonical curve."""
    (x0, y0), (x1, y1), (x2, y2), (x3, y3) = CURVE
    u = 1 - t
    a, b, c, d = u**3, 3 * u**2 * t, 3 * u * t**2, t**3
    return (a * x0 + b * x1 + c * x2 + d * x3, a * y0 + b * y1 + c * y2 + d * y3)


def _ease(t: float) -> float:
    """Approximation of ``cubic-bezier(.22,.61,.36,1)``."""
    return 1 - (1 - t) ** 3


class PathLine(tk.Canvas):
    """The brand signature: a terracotta stroke entering high and leaving low.

    Doubles as ornament (the header band) and as progress indicator, where
    ``progress`` draws only the fraction already covered.
    """

    def __init__(
        self,
        master: tk.Misc,
        *,
        height: int = 96,
        width: int = 10,
        thickness: int = 2,
        track: bool = False,
        background: str = CHARCOAL,
    ) -> None:
        super().__init__(
            master,
            height=height,
            width=width,
            background=background,
            highlightthickness=0,
            borderwidth=0,
        )
        self._thickness = thickness
        self._track = track
        self._fraction = 0.0
        self._revealed = 1.0 if reduced_motion() else 0.0
        self._animation: str | None = None
        self.bind("<Configure>", lambda _event: self._draw())

    # ------------------------------------------------------------------- api

    def animate_in(self, duration: int = LINE_DURATION) -> None:
        """Draw the line once, from start to end."""
        if reduced_motion():
            self._revealed = 1.0
            self._draw()
            return
        self._stop_animation()
        step = 16
        frames = max(1, duration // step)

        def tick(frame: int = 0) -> None:
            self._revealed = _ease(min(1.0, frame / frames))
            self._draw()
            if frame < frames:
                self._animation = self.after(step, tick, frame + 1)
            else:
                self._animation = None

        tick()

    @property
    def progress(self) -> float:
        return self._fraction

    @progress.setter
    def progress(self, value: float) -> None:
        self._fraction = min(1.0, max(0.0, float(value)))
        self._draw()

    def reset(self) -> None:
        self._stop_animation()
        self._fraction = 0.0
        self._revealed = 1.0
        self._draw()

    # --------------------------------------------------------------- drawing

    def _stop_animation(self) -> None:
        if self._animation is not None:
            self.after_cancel(self._animation)
            self._animation = None

    def _points(self) -> list[tuple[float, float]]:
        width = max(self.winfo_width(), 1)
        height = max(self.winfo_height(), 1)
        margin = self._thickness
        return [
            (
                margin + _bezier(i / SEGMENTS)[0] / 100 * (width - 2 * margin),
                margin + _bezier(i / SEGMENTS)[1] / 100 * (height - 2 * margin),
            )
            for i in range(SEGMENTS + 1)
        ]

    def _draw(self) -> None:
        # Only the stroke is redrawn: callers may add their own canvas items
        # (the header draws its typography here so the line can cross it).
        self.delete(STROKE_TAG)
        points = self._points()

        if self._track:
            self._stroke(points, 1.0, fixed_color=BORDER_SUBTLE)

        limit = min(self._revealed, self._fraction) if self._track else self._revealed
        if limit > 0:
            self._stroke(points, limit)
        self.tag_lower(STROKE_TAG)

    def _stroke(
        self, points: list[tuple[float, float]], end: float, fixed_color: str | None = None
    ) -> None:
        """Stroke the requested span with a terra to terra-light gradient."""
        for i in range(min(int(end * SEGMENTS), SEGMENTS)):
            x1, y1 = points[i]
            x2, y2 = points[i + 1]
            color = fixed_color or _blend(TERRA, TERRA_LIGHT, i / SEGMENTS)
            self.create_line(
                x1,
                y1,
                x2,
                y2,
                fill=color,
                width=self._thickness,
                capstyle="round",
                smooth=True,
                tags=STROKE_TAG,
            )


def _rounded_points(x1: float, y1: float, x2: float, y2: float, radius: float) -> list[float]:
    """A rounded rectangle expressed as a smoothed polygon."""
    radius = min(radius, abs(x2 - x1) / 2, abs(y2 - y1) / 2)
    return [
        x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
        x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
        x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
    ]


Variant = Literal["primary", "secondary", "tertiary", "destructive"]


class Button(tk.Canvas):
    """Button with radius, states and a visible focus ring.

    Filled terracotta only in the ``primary`` variant, which must be unique on
    the screen; the others are stroke or text.
    """

    HEIGHT = 44
    HEIGHT_COMPACT = 36

    def __init__(
        self,
        master: tk.Misc,
        text: str,
        command: Callable[[], None],
        *,
        variant: Variant = "secondary",
        compact: bool = False,
        min_width: int = 0,
        background: str = CHARCOAL,
    ) -> None:
        self._height = self.HEIGHT_COMPACT if compact else self.HEIGHT
        super().__init__(
            master,
            height=self._height,
            background=background,
            highlightthickness=0,
            borderwidth=0,
            takefocus=True,
            cursor="hand2",
        )
        self._text = text
        self._command = command
        self._variant: Variant = variant
        self._background = background
        self._min_width = min_width
        self._hovered = False
        self._focused = False
        self._enabled = True
        self._apply_width()

        self.bind("<Configure>", lambda _event: self._draw())
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        self.bind("<FocusIn>", self._on_focus_in)
        self.bind("<FocusOut>", self._on_focus_out)
        self.bind("<Return>", self._on_click)
        self.bind("<space>", self._on_click)

    # ------------------------------------------------------------------- api

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        if enabled != self._enabled:
            self._enabled = enabled
            self.configure(takefocus=enabled)
            self._draw()

    def set_text(self, text: str) -> None:
        self._text = text
        self._apply_width()
        self._draw()

    def _apply_width(self) -> None:
        measured = tkfont.Font(font=Fonts.button()).measure(self._text)
        self.configure(width=max(self._min_width, measured + 40))

    # ---------------------------------------------------------------- events

    def _on_enter(self, _event: tk.Event) -> None:
        self._hovered = True
        self._draw()

    def _on_leave(self, _event: tk.Event) -> None:
        self._hovered = False
        self._draw()

    def _on_focus_in(self, _event: tk.Event) -> None:
        self._focused = True
        self._draw()

    def _on_focus_out(self, _event: tk.Event) -> None:
        self._focused = False
        self._draw()

    def _on_click(self, _event: tk.Event) -> str:
        if self._enabled:
            self.focus_set()
            self._command()
        return "break"

    # --------------------------------------------------------------- drawing

    def _colors(self) -> tuple[str | None, str | None, str]:
        """Return ``(fill, outline, text_color)`` for the current state."""
        if not self._enabled:
            return (SURFACE, None, TEXT_MUTED)
        if self._variant == "primary":
            return (TERRA_LIGHT if self._hovered else TERRA, None, PAPER)
        if self._variant == "destructive":
            return (SURFACE if self._hovered else None, ERROR, ERROR)
        if self._variant == "tertiary":
            return (None, None, PAPER if self._hovered else TERRA_LIGHT)
        return (SURFACE if self._hovered else None, BORDER, TEXT)

    def _draw(self) -> None:
        self.delete("all")
        width = max(self.winfo_width(), 1)
        height = max(self.winfo_height(), 1)
        fill, outline, text_color = self._colors()

        if self._focused and self._enabled:
            self.create_polygon(
                _rounded_points(1, 1, width - 1, height - 1, RADIUS_CONTROL + 2),
                fill="",
                outline=TERRA_LIGHT,
                width=2,
                smooth=True,
            )

        if fill or outline:
            self.create_polygon(
                _rounded_points(4, 4, width - 4, height - 4, RADIUS_CONTROL),
                fill=fill or self._background,
                outline=outline or "",
                width=1 if outline else 0,
                smooth=True,
            )

        self.create_text(
            width / 2, height / 2, text=self._text, fill=text_color, font=Fonts.button()
        )
        if self._variant == "tertiary" and self._enabled:
            font = tkfont.Font(font=Fonts.button())
            half = font.measure(self._text) / 2
            baseline = height / 2 + font.metrics("ascent") / 2 + 4
            self.create_line(
                width / 2 - half, baseline, width / 2 + half, baseline, fill=text_color, width=1
            )


class Card(tk.Frame):
    """A 16px-radius surface with a 1px border and no shadow.

    The background is drawn on a ``Canvas`` and the content lives in an inner
    frame, since Tk has no ``border-radius``.
    """

    def __init__(
        self,
        master: tk.Misc,
        *,
        padding: int = 20,
        radius: int = RADIUS_CARD,
        background: str = SURFACE,
        outer_background: str = CHARCOAL,
        border: str = BORDER,
    ) -> None:
        super().__init__(master, background=outer_background)
        self._radius = radius
        self._background = background
        self._border = border

        self._canvas = tk.Canvas(
            self, background=outer_background, highlightthickness=0, borderwidth=0
        )
        self._canvas.place(relwidth=1, relheight=1)
        self.content = tk.Frame(self, background=background)
        self.content.pack(fill="both", expand=True, padx=padding, pady=padding)
        self.bind("<Configure>", lambda _event: self._draw())

    def _draw(self) -> None:
        self._canvas.delete("all")
        width = max(self.winfo_width(), 2)
        height = max(self.winfo_height(), 2)
        self._canvas.create_polygon(
            _rounded_points(1, 1, width - 1, height - 1, self._radius),
            fill=self._background,
            outline=self._border,
            width=1,
            smooth=True,
        )
