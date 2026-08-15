"""Nzila visual identity mapped onto Tkinter.

Rules the rest of the interface has to respect:
  - terracotta is never a mass: only strokes, details and actions, with a
    single primary button per screen;
  - Fraunces is display only, always lowercase;
  - Instrument Sans carries every functional piece of the interface;
  - no shadows over charcoal - depth comes from surface plus a 1px border;
  - the path line is the only decorative element.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk
from typing import Final

from ..fonts import DISPLAY_CANDIDATES, SANS_CANDIDATES, register_bundled_fonts, resolve_family

# --------------------------------------------------------------------- colour

CHARCOAL: Final = "#1A1714"
SURFACE: Final = "#2E2925"
SURFACE_HIGH: Final = "#3A3430"
BORDER: Final = "#3A3430"
BORDER_SUBTLE: Final = "#26211D"

PAPER: Final = "#F4EFE8"
TERRA: Final = "#C4552F"
TERRA_LIGHT: Final = "#D98E4A"

TEXT: Final = "#F4EFE8"
TEXT_MUTED: Final = "#8A817A"

OK: Final = "#7D9270"
WARNING: Final = "#C9A227"
ERROR: Final = "#E0736C"

# --------------------------------------------------------------------- metric

SPACE: Final = {1: 4, 2: 8, 3: 12, 4: 16, 6: 24, 8: 32, 12: 48, 16: 64}
RADIUS_CHIP: Final = 6
RADIUS_CONTROL: Final = 8
RADIUS_CARD: Final = 16
RADIUS_SURFACE: Final = 24

T_MICRO: Final = 120
T_BASE: Final = 200
T_ENTER: Final = 420
LINE_DURATION: Final = 1200

# ----------------------------------------------------------------- typography


class Fonts:
    """Families resolved once, with fallbacks when registration fails."""

    display: str = "Georgia"
    sans: str = "Helvetica"

    @classmethod
    def resolve(cls, root: tk.Misc) -> None:
        available = set(tkfont.families(root))
        cls.display = resolve_family(DISPLAY_CANDIDATES, available, "Georgia")
        cls.sans = resolve_family(SANS_CANDIDATES, available, "Helvetica")

    # Negative sizes are pixels, matching the design scale.
    @classmethod
    def display_m(cls, size: int = 30) -> tuple:
        return (cls.display, -size, "bold")

    @classmethod
    def display_s(cls, size: int = 22) -> tuple:
        return (cls.display, -size, "bold")

    @classmethod
    def heading(cls) -> tuple:
        return (cls.sans, -18, "bold")

    @classmethod
    def body(cls) -> tuple:
        return (cls.sans, -14)

    @classmethod
    def body_small(cls) -> tuple:
        return (cls.sans, -13)

    @classmethod
    def label(cls) -> tuple:
        return (cls.sans, -11, "bold")

    @classmethod
    def button(cls) -> tuple:
        return (cls.sans, -14, "bold")

    @classmethod
    def data(cls) -> tuple:
        return (cls.sans, -13)


def tracked(text: str) -> str:
    """Emulate ``letter-spacing: 0.12em`` on labels - Tk has no tracking."""
    return " ".join(text.upper())


# --------------------------------------------------------------------- styles


def apply_theme(root: tk.Misc) -> ttk.Style:
    """Apply the palette to the root window and the few ttk widgets in use."""
    register_bundled_fonts()
    Fonts.resolve(root)

    style = ttk.Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")

    root.configure(background=CHARCOAL)

    style.configure(".", background=CHARCOAL, foreground=TEXT, font=Fonts.body())
    style.configure("TFrame", background=CHARCOAL)
    style.configure("TLabel", background=CHARCOAL, foreground=TEXT)

    _style_combobox(style, root)
    _style_check(style)
    _style_scrollbar(style)
    _style_tree(style)
    return style


def _style_combobox(style: ttk.Style, root: tk.Misc) -> None:
    style.configure(
        "Nz.TCombobox",
        fieldbackground=SURFACE,
        background=SURFACE,
        foreground=TEXT,
        arrowcolor=TEXT_MUTED,
        bordercolor=BORDER,
        lightcolor=BORDER,
        darkcolor=BORDER,
        selectbackground=SURFACE,
        selectforeground=TEXT,
        padding=(10, 8),
    )
    style.map(
        "Nz.TCombobox",
        fieldbackground=[("readonly", SURFACE)],
        bordercolor=[("focus", TERRA)],
        arrowcolor=[("active", TERRA_LIGHT)],
    )
    # The dropdown is a classic Tk listbox, configured through the option database.
    root.option_add("*TCombobox*Listbox.background", SURFACE)
    root.option_add("*TCombobox*Listbox.foreground", TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", SURFACE_HIGH)
    root.option_add("*TCombobox*Listbox.selectForeground", TEXT)
    root.option_add("*TCombobox*Listbox.borderWidth", 0)


def _style_check(style: ttk.Style) -> None:
    style.configure(
        "Nz.TCheckbutton",
        background=CHARCOAL,
        foreground=TEXT,
        indicatorbackground=SURFACE,
        indicatorforeground=TERRA,
        focuscolor=TERRA_LIGHT,
        font=Fonts.body_small(),
    )
    style.map(
        "Nz.TCheckbutton",
        indicatorbackground=[("selected", TERRA), ("disabled", SURFACE)],
        foreground=[("disabled", TEXT_MUTED)],
    )


def _style_scrollbar(style: ttk.Style) -> None:
    style.configure(
        "Nz.Vertical.TScrollbar",
        background=SURFACE_HIGH,
        troughcolor=CHARCOAL,
        bordercolor=CHARCOAL,
        arrowcolor=TEXT_MUTED,
        width=10,
    )
    style.map("Nz.Vertical.TScrollbar", background=[("active", TEXT_MUTED)])


def _style_tree(style: ttk.Style) -> None:
    """Table without vertical rules and with a label-styled header."""
    style.configure(
        "Nz.Treeview",
        background=SURFACE,
        fieldbackground=SURFACE,
        foreground=TEXT,
        bordercolor=BORDER,
        borderwidth=0,
        rowheight=30,
        font=Fonts.data(),
    )
    style.configure(
        "Nz.Treeview.Heading",
        background=CHARCOAL,
        foreground=TEXT_MUTED,
        font=Fonts.label(),
        relief="flat",
        borderwidth=0,
        padding=(8, 6),
    )
    style.map(
        "Nz.Treeview", background=[("selected", SURFACE_HIGH)], foreground=[("selected", TEXT)]
    )
    style.map("Nz.Treeview.Heading", background=[("active", CHARCOAL)])
    style.layout("Nz.Treeview", [("Nz.Treeview.treearea", {"sticky": "nswe"})])


def text_widget_options() -> dict[str, object]:
    """Options for the transcription box (``tk.Text`` is not a ttk widget)."""
    return {
        "background": SURFACE,
        "foreground": TEXT,
        "insertbackground": TERRA_LIGHT,
        "selectbackground": SURFACE_HIGH,
        "selectforeground": TEXT,
        "relief": "flat",
        "borderwidth": 0,
        "highlightthickness": 0,
        "padx": 20,
        "pady": 16,
        "wrap": "word",
        "spacing1": 2,
        "spacing3": 6,
        "font": Fonts.body(),
    }
