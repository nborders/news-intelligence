# Event Timelines Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add collapsible vertical event timelines to analysis sections, with hover tooltips matching the existing footnote tooltip pattern, and a Wikipedia link on the timeline header.

**Architecture:** Four changes to `view_export.py` only: (1) `render_timeline()` function that parses a fenced `timeline` block from the analysis markdown and emits timeline HTML; (2) fenced block state machine added to the `render_analysis()` rendering loop to detect and dispatch `timeline` blocks; (3) CSS rules for the timeline and floating tooltip; (4) `#tl-tooltip` div + JS in `build_js()`. Plus one change to `CLAUDE.md` to document the timeline format. No new files in the main workflow.

**Tech Stack:** Python (stdlib + `datetime`), HTML/CSS/JS — no new dependencies.

---

## Visual Mockup

### Before (current output — no timeline)

```
┌─────────────────────────────────────────────────────────┐
│  ▾ Iran War — The One-Month Mark                        │
│    Trump declares victory while Israel says weeks remain │
│  ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄  │
│  [body paragraphs]                                       │
│  KEY: Trump's political clock and Israel's military...   │
│                                                          │
│  ```timeline 2026 Iran war | https://...                 │  ← rendered as
│  2026-02-13 | US–Israel air campaign begins | ...        │    raw <pre> text
│  ```                                                     │    (broken)
└─────────────────────────────────────────────────────────┘
```

### After (this plan implements)

```
┌─────────────────────────────────────────────────────────┐
│  ▾ Iran War — The One-Month Mark                        │
│    Trump declares victory while Israel says weeks remain │
│  ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄  │
│  [body paragraphs]                                       │
│  KEY: Trump's political clock and Israel's military...   │
│                                                          │
│  ┌─ Timeline · 2026 Iran War ──────── Ⓦ 2026 Iran war ─┐│
│  │  Feb 13  ●  US–Israel air campaign begins            ││
│  │  Feb 19  ●  Iran threatens Hormuz closure            ││
│  │  Mar 4   ●  Bushehr nuclear plant hit                ││
│  │  Mar 24◀ ●  Trump declares victory; Israel disagrees ││  ← gold dot
│  └──────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘

On hover (any row) — floating tooltip appears above the row:
┌─────────────────────────────────────────┐
│ February 19, 2026                       │
│ Iran threatens Strait of Hormuz closure │
│ IRGC announces it will mine the strait  │
│ if strikes continue. Oil surges to      │
│ $112/barrel. Fifth Fleet repositions.   │
│ [Ⓦ Read on Wikipedia]                   │
└─────────────────────────────────────────┘
300ms hide delay (row leave), 120ms (tooltip leave)
Tooltip has pointer-events:auto so the link is clickable.
```

---

## File Map

| File | Change |
|------|--------|
| `view_export.py` | Add `import datetime`; add `render_timeline()` before `wrap_sections()`; add fenced block state machine to `render_analysis()` loop; append CSS; add `#tl-tooltip` div; add JS to `build_js()` |
| `CLAUDE.md` | Add timeline format block to Analysis Format section |
| `tests/test_timelines.py` | New — unit tests for `render_timeline()` |

**Not modified:** `wiki_scraper.py`, `news_scraper.py`, `run_daily.py`, `install_launchd.sh`, analysis `.md` files (except one used for visual verification).

---

## Task 1: `render_timeline()` function + tests

**Files:**
- Modify: `view_export.py` — add `import datetime` at line 28 (with other imports); add `render_timeline()` just before `wrap_sections()` at line 539
- Create: `tests/test_timelines.py`

**Context:** `render_timeline()` is a pure function. It takes `lang_line` (the full language tag string, e.g. `"timeline 2026 Iran war | https://en.wikipedia.org/wiki/..."`) and `lines` (a list of entry strings, each `"YYYY-MM-DD | title | note | url"`). It returns a complete `.tl-box` HTML string. `datetime` is not yet imported in `view_export.py` — add it. The function lives just before `wrap_sections()` at ~line 539.

- [ ] **Step 1: Create `tests/` directory and write failing tests**

Create `/Users/bart/Desktop/claude/tools/wiki-scraper/tests/test_timelines.py`:

