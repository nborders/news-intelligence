# Design Spec: Event Timelines
**Date:** 2026-03-24
**Status:** Approved

---

## Problem

Major ongoing stories — wars, economic crises, political proceedings — span weeks or months of daily analyses. Each day's section covers only what happened that day, with no sense of where today's events fit in the arc of the larger story. A reader picking up the analysis on March 24 has no quick way to understand that Trump's "victory" declaration is day 39 of a conflict that started with a missile strike on Haifa.

---

## Solution Summary

For any section covering a large, ongoing topic, Claude optionally includes a collapsible timeline block beneath the section body. The timeline is:

1. **Vertical** — dates on the left, event titles on the right, connected by a dotted vertical line
2. **Compact by default** — event titles only, no sub-notes visible until hover
3. **Hover tooltip** — mousing over any event row shows a floating card (above the row, same pattern as footnote tooltips) with: full date, event title, context note, and a "Read on Wikipedia" link
4. **Wikipedia-linked** — the timeline header carries a `W` icon + article name linking to the main Wikipedia article for the ongoing topic
5. **Today-marked** — the entry matching today's date gets a gold dot, gold date label, and a `◀` marker
6. **Inline, collapsible** — the timeline lives inside the section's `<details>` block and collapses with it

---

## Approved Visual Design

From brainstorming session 2026-03-24:

```
┌─ Timeline · 2026 Iran War ─────────────── Ⓦ 2026 Iran war ─┐
│                                                              │
│  Feb 13  ●  US–Israel air campaign begins                   │
│  Feb 19  ●  Iran threatens Hormuz closure                   │
│  Mar 4   ●  Bushehr nuclear plant hit                       │
│  Mar 24◀ ●  Trump declares victory; Israel says weeks remain│  ← gold
└──────────────────────────────────────────────────────────────┘

On hover (row):  floating tooltip appears above the row
┌─────────────────────────────────────────┐
│ February 19, 2026                       │
│ Iran threatens Strait of Hormuz closure │
│ IRGC announces it will mine the strait  │
│ if strikes continue. Oil surges to      │
│ $112/barrel. Fifth Fleet repositions.   │
│  [Ⓦ Read on Wikipedia]                  │
└─────────────────────────────────────────┘
```

**Tooltip behavior:**
- Appears above hovered row, 4px gap
- Floats using `position:absolute` + `getBoundingClientRect()` (same as footnote tooltips)
- Clamped to viewport horizontally; flips below row if near top of page
- Invisible bridge (CSS `::after`) fills the gap so mouse can reach the tooltip
- Hide delay: 300ms after leaving the row, 120ms after leaving the tooltip
- `pointer-events:auto` so the Wikipedia link is clickable

---

## Data Format — What Claude Writes

Claude writes timelines as a fenced code block with the language tag `timeline`. The block appears immediately after the section's KEY/WATCH callout, before the closing `---`.

**Syntax:**

````markdown
```timeline 2026 Iran war | https://en.wikipedia.org/wiki/2026_Israel%E2%80%93Iran_war
2026-02-13 | US–Israel air campaign begins | After Iran's missile barrage strikes Haifa's port district, US and Israeli air forces launch coordinated strikes on IRGC infrastructure. | https://en.wikipedia.org/wiki/2026_Israel%E2%80%93Iran_war
2026-02-19 | Iran threatens Hormuz closure | IRGC naval command announces it will mine the strait if strikes continue. Oil surges to $112/barrel. US Fifth Fleet repositions. | https://en.wikipedia.org/wiki/Strait_of_Hormuz
2026-03-04 | Bushehr nuclear plant hit | Israeli strikes disable the reactor's cooling systems. IAEA calls emergency session. | https://en.wikipedia.org/wiki/Bushehr_Nuclear_Power_Plant
2026-03-24 | Trump declares victory; Israel says 3–4 weeks remain | Trump posts "MISSION ACCOMPLISHED" as IDF says Iran's reconstitution capability requires more strikes. ISW notes diverging timelines. | https://en.wikipedia.org/wiki/2026_Israel%E2%80%93Iran_war
```
````

**Header line** (after the language tag, separated by ` | `):
- Field 1: Wikipedia article display name
- Field 2: Wikipedia article URL

