# Habit Tracker — Implementation Spec

## Context

This is an addition to an existing local web app (`morning_log/`). The existing app is a morning routine logger. We are adding a habit tracker that becomes the **new tab page**, with the morning log moved to `/morning`.

The existing stack: plain Python `http.server`, vanilla JS, no build tools, no npm, no frameworks. Keep it that way.

---

## Existing files (do not break these)

```
morning_log/
  main.py        ← Python HTTP server, manual routing
  app.js         ← morning log frontend logic
  morning.html   ← RENAME from index.html (update main.py route accordingly)
  style.css      ← shared styles, Gruvbox dark theme
  launch.sh      ← pkills and relaunches main.py, leave unchanged
  morning_log.csv
```

### Rename
- `index.html` → `morning.html`
- Update `main.py`: route `/morning` → `morning.html`, route `/` → `habits.html`

---

## New files to create

```
morning_log/
  habits.html        ← habit tracker page (new tab)
  habits.js          ← habit tracker frontend
  habits_config.py   ← habit definitions, imported by main.py
  habits.csv         ← wide-format CSV, created by server if missing
```

---

## "Today" definition

**Everywhere in both Python and JS:**  
Today = `(now - 4 hours).date()`  
Days roll over at 04:00, not midnight. A user logging at 01:30 is still recording for yesterday.

In Python: `(datetime.now() - timedelta(hours=4)).date()`  
In JS: `new Date(Date.now() - 4 * 3600 * 1000)` then extract local date as `YYYY-MM-DD`.

---

## `habits_config.py`

```python
HABITS = [
    {
        "id":        "meditation",       # stable slug, used as CSV column header — NEVER change
        "label":     "Meditate",         # display name, can change freely
        "group":     "Mind",             # group heading
        "freq":      "daily",            # "daily" or "weekly"
        "criterion": "10+ minutes, eyes closed, no phone",
        "retired":   False,              # True = hidden from UI, CSV column preserved
    },
    # ... more habits
]
```

Rules:
- `id` is the CSV column name. Never rename it once the CSV has data.
- `retired: True` hides from UI but CSV column is kept intact.
- Groups are just strings; habits in the same group string are visually grouped.
- Order in the list = order in the UI within each group.
- Editing this file requires a server restart to take effect.

---

## `habits.csv` format (wide)

```
date,meditation,exercise,reading,stretching
2026-06-01,1,,1,1
2026-06-02,,1,,
2026-06-04,1,1,,1
```

- One row per logical date (`YYYY-MM-DD`, using 4am rollover).
- One column per habit `id`.
- `1` = done, empty = not done. No `0`s written — empty means not done. This makes hand-editing easier.
- Dates with no completions may be entirely absent from the file.
- CSV headers = `date` + all habit IDs from `HABITS` (in order, including retired ones).
- Server creates the file with headers if missing.

---

## Python routes (additions to `main.py`)

```
GET  /                    → habits.html (new tab page)
GET  /morning             → morning.html (was /)
GET  /habits.js           → habits.js
GET  /habits_data         → JSON, see shape below
POST /habits_log          → body: {date, habit_id, value (1 or 0)}
```

Keep all existing routes (`/session`, `/log`, `/style.css`, `/app.js`) unchanged.

### `GET /habits_data` response shape

```json
{
  "today": "2026-06-04",
  "habits": [
    {
      "id": "meditation",
      "label": "Meditate",
      "group": "Mind",
      "freq": "daily",
      "criterion": "10+ minutes, eyes closed, no phone"
    }
  ],
  "rows": {
    "2026-06-04": {"meditation": 1, "exercise": 0},
    "2026-06-03": {"meditation": 0, "exercise": 1}
  }
}
```

- `habits` array: only non-retired habits, in config order.
- `rows`: keyed by date string. Server sends last **30 days** for daily habits, last **84 days** (12 weeks) for weekly — but just send 84 days for all; the JS will slice as needed.
- Missing dates in `rows` = all zeros for that date.
- `value` in POST is `1` or `0`. Server writes `1` or empty to CSV accordingly.

### `POST /habits_log` behaviour