```python
"""Tests for render_timeline() in view_export.py"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import datetime
from unittest.mock import patch
from view_export import render_timeline

FIXED_TODAY = "2026-03-24"

def _render(lang_line, lines):
    """Render with today fixed to 2026-03-24."""
    with patch("view_export.datetime") as mock_dt:
        mock_dt.date.today.return_value = datetime.date(2026, 3, 24)
        mock_dt.date.fromisoformat.side_effect = datetime.date.fromisoformat
        return render_timeline(lang_line, lines)

def test_header_article_name_and_wiki_link():
    html = _render(
        "timeline 2026 Iran war | https://en.wikipedia.org/wiki/2026_Iran_war",
        ["2026-02-13 | Campaign begins | Some note | https://en.wikipedia.org/wiki/2026_Iran_war"]
    )
    assert "Timeline · 2026 Iran war" in html
    assert 'href="https://en.wikipedia.org/wiki/2026_Iran_war"' in html
    assert "tl-wiki" in html

def test_entry_renders_date_and_title():
    html = _render(
        "timeline Test | https://en.wikipedia.org/wiki/Test",
        ["2026-02-13 | Campaign begins | A note | https://en.wikipedia.org/wiki/Test"]
    )
    assert "Feb 13" in html
    assert "Campaign begins" in html
    assert 'class="vtl-date"' in html
    assert 'class="vtl-event"' in html

def test_today_entry_gets_today_class_and_marker():
    html = _render(
        "timeline Test | https://en.wikipedia.org/wiki/Test",
        [f"{FIXED_TODAY} | Today thing | A note | https://en.wikipedia.org/wiki/Test"]
    )
    assert "today" in html
    assert "◀" in html
    assert "Today" in html  # full date in data-tip-date

def test_non_today_entry_has_no_today_class():
    html = _render(
        "timeline Test | https://en.wikipedia.org/wiki/Test",
        ["2026-02-13 | Past event | A note | https://en.wikipedia.org/wiki/Test"]
    )
    assert 'class="vtl-row today"' not in html

def test_data_tip_attributes_set():
    html = _render(
        "timeline Test | https://en.wikipedia.org/wiki/Test",
        ["2026-02-13 | My title | My note | https://en.wikipedia.org/wiki/Sub"]
    )
    assert 'data-tip-title="My title"' in html
    assert 'data-tip-note="My note"' in html
    assert 'data-tip-url="https://en.wikipedia.org/wiki/Sub"' in html

def test_empty_lines_skipped():
    html = _render(
        "timeline Test | https://en.wikipedia.org/wiki/Test",
        ["", "2026-02-13 | Event | Note | https://en.wikipedia.org/wiki/Test", ""]
    )
    # Should still render the one valid entry
    assert "Event" in html
    # Should not have extra empty rows
    assert html.count('class="vtl-row') == 1

def test_html_escaping():
    html = _render(
        "timeline Test & More | https://en.wikipedia.org/wiki/Test",
        ['2026-02-13 | Title <b>bold</b> | Note "quoted" | https://en.wikipedia.org/wiki/Test']
    )
    assert "<b>" not in html
    assert "&lt;b&gt;" in html
    assert "&quot;" in html

if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"  ✓ {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  ✗ {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    if failed:
        sys.exit(1)
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /Users/bart/Desktop/claude/tools/wiki-scraper
python3 tests/test_timelines.py
```

Expected: `ImportError: cannot import name 'render_timeline' from 'view_export'`

- [ ] **Step 3: Add `import datetime` to `view_export.py`**

At line 28 (after `import argparse`), find the imports block:
```python
import argparse
import html
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path
```

Add `import datetime` after `import argparse`:
```python
import argparse
import datetime
import html
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path
```

- [ ] **Step 4: Add `render_timeline()` to `view_export.py`**

Add this function just before `wrap_sections()` (currently at line 539, will shift by 1 after adding the import):

