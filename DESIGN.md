# Nzila identity in a Tkinter application

How the Nzila visual contract was implemented here, what Tkinter could not do, and the
deliberate deviations. Read this before changing anything under `transcriber/ui/`.

## Where the tokens live

`ui/theme.py` is the single source of truth. Nothing anywhere else hardcodes a colour,
a radius or a duration.

| Token group | Constant |
| --- | --- |
| Dark surfaces | `CHARCOAL`, `SURFACE`, `SURFACE_HIGH`, `BORDER`, `BORDER_SUBTLE` |
| Accent | `TERRA`, `TERRA_LIGHT`, `PAPER` |
| Text | `TEXT`, `TEXT_MUTED` |
| State | `OK`, `WARNING`, `ERROR` |
| Spacing | `SPACE` (4px scale) |
| Radius | `RADIUS_CHIP` 6, `RADIUS_CONTROL` 8, `RADIUS_CARD` 16, `RADIUS_SURFACE` 24 |
| Motion | `T_MICRO` 120, `T_BASE` 200, `T_ENTER` 420, `LINE_DURATION` 1200 |

## The four rules that keep it from going generic

1. **Terracotta is never a mass.** The only filled terracotta in the whole app is the
   single primary button (`Transcribe`). Everything else is stroke: the path line, the
   focus ring, the caret, the running-state text.
2. **Fraunces is display only, always lowercase.** It appears in exactly two places: the
   header title and the empty-state headline. Never in a button, label, table or status.
3. **The line always runs the same way.** `widgets.CURVE` is a single constant, entering
   top-left and leaving bottom-right. It is never mirrored, flipped or duplicated on a
   screen.
4. **Charcoal is the default, not cream.** There is no light mode.

## The path line

`widgets.PathLine` is the only decorative element and doubles as the progress indicator,
which is what the brand asks for — progress is the theme.

- The SVG cubic Bezier is evaluated in Python (`_bezier`) and drawn as 72 short
  `create_line` segments. Tk cannot stroke a gradient, so each segment gets its own
  colour interpolated from `TERRA` to `TERRA_LIGHT` (`_blend`). At this segment count the
  banding is invisible.
- `animate_in()` reproduces `stroke-dasharray` by revealing segments over 1200 ms with
  an eased curve (`_ease` approximates `cubic-bezier(.22,.61,.36,1)`). It runs once on
  window open and once after a language switch rebuilds the tree.
- `track=True` draws the full path in `BORDER_SUBTLE` first and then the covered
  fraction in terracotta. That is the progress widget; there is no `ttk.Progressbar`
  anywhere.
- `_draw()` deletes only items tagged `STROKE_TAG` and calls `tag_lower` on them, so the
  header can draw its typography on the same canvas and have the line pass behind the
  letters instead of being chopped by opaque label boxes.
- `NZ_REDUCED_MOTION=1` stands in for `prefers-reduced-motion`: the line appears already
  drawn. Tk exposes no OS accessibility setting, so this is an environment variable.

## Widgets Tkinter does not have

- **`widgets.Button`** — Tk buttons cannot do rounded corners, so it is a `Canvas`
  drawing a smoothed polygon (`_rounded_points`). It implements the four variants from
  the contract, hover, disabled, and a 2px `TERRA_LIGHT` focus ring at 2px offset. It is
  keyboard reachable (`takefocus`, `Return`, `space`), because a canvas widget gets none
  of that for free.
- **`widgets.Card`** — a `Frame` with a `Canvas` behind it painting a 16px-radius
  rectangle with a 1px border and no shadow, plus an inner frame holding the content.
- **Queue table** — `ttk.Treeview` restyled: no vertical rules, `BORDER_SUBTLE`
  separators, header in the label style, selection on `SURFACE_HIGH` rather than a
  coloured fill. Row state is carried by tag colours *and* the written state name, never
  by colour alone.

## Deliberate deviations

| Contract item | What was done | Why |
| --- | --- | --- |
| `letter-spacing: 0.12em` on labels | `theme.tracked()` inserts spaces between characters | Tk fonts have no tracking. Applied to eyebrows and table headers only. |
| Fraunces at weight 600 | Requested as `bold` | The bundled file is a variable font; Tk selects the closest named instance. |
| No emoji in interface | The privacy line lost the padlock the first spec asked for | Anti-pattern 9 in the contract wins over the earlier requirement. |
| Lucide icons at 1.5px | No icons at all | Tk has no vector icon support and bitmap icons would break the stroke weight. Meaning is carried by words. |
| Shadow on paper surfaces | Not implemented | There is no light mode in this application. |
| The monogram | Absent | It belongs to Nzila, not to a product, and never becomes an app icon. |

## Interface language

`i18n.py` holds both catalogs; `theme`/`widgets` never contain a user-visible string.
Switching language destroys the root frame and calls `_build()` again, which is simpler
and less bug-prone than tracking every widget, and it costs a few milliseconds. Queue,
selection, results and progress survive because they live on the model
(`Batch`, `Job`), not on the widgets.

## Threading contract

- Widgets are touched only on the Tk main thread. Workers publish dataclass events into
  a `queue.Queue`, drained by `MainWindow._drain_events` through `after()`.
- `transcription.preload()` **must** be called on the main thread before starting
  workers. Importing `faster_whisper` builds a Tk root somewhere in its dependency
  chain; doing that off the main thread makes AppKit abort the process with
  *"NSWindow should only be instantiated on the main thread"*. `MainWindow._start()`
  calls it right before `BatchWorker.start()`.
- `Treeview` delivers `<<TreeviewSelect>>` asynchronously, so `_on_list_select` compares
  the incoming index against the current selection before acting. Without that guard,
  selecting a row programmatically feeds the event back into an endless loop that hangs
  `update()`.