- Read CSV into memory.
- Find or create the row for the given date.
- Set the cell `[date][habit_id]` to `"1"` (if value=1) or `""` (if value=0).
- Write CSV back out.
- Respond `{"ok": true}`.
- If date is more than 1 day in the past (using 4am rollover), still allow it — no validation. The UI won't offer it but hand-edits via POST should work.

---

## Frontend: `habits.html`

Same structure as `morning.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
  <title>Habits</title>
  <link rel="stylesheet" href="/style.css">
</head>
<body>
  <header>
    <h1>Habits</h1>
    <div class="date-line" id="dateLine"></div>
  </header>
  <div id="app"></div>
  <div id="overlay" class="overlay hidden"></div>
  <script src="/habits.js"></script>
</body>
</html>
```

Add a small link in the header area (or below h1) to `/morning` — plain text, dim color, small font. Something like `→ morning log`.

---

## Frontend layout

### Page structure

Max-width container (same as morning log, `max-width: 440px`, centered). On wide screens content stays narrow with vertical aspect ratio — same as the morning log card behaviour.

### Per group

```
MIND                          ← group header: small-caps, dim (--gvb-fg4), uppercase
──────────────────────────    ← 1px line, --gvb-bg3

[habit row]
[habit row]

BODY
──────────────────────────
[habit row]
```

Groups are visual separators only, not collapsible.

### Habit row (collapsed, default)

```
▶ Meditate          ○ ● ○ ●
  ▓░▓▓░▓▓▓░░▓▓▓▓░▓▓▓░░░░░░░░░
```

- `▶` / `▼` toggle (CSS rotation of a single caret character is fine)
- Label text
- Right side: 4 dots
- Below label row: the bar, full width of the habit content area

### The 4 dots

- Left = today, then D−1, D−2, D−3 going right
- Today's dot: slightly larger (~1.25×), uses `--gvb-aqua` when filled, `--gvb-bg3` when empty
- Past dots: standard size, `--gvb-aqua2` when filled, `--gvb-bg2` when empty
- Today's dot is **clickable**: toggles completion, POSTs immediately, re-renders the row
- For weekly habits: dots represent last 4 weeks instead of last 4 days

### The bar

- Sits directly below the label+dots row, no gap
- Full width of the habit row content area (respects card padding)
- Height: 4px
- 30 segments for daily, 12 for weekly
- Left = most recent (today / this week), right = oldest
- Each segment: filled = `--gvb-aqua` at ~60% opacity, empty = `--gvb-bg2`
- Segments separated by 1px gaps (use CSS `gap` on a flex or grid container)
- No border-radius, or 1px max — keep it sharp

### Habit row (expanded, after tapping label)

```
▼ Meditate          ○ ● ○ ●
  ▓░▓▓░▓▓▓░░▓▓▓▓░▓▓▓░░░░░░░░░
  10+ minutes, eyes closed,    ← criterion text, dim, small font
  no phone
  [ heatmap ]                  ← ghost-btn style, left-aligned
```

Accordion animation: simple CSS max-height transition is fine.

---

## Heatmap overlay

Triggered by tapping `[ heatmap ]` inside an expanded habit row.

```
┌─────────────────────────────┐
│ Meditate              [ ✕ ] │
│                             │
│ [52-week grid of squares]   │
│                             │
│ Jan Feb Mar ...             │
└─────────────────────────────┘
```

- Full-screen dark backdrop (`--gvb-bg0_h` at 90% opacity)
- Centered card, same style as `.card` in existing CSS
- Title = habit label
- Grid: 52 columns × 7 rows (weeks × days), left = oldest, right = newest
- Each cell: small square (~10px), `--gvb-aqua` if done, `--gvb-bg2` if not, 2px gap
- Month labels along the top (abbreviated, dim)
- Close: ✕ button top-right, also close on backdrop click
- Use only data already fetched (84 days). Cells beyond available data are rendered empty.
- On mobile the grid should be scrollable horizontally if it overflows

---

## CSS additions to `style.css`

Add these classes. Do not modify existing rules.