**Entry lines** (one per event, ` | ` separated):
- Field 1: ISO date `YYYY-MM-DD`
- Field 2: Short event title (fits on one line)
- Field 3: Context note (1–3 sentences for the tooltip)
- Field 4: Wikipedia URL for this specific event (may be same as main article, or a sub-article)

**Rules for Claude when writing timeline entries:**
- Only include timelines for sections covering major, ongoing multi-week stories
- Add new entries each run — carry forward all previous entries, append today's
- Entries must be in chronological order
- Dates must be ISO format (`YYYY-MM-DD`) — the renderer uses them to detect "today"
- Every entry needs a Wikipedia URL — use the main article URL if no better sub-article exists
- Do not include timelines in: Science & Discovery, Dispatch from the Absurd, Other Consequential Events

---

## File Map

| File | Change |
|------|--------|
| `view_export.py` | Detect `timeline` fenced blocks in `render_markdown()`; emit timeline HTML; add CSS; add JS tooltip logic to `build_js()`; add `#tl-tooltip` div to page template |
| `CLAUDE.md` | Add timeline format instructions and rules to Analysis Format section |

**Not modified:** `wiki_scraper.py`, `news_scraper.py`, `run_daily.py`, `install_launchd.sh`, analysis `.md` files

---

## Rendering — `view_export.py` Changes

### 1. Fenced block detection in `render_markdown()`

When the renderer encounters a fenced block whose language tag starts with `timeline`, instead of emitting a `<pre><code>` block it calls `render_timeline(header, lines)`.

The existing fenced block handler already has `code_lang = line[3:].strip()` — add a branch:

```python
if code_lang.startswith('timeline'):
    out.append(render_timeline(code_lang, code_buf))
else:
    # existing <pre><code> path
```

### 2. `render_timeline(lang_line, lines)` function

Parses the header and entry lines, returns the timeline HTML string.

**Header parsing:** `lang_line` is e.g. `timeline 2026 Iran war | https://en.wikipedia.org/wiki/...`
- Strip the `timeline ` prefix
- Split on ` | ` → `[article_name, wiki_url]`

**Entry parsing:** Each line in `lines` → split on ` | ` → `[date_str, title, note, entry_url]`
- Detect "today": compare `date_str` against `datetime.date.today().isoformat()`
- Format display date: parse ISO date, format as `Mon DD` (e.g. `Feb 13`)
- If `today`: add class `today`, append ` ◀` to the date label

**Output:** Returns a `.tl-box` div containing:
- Header row: `.tl-box-label` ("Timeline · {article_name}") + `.tl-wiki` link with W icon
- `.vtl` container with one `.vtl-row` per entry
- Each row has `data-tip-date`, `data-tip-title`, `data-tip-note`, `data-tip-url` attributes

### 3. CSS additions (end of CSS constant)

New rules for: `.tl-box`, `.tl-box-header`, `.tl-box-label`, `.tl-wiki`, `.vtl` and its children, `.vtl-row.today`, `#tl-tooltip` and its children (`.tip-date`, `.tip-title`, `.tip-note`, `.tip-link`).

### 4. `#tl-tooltip` div in page template

Add once, after `<div id="fn-tooltip">`:
```html
<div id="tl-tooltip"><div class="tip-date" id="tip-date"></div>...Wikipedia link...</div>
```

### 5. JS additions in `build_js()`

Add the `_showTlTip` / `_hideTlTip` functions and event listeners (same pattern as existing footnote tooltip JS). Key values: row-leave delay 300ms, tooltip-leave delay 120ms, invisible bridge via CSS `::after`.

---

## Constraints

- The timeline fenced block is optional — sections without one render normally
- Entries accumulate over time: Claude carries forward all previous entries and appends new ones each run. The analysis `.md` file is the sole source of truth — no separate data file
- Wikipedia URLs are external links — require internet connection when viewing
- The tooltip uses `position:absolute` (not `fixed`) so it scrolls correctly with the page
- On mobile, hover doesn't exist — the tooltip won't appear. Timeline entries are still readable as a plain list. Touch support (tap to show/dismiss) is out of scope for this version

---

## Out of Scope

- Touch/tap support for mobile tooltip (future)
- Automatic Wikipedia URL resolution (Claude provides URLs manually)
- Timeline entries for non-ongoing one-off events
- A separate "all timelines" page or sidebar view