```python
def render_timeline(lang_line: str, lines: list[str]) -> str:
    """
    Render a ```timeline fenced block as HTML.

    lang_line : full language tag, e.g.
                "timeline 2026 Iran war | https://en.wikipedia.org/wiki/..."
    lines     : entry lines, each "YYYY-MM-DD | title | note | url"
    Returns   : .tl-box HTML string ready to append to body_html.
    """
    # ── Parse header ──────────────────────────────────────────────────────
    header = lang_line[len("timeline"):].strip()
    parts = header.split(" | ", 1)
    article_name = parts[0].strip() if parts else "Timeline"
    wiki_url = parts[1].strip() if len(parts) > 1 else ""

    today_str = datetime.date.today().isoformat()  # "2026-03-24"

    # ── W icon SVG (matches tooltip link style) ───────────────────────────
    def w_svg(color: str) -> str:
        return (
            f'<svg width="13" height="13" viewBox="0 0 50 50" fill="none">'
            f'<circle cx="25" cy="25" r="23" stroke="{color}" stroke-width="2.5" fill="none"/>'
            f'<text x="8" y="34" font-family="Georgia,serif" font-size="27" '
            f'fill="{color}" font-weight="bold">W</text></svg>'
        )

    # ── Build rows ────────────────────────────────────────────────────────
    rows_html = []
    for raw in lines:
        if not raw.strip():
            continue
        fields = raw.split(" | ", 3)
        if len(fields) < 2:
            continue
        date_str  = fields[0].strip()
        title     = fields[1].strip()
        note      = fields[2].strip() if len(fields) > 2 else ""
        entry_url = fields[3].strip() if len(fields) > 3 else wiki_url

        is_today = date_str == today_str

        # Short display date: "Feb 13" or "Mar 24 ◀"
        # Note: use d.day (not %-d) — %-d is Linux-only, fails on macOS BSD strftime
        try:
            d = datetime.date.fromisoformat(date_str)
            short = f"{d.strftime('%b')} {d.day}"
            full  = f"{d.strftime('%B')} {d.day}, {d.year}"
        except ValueError:
            short = full = date_str

        if is_today:
            short += " ◀"
            full  += " · Today"

        row_class = "vtl-row today" if is_today else "vtl-row"
        rows_html.append(
            f'<div class="{row_class}"'
            f' data-tip-date="{html.escape(full)}"'
            f' data-tip-title="{html.escape(title)}"'
            f' data-tip-note="{html.escape(note)}"'
            f' data-tip-url="{html.escape(entry_url)}">'
            f'<div class="vtl-date">{html.escape(short)}</div>'
            f'<div class="vtl-dot"></div>'
            f'<div class="vtl-event">{html.escape(title)}</div>'
            f'</div>'
        )

    # ── Wikipedia header link ─────────────────────────────────────────────
    wiki_link = ""
    if wiki_url:
        wiki_link = (
            f'<a class="tl-wiki" href="{html.escape(wiki_url)}"'
            f' target="_blank" rel="noopener">'
            f'{w_svg("#8a7f6a")}'
            f'<span>{html.escape(article_name)}</span>'
            f'</a>'
        )

    rows = "\n".join(rows_html)
    return (
        f'<div class="tl-box">\n'
        f'<div class="tl-box-header">\n'
        f'<span class="tl-box-label">Timeline · {html.escape(article_name)}</span>\n'
        f'{wiki_link}\n'
        f'</div>\n'
        f'<div class="vtl">\n'
        f'{rows}\n'
        f'</div>\n'
        f'</div>'
    )
```

- [ ] **Step 5: Run tests again — all should pass**

```bash
cd /Users/bart/Desktop/claude/tools/wiki-scraper
python3 tests/test_timelines.py
```

Expected:
```
  ✓ test_header_article_name_and_wiki_link
  ✓ test_entry_renders_date_and_title
  ✓ test_today_entry_gets_today_class_and_marker
  ✓ test_non_today_entry_has_no_today_class
  ✓ test_data_tip_attributes_set
  ✓ test_empty_lines_skipped
  ✓ test_html_escaping

7 passed, 0 failed
```

- [ ] **Step 6: Commit**

```bash
git add view_export.py tests/test_timelines.py
git commit -m "feat: add render_timeline() function with datetime import"
```

---

## Task 2: Fenced block state machine in `render_analysis()`

**Files:**
- Modify: `view_export.py` — inside `render_analysis()`, add state machine to the `for line in lines:` loop (around line 643)

**Context:** The current rendering loop has no handling for triple-backtick fenced blocks. Lines starting with ` ``` ` fall through to the `else` branch and get buffered as paragraph text, which would render a `timeline` block as garbled paragraph output. We need a state machine that tracks when we're inside a fenced block and dispatches to `render_timeline()` when the block closes.

The state machine must be inserted **before** the existing line handlers in the loop (before the `if line.startswith("# "):` chain), so fenced blocks are intercepted before any other handler sees the backtick lines.

- [ ] **Step 1: Add state variables before the loop**

Find the comment `# ── Second pass: render body ──` (around line 622). Just after the variable declarations (`body_html = []`, `in_footnote_section = False`, etc.), add three new state variables:

```python
    # Fenced block state
    in_code_block = False
    code_lang = ""
    code_buf: list[str] = []
```

- [ ] **Step 2: Add fenced block handler at the top of the loop body**

Inside `for line in lines:`, immediately after the two existing early-exit checks (the footnote-def skip and the `in_footnote_section` skip), add:

```python
        # ── Fenced code / timeline block ─────────────────────────────────
        if line.startswith("```"):
            if not in_code_block:
                in_code_block = True
                code_lang = line[3:].strip()
                code_buf = []
            else:
                in_code_block = False
                if code_lang.startswith("timeline"):
                    flush_paragraph()
                    body_html.append(render_timeline(code_lang, code_buf))
                else:
                    flush_paragraph()
                    code_text = html.escape("\n".join(code_buf))
                    lang_class = f' class="language-{html.escape(code_lang)}"' if code_lang else ""
                    body_html.append(f'<pre><code{lang_class}>{code_text}</code></pre>')
                code_buf = []
                code_lang = ""
            continue

        if in_code_block:
            code_buf.append(line)
            continue
```

Place this block **before** `# Block-level image` comment (currently line ~656).

- [ ] **Step 3: Verify syntax**

```bash
cd /Users/bart/Desktop/claude/tools/wiki-scraper
python3 -c "import view_export"
```

Expected: no output, exit 0.

- [ ] **Step 4: Run tests — all still pass**

```bash
python3 tests/test_timelines.py
```

Expected: 7 passed, 0 failed.

- [ ] **Step 5: Commit**

```bash
git add view_export.py
git commit -m "feat: fenced block state machine in render_analysis() — dispatches timeline blocks"
```

---

## Task 3: Timeline and tooltip CSS

**Files:**
- Modify: `view_export.py` — CSS constant, just before the closing `"""`  (currently line 335)

**Context:** The CSS constant ends after `.toggle-btn:hover { ... }` at line 334, then `"""` at line 335. Append new rules before that closing quote. All class names match the HTML emitted by `render_timeline()` and the `#tl-tooltip` div added in Task 4.

- [ ] **Step 1: Append CSS rules to the CSS constant**

Find the exact end of the CSS constant:
```python
.toggle-btn:hover { background: #2e2820; color: #c98a2e; border-color: #c98a2e; }
"""
```

Change to:
```python
.toggle-btn:hover { background: #2e2820; color: #c98a2e; border-color: #c98a2e; }

/* ── Event timelines ──────────────────────────────────────────────────── */
.tl-box {
  border: 1px solid #3a342e;
  border-radius: 4px;
  background: #211e1a;
  padding: 12px;
  margin-top: 12px;
}
.tl-box-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.tl-box-label {
  color: #8a7f6a;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}
.tl-wiki {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  text-decoration: none;
}
.tl-wiki span { font-size: 10px; color: #6eadd4; }
.tl-wiki:hover span { text-decoration: underline; }

.vtl { position: relative; padding-left: 76px; }
.vtl::before {
  content: '';
  position: absolute;
  left: 65px; top: 6px; bottom: 6px;
  width: 1px;
  background: #3a342e;
}
.vtl-row {
  position: relative;
  margin-bottom: 10px;
  padding-left: 14px;
  cursor: default;
}
.vtl-row:last-child { margin-bottom: 0; }
.vtl-date {
  position: absolute;
  left: -76px;
  width: 62px;
  text-align: right;
  font-size: 10px;
  color: #8a7f6a;
  line-height: 1.6;
  padding-top: 1px;
}
.vtl-dot {
  position: absolute;
  left: -5px; top: 5px;
  width: 9px; height: 9px;
  border-radius: 50%;
  background: #3a342e;
  border: 1px solid #4a4438;
  transition: background 0.12s, border-color 0.12s;
}
.vtl-row[data-tip-title]:hover .vtl-dot { background: #6eadd4; border-color: #6eadd4; }
.vtl-event {
  font-size: 11px;
  color: #c8bfa8;
  line-height: 1.6;
  transition: color 0.12s;
}
.vtl-row[data-tip-title]:hover .vtl-event { color: #e8dfc8; }
.vtl-row.today .vtl-date { color: #c98a2e; font-weight: 600; }
.vtl-row.today .vtl-dot {
  background: #c98a2e; border-color: #c98a2e;
  width: 11px; height: 11px;
  left: -6px; top: 4px;
}
.vtl-row.today .vtl-event { color: #e8dfc8; font-weight: 600; }
.vtl-row.today[data-tip-title]:hover .vtl-dot { background: #e09030; border-color: #e09030; }

/* ── Timeline hover tooltip ───────────────────────────────────────────── */
#tl-tooltip {
  display: none;
  position: absolute;
  z-index: 9999;
  width: 280px;
  background: #1e1a10;
  border: 1px solid #c98a2e;
  border-radius: 5px;
  padding: 12px 14px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.65);
  pointer-events: auto;
  font-size: 13px;
  line-height: 1.5;
}
/* Invisible bridge fills gap between tooltip bottom and row so mouse
   can travel to the tooltip without triggering the hide timer. */
#tl-tooltip::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 0; right: 0;
  height: 14px;
}
.tip-date  { font-size: 10px; color: #8a7f6a; letter-spacing: 0.06em; margin-bottom: 4px; }
.tip-title { font-size: 12px; color: #e8dfc8; font-weight: 600; line-height: 1.4; margin-bottom: 6px; }
.tip-note  { font-size: 11px; color: #b8b0a0; line-height: 1.5; margin-bottom: 10px; }
.tip-link  {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 10px;
  color: #6eadd4;
  text-decoration: none;
  border: 1px solid #3a342e;
  border-radius: 3px;
  padding: 4px 10px;
  background: #2a2520;
  transition: border-color 0.12s, color 0.12s;
}
.tip-link:hover { border-color: #6eadd4; color: #8ac8e8; }
"""
```

- [ ] **Step 2: Verify syntax**

```bash
python3 -c "import view_export"
```

Expected: exit 0.

- [ ] **Step 3: Commit**

```bash
git add view_export.py
git commit -m "feat: add timeline and tooltip CSS"
```

---

## Task 4: `#tl-tooltip` div and JS

**Files:**
- Modify: `view_export.py` — page template (line ~785) and `build_js()` return string

**Context:** The page template has `<div id="fn-tooltip"></div>` at line 785. Add the `#tl-tooltip` div immediately after it. The `build_js()` function returns a `<script>` block — add the timeline tooltip JS just before the closing `</script>` tag (after the existing `toggleAllSections` function).

- [ ] **Step 1: Add `#tl-tooltip` div to page template**

Find in `render_analysis()`:
```python
<div id="fn-tooltip"></div>
```

Change to:
```python
<div id="fn-tooltip"></div>
<div id="tl-tooltip">
  <div class="tip-date" id="tip-date"></div>
  <div class="tip-title" id="tip-title"></div>
  <div class="tip-note" id="tip-note"></div>
  <a class="tip-link" id="tip-link" href="#" target="_blank" rel="noopener">
    <svg width="11" height="11" viewBox="0 0 50 50" fill="none"><circle cx="25" cy="25" r="23" stroke="#6eadd4" stroke-width="2.5" fill="none"/><text x="8" y="34" font-family="Georgia,serif" font-size="27" fill="#6eadd4" font-weight="bold">W</text></svg>
    Read on Wikipedia
  </a>
</div>
```

- [ ] **Step 2: Add timeline tooltip JS to `build_js()`**

Find the closing lines of `build_js()`'s return string:
```python
  btn.textContent = anyOpen ? 'Expand all' : 'Collapse all';
}}
</script>
"""
```

Change to:
```python
  btn.textContent = anyOpen ? 'Expand all' : 'Collapse all';
}}

// ── Timeline hover tooltips ──────────────────────────────────────────────
const _tlTip = document.getElementById('tl-tooltip');
let _tlTimeout;

function _showTlTip(row) {{
  clearTimeout(_tlTimeout);
  document.getElementById('tip-date').textContent  = row.dataset.tipDate  || '';
  document.getElementById('tip-title').textContent = row.dataset.tipTitle || '';
  document.getElementById('tip-note').textContent  = row.dataset.tipNote  || '';
  document.getElementById('tip-link').href = row.dataset.tipUrl || '#';
  _tlTip.style.display = 'block';

  const r    = row.getBoundingClientRect();
  const tipH = _tlTip.offsetHeight;
  const tipW = 280;
  let top  = r.top + window.scrollY - tipH - 4;
  let left = r.left + window.scrollX;

  // Clamp horizontally so tooltip never clips off screen
  if (left + tipW > window.innerWidth - 12) left = window.innerWidth - tipW - 12;
  left = Math.max(8, left);

  // If tooltip would go above viewport, show below the row instead
  if (top < window.scrollY + 8) top = r.bottom + window.scrollY + 4;

  _tlTip.style.top  = top + 'px';
  _tlTip.style.left = left + 'px';
}}

function _hideTlTip(delay) {{
  _tlTimeout = setTimeout(() => {{ _tlTip.style.display = 'none'; }}, delay);
}}

document.querySelectorAll('.vtl-row[data-tip-title]').forEach(row => {{
  row.addEventListener('mouseenter', () => _showTlTip(row));
  row.addEventListener('mouseleave', () => _hideTlTip(300));
}});
_tlTip.addEventListener('mouseenter', () => clearTimeout(_tlTimeout));
_tlTip.addEventListener('mouseleave', () => _hideTlTip(120));
</script>
"""
```

Note: JS uses `{{` and `}}` because this is inside a Python f-string.

- [ ] **Step 3: Verify syntax**

```bash
python3 -c "import view_export"
```

Expected: exit 0.

- [ ] **Step 4: Run tests — all still pass**

```bash
python3 tests/test_timelines.py
```

Expected: 7 passed, 0 failed.

- [ ] **Step 5: Commit**

```bash
git add view_export.py
git commit -m "feat: add tl-tooltip div and JS — timeline hover tooltips wired up"
```

---

## Task 5: Update CLAUDE.md with timeline format

**Files:**
- Modify: `CLAUDE.md` — Analysis Format section

**Context:** CLAUDE.md already has sections for document header, section format, and callout syntax. Add the timeline block format after the callout syntax section and before "Standard sections to include". This tells Claude when and how to write timeline entries.

- [ ] **Step 1: Add timeline format block to CLAUDE.md**

Find the callout box syntax section:
```markdown
### Callout box syntax (three types)

```
> **KEY:** [insight] — amber box, use for things the reader should not miss
> **WATCH:** [observation] — rust red box, use for undercovered significance
> **ABSURD:** [humor] — sage green box, use once per analysis for the humor beat
```

Only use `KEY` or `WATCH` once or twice per section maximum. They lose meaning if overused.
```

Add the following immediately after (before `### Footnotes`):

````markdown
### Timeline blocks (optional, for major ongoing stories)

For sections covering large, multi-week ongoing events (wars, major political proceedings, economic crises), include a timeline block after the KEY/WATCH callout. Use the fenced `timeline` format:

```timeline [Wikipedia article name] | [Wikipedia article URL]
YYYY-MM-DD | Short event title | 1–3 sentence context note for the hover tooltip | Wikipedia URL for this event
YYYY-MM-DD | Short event title | 1–3 sentence context note | Wikipedia URL
```

**Example:**
```timeline 2026 Iran war | https://en.wikipedia.org/wiki/2026_Israel%E2%80%93Iran_war
2026-02-13 | US–Israel air campaign begins | After Iran's missile barrage strikes Haifa's port district, US and Israeli air forces launch coordinated strikes on IRGC infrastructure across western Iran. | https://en.wikipedia.org/wiki/2026_Israel%E2%80%93Iran_war
2026-02-19 | Iran threatens Hormuz closure | IRGC naval command announces it will mine the strait if strikes continue. Oil surges to $112/barrel. US Fifth Fleet repositions two carrier groups. | https://en.wikipedia.org/wiki/Strait_of_Hormuz
2026-03-24 | Trump declares victory; Israel says weeks remain | Trump posts "MISSION ACCOMPLISHED" as IDF says Iran's reconstitution capability requires 3–4 more weeks. ISW notes diverging timelines. | https://en.wikipedia.org/wiki/2026_Israel%E2%80%93Iran_war
```

**Rules:**
- Carry forward ALL previous entries each run — the timeline accumulates. Append new entries for today; do not remove old ones.
- Entries must be in chronological order, oldest first.
- Dates must be ISO format `YYYY-MM-DD` — the renderer uses them to mark "today" automatically.
- Every entry needs a Wikipedia URL. Use the main article URL if no specific sub-article exists.
- The entry URL (field 4) links from the hover tooltip — choose the most relevant Wikipedia page for that specific event.
- Use the main article URL in the header (field after the language tag) — this links from the timeline box header.
- Only include timelines for sections about major, multi-week ongoing stories. Do NOT include in: Science & Discovery, Dispatch from the Absurd, Other Consequential Events, or one-off single-day events.
````

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add timeline block format to CLAUDE.md analysis instructions"
```

---

## Task 6: Visual verification

**Files:**
- Modify: `analysis_2026-03-24.md` — add sample timeline block to the Iran War section (temporary, for verification only — will be properly included in next analysis run)

**Context:** Verify the full render pipeline end-to-end by adding a real timeline block to an existing analysis file and rendering it.

- [ ] **Step 1: Add a timeline block to `analysis_2026-03-24.md`**

Find the Iran War section. After its `> **KEY:**` callout and before the `---` separator, add:

````markdown
```timeline 2026 Iran war | https://en.wikipedia.org/wiki/2026_Israel%E2%80%93Iran_war
2026-02-13 | US–Israel air campaign begins | After Iran's missile barrage strikes Haifa's port district, US and Israeli air forces launch coordinated strikes on IRGC infrastructure across western Iran. | https://en.wikipedia.org/wiki/2026_Israel%E2%80%93Iran_war
2026-02-19 | Iran threatens Hormuz closure | IRGC naval command announces it will mine the strait if strikes continue. Oil surges to $112/barrel. US Fifth Fleet repositions two carrier groups. | https://en.wikipedia.org/wiki/Strait_of_Hormuz
2026-03-04 | Bushehr nuclear plant hit | Israeli strikes disable the reactor's cooling systems. IAEA calls an emergency session. Iranian state media reports elevated radiation in Bushehr province. | https://en.wikipedia.org/wiki/Bushehr_Nuclear_Power_Plant
2026-03-24 | Trump declares victory; Israel says weeks remain | Trump posts "MISSION ACCOMPLISHED" as IDF says Iran's reconstitution capability requires 3–4 more weeks. ISW notes diverging political and military timelines. | https://en.wikipedia.org/wiki/2026_Israel%E2%80%93Iran_war
```
````

- [ ] **Step 2: Render and open in browser**

```bash
cd /Users/bart/Desktop/claude/tools/wiki-scraper
python3 view_export.py analysis_2026-03-24.md
```

Expected:
1. Browser opens
2. Iran War section shows a `Timeline · 2026 Iran war` box with a `Ⓦ` link on the right
3. Four event rows visible (Feb 13, Feb 19, Mar 4, Mar 24 ◀)
4. Mar 24 row has gold dot and gold date
5. Hovering any row shows a floating tooltip above it (within 300ms)
6. Tooltip shows: full date, title, note, "Read on Wikipedia" link
7. Mouse can move into tooltip to click the link without it dismissing
8. No layout shift — existing section content is unchanged

- [ ] **Step 3: Commit**

```bash
git add view_export.py tests/test_timelines.py CLAUDE.md analysis_2026-03-24.md
git commit -m "feat: event timelines complete — vertical timeline with hover tooltips and Wikipedia links"
```