```css
/* Habit tracker */
.group-header { ... }        /* small-caps, dim label */
.group-divider { ... }       /* 1px line */
.habit-row { ... }           /* wrapper for one habit */
.habit-label-row { ... }     /* flex row: caret + label + dots */
.habit-caret { ... }         /* ▶ rotates to ▼ when .open */
.habit-dots { ... }          /* flex row of 4 dots */
.habit-dot { ... }           /* single dot circle */
.habit-dot.today { ... }     /* larger, aqua */
.habit-dot.done { ... }      /* filled */
.habit-bar { ... }           /* flex container for segments */
.habit-bar-seg { ... }       /* individual segment */
.habit-bar-seg.done { ... }  /* filled segment */
.habit-accordion { ... }     /* max-height transition */
.habit-accordion.open { ... }
.habit-criterion { ... }     /* criterion text style */
.overlay { ... }             /* full-screen backdrop */
.overlay.hidden { ... }
.heatmap-card { ... }        /* centered overlay card */
.heatmap-grid { ... }        /* CSS grid for squares */
.heatmap-cell { ... }        /* individual square */
.heatmap-cell.done { ... }
.heatmap-months { ... }      /* month label row */
```

---

## `habits.js` logic outline

```
loadHabits()
  → GET /habits_data
  → store data globally
  → computeLogicalToday()
  → render()

render()
  → group habits by .group
  → for each group: renderGroup()
  → for each habit: renderHabitRow()

renderHabitRow(habit, rows, today)
  → compute dot states (last 4 days/weeks)
  → compute bar states (last 30 days / 12 weeks)
  → build HTML
  → attach click handlers

toggleToday(habit_id)
  → read current state
  → POST /habits_log {date: today, habit_id, value: 1 or 0}
  → on success: flip local state, re-render that row only

toggleAccordion(habit_id)
  → toggle .open class on accordion div
  → rotate caret

openHeatmap(habit_id)
  → build heatmap grid from global rows data
  → show overlay

closeHeatmap()
  → hide overlay

computeLogicalToday()
  → new Date(Date.now() - 4*3600*1000)
  → return 'YYYY-MM-DD' string in local time

weekKey(dateStr)
  → given a YYYY-MM-DD, return the Monday of that week as YYYY-MM-DD
  → used to aggregate weekly habit data
```

For weekly habits, "this week is complete" = any day in Mon–Sun of that week has value 1 in `rows`.

---

## Startup & launch

`launch.sh` is unchanged. It kills and restarts `main.py`.  
`main.py` imports `habits_config.py` at the top (`from habits_config import HABITS`).  
`main.py` calls `ensure_habits_csv()` on startup, same pattern as `ensure_csv()`.

`ensure_habits_csv()`:
- Creates `habits.csv` if missing
- Writes header row: `date` + all habit IDs (including retired, to preserve column positions)
- If file exists but is missing columns for new habits, **append the new columns** to the header and backfill empty values for existing rows

---

## Explicit non-goals (do not implement)

- Adding/removing habits from the UI
- Editing past days from the UI (edit `habits.csv` by hand)
- Authentication or multi-user support
- Any JS framework, build step, or package manager
- Monthly habits (dropped from spec)
- Numeric streak counters or labels

---

## Gruvbox color reference (already in style.css as CSS vars)

```
--gvb-aqua:    #689d6a   ← filled dots, filled bar segments, filled heatmap cells
--gvb-aqua2:   #8ec07c   ← past filled dots (slightly brighter)
--gvb-bg0:     #282828   ← page background
--gvb-bg1:     #3c3836   ← card background
--gvb-bg2:     #504945   ← empty dots, empty bar segments
--gvb-bg3:     #665c54   ← borders, group dividers
--gvb-fg1:     #ebdbb2   ← primary text
--gvb-fg4:     #a89984   ← dim text (group headers, criterion text)
--gvb-bg0_h:   #1d2021   ← overlay backdrop
```

Font stacks already defined: `--sans` (Rajdhani/Roboto) and `--mono` (JetBrains Mono/Roboto Mono).

---

## Implementation order suggestion

1. Add routes to `main.py`, rename `index.html` → `morning.html`, update `/morning` route
2. Create `habits_config.py` with 2–3 example habits
3. Implement `ensure_habits_csv()` and `GET /habits_data` in `main.py`
4. Implement `POST /habits_log` in `main.py`
5. Create `habits.html`
6. Create `habits.js` — render only, no interactivity yet
7. Add CSS to `style.css`
8. Wire up dot click (toggle today)
9. Wire up accordion
10. Wire up heatmap overlay
