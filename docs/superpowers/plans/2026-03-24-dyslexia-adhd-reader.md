# Dyslexia/ADHD-Friendly Reader Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the analysis HTML output easier to read for a user with dyslexia and ADHD-PI by adding Lexend font with improved spacing, and collapsible sections with always-visible subtitles.

**Architecture:** Two targeted changes to `view_export.py` only: (1) CSS typography update — Lexend font, letter-spacing, word-spacing; (2) post-processing pass over `body_html` that wraps each `<h2>` + subtitle into a `<details><summary>` block, plus a "Collapse all / Expand all" JS button. No changes to analysis format or other files.

**Tech Stack:** Python (stdlib), HTML/CSS/JS — no new dependencies.

---

## Visual Mockup

The mockup below shows the two changes side-by-side. Open **http://localhost:8767** to see it rendered, or read the inline preview below.

> **Before / After — Typography + Collapsible Sections**

### Before (current output)

```
┌─────────────────────────────────────────────────────────┐
│  Current Events Analysis — 2026-03-24                   │
│                                                         │
│  ## Iran War Enters New Phase                           │  ← always visible,
│  *US forces respond to Iranian escalation in Iraq*      │    no way to collapse
│                                                         │
│  [full paragraph text — dense, no way to skip]          │
│  [full paragraph text — dense, no way to skip]          │
│  [full paragraph text — dense, no way to skip]          │
│                                                         │
│  ## Pakistan–Afghanistan Conflict                       │
│  *Nuclear-armed Pakistan conducts airstrikes*           │
│                                                         │
│  [full paragraph text — dense, no way to skip]          │
│  [full paragraph text — dense, no way to skip]          │
└─────────────────────────────────────────────────────────┘
Font: system-ui   letter-spacing: 0.01em   word-spacing: default
```

### After (this plan implements)

```
┌─────────────────────────────────────────────────────────┐
│  Current Events Analysis — 2026-03-24                   │
│  [ Collapse all ]                                       │  ← new toggle button
│                                                         │
│  ▾ Iran War Enters New Phase                            │  ← clickable summary
│    US forces respond to Iranian escalation in Iraq      │  ← subtitle always visible
│    ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄    │
│    [paragraph — visible when section is open]           │
│    [paragraph — visible when section is open]           │
│                                                         │
│  ▸ Pakistan–Afghanistan Conflict                        │  ← collapsed: only
│    Nuclear-armed Pakistan conducts airstrikes           │    header + subtitle
│                                                         │  ← body hidden
│  ▾ Science & Discovery                                  │
│    A record gamma-ray burst reshapes models of...       │
│    ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄    │
│    [paragraph — visible]                                │
└─────────────────────────────────────────────────────────┘
Font: Lexend   letter-spacing: 0.12em   word-spacing: 0.16em
```

**"Collapse all" state** — rapid scan mode:

```
┌─────────────────────────────────────────────────────────┐
│  Current Events Analysis — 2026-03-24                   │
│  [ Expand all ]                                         │
│                                                         │
│  ▸ Iran War Enters New Phase                            │
│    US forces respond to Iranian escalation in Iraq      │
│                                                         │
│  ▸ Pakistan–Afghanistan Conflict                        │
│    Nuclear-armed Pakistan conducts airstrikes           │
│                                                         │
│  ▸ Science & Discovery                                  │
│    A record gamma-ray burst reshapes models of...       │
│                                                         │
│  ▸ Dispatch from the Absurd                             │
│    The Center 795 situation reads as dark comedy        │
└─────────────────────────────────────────────────────────┘
All sections collapsed — headlines + subtitles only visible.
Click any ▸ header to expand just that section.
```

---

## File Map

| File | Change |
|------|--------|
| `view_export.py` | Modify CSS block (lines 40–170 approx), add `wrap_sections()` post-processing function, update `render_analysis()` to call it, extend `build_js()` with toggle button JS |

**Not modified:** `wiki_scraper.py`, `news_scraper.py`, `run_daily.py`, `CLAUDE.md`, analysis `.md` files.

---

## Task 1: Typography — Lexend font and spacing

**Files:**
- Modify: `view_export.py` — CSS constant (lines 40–58)

**Context:** The CSS constant starts at line 40. The `body` rule is at lines 54–58. We need to add a Google Fonts import at the top of the CSS string and update three properties on the `body` rule. The sidebar has its own `letter-spacing` override on `#sidebar h2` — leave that untouched.

- [ ] **Step 1: Add Lexend import and update body CSS**

In `view_export.py`, find the `CSS = """` block. Make two changes:

**Change 1** — Add the Google Fonts import as the very first line inside the CSS string (before `* { box-sizing...`):
```css
@import url('https://fonts.googleapis.com/css2?family=Lexend:wght@300;400;500;600&display=swap');
```

**Change 2** — Update the `body` rule from:
```css
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: #1a1714; color: #e8dfc8; font-size: 19px; line-height: 2.0;
  letter-spacing: 0.01em;
}
```
To:
```css
body {
  font-family: Lexend, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: #1a1714; color: #e8dfc8; font-size: 19px; line-height: 2.0;
  letter-spacing: 0.12em;
  word-spacing: 0.16em;
}
```

- [ ] **Step 2: Verify visually**

Run:
```bash
cd /Users/bart/Desktop/claude/tools/wiki-scraper
python3 view_export.py analysis_2026-03-24.md
```

Expected: browser opens, body text uses Lexend (visibly wider letter spacing, more readable). The sidebar and callout labels should be unaffected.

- [ ] **Step 3: Commit**

```bash
git add view_export.py
git commit -m "feat: Lexend font, increased letter/word spacing for dyslexia readability"
```

---

## Task 2: Progressive disclosure — collapsible sections

**Files:**
- Modify: `view_export.py` — add CSS rules, add `wrap_sections()` function, update `render_analysis()`, extend `build_js()`

**Context:** After the main rendering loop (line 608), `body_html` is a list of HTML strings. Each section starts with an `<h2 id="...">` followed by either a `<p class="subtitle">` or nothing. The footnotes block is appended after this list (lines 610–622) and must NOT be wrapped.

The strategy:
1. Add `wrap_sections()` — a post-processing function that scans `body_html`, finds `<h2>` elements, pairs them with their subtitle (if present), and wraps both + the following content in `<details open><summary>...</summary><div class="section-body">...</div></details>`
2. Call `wrap_sections(body_html)` at line 608, before the footnotes block is appended
3. Add CSS for `<details>/<summary>` styling and the toggle button
4. Add the toggle button HTML into the masthead
5. Add the toggle JS into `build_js()`

- [ ] **Step 1: Add CSS for details/summary and toggle button**

Find the end of the CSS constant (just before the closing `"""`). Add these rules:

```css
/* ── Collapsible sections ─────────────────────────────────────────────── */
details { margin-bottom: 0; }
details + hr { margin-top: 0; }

summary {
  list-style: none;
  cursor: pointer;
  padding: 0.3rem 0;
  user-select: none;
}
summary::-webkit-details-marker { display: none; }

summary h2 {
  display: inline;
  margin-top: 0;
}

summary .subtitle {
  display: block;
  color: #8a7f6a;
  font-size: 0.88em;
  font-style: italic;
  margin-top: 0.2rem;
  margin-bottom: 0;
  letter-spacing: 0.06em;
}

summary::after {
  content: ' ▾';
  color: #8a7f6a;
  font-size: 0.75em;
  vertical-align: middle;
}
details:not([open]) summary::after { content: ' ▸'; }

.section-body { padding-top: 0.6rem; }

/* ── Collapse/expand toggle button ───────────────────────────────────── */
.toggle-btn {
  display: inline-block;
  margin: 0.8rem 0 1.6rem;
  padding: 0.35rem 0.9rem;
  background: #242019;
  border: 1px solid #3a342e;
  border-radius: 4px;
  color: #8a7f6a;
  font-size: 0.8rem;
  font-family: inherit;
  letter-spacing: 0.08em;
  cursor: pointer;
}
.toggle-btn:hover { background: #2e2820; color: #c98a2e; border-color: #c98a2e; }
```

- [ ] **Step 2: Add `wrap_sections()` function**

Add this function to `view_export.py` just before the `render_analysis` function (around line 475):

```python
def wrap_sections(body_html: list[str]) -> list[str]:
    """
    Post-processing pass: wrap each <h2> section in <details><summary>.
    The <h2> and its optional <p class="subtitle"> go inside <summary>.
    Everything up to the next <h2>, <hr>, or end-of-list goes in <div class="section-body">.
    The footnotes block (starts with <div class="footnotes">) is left untouched.
    """
    result = []
    i = 0
    while i < len(body_html):
        item = body_html[i]

        # Don't wrap footnotes block
        if item.startswith('<div class="footnotes"'):
            result.append(item)
            i += 1
            continue

        # Section heading — start a <details> block
        if item.startswith('<h2 '):
            summary_parts = [item]
            i += 1

            # Optional subtitle immediately following
            if i < len(body_html) and '<p class="subtitle">' in body_html[i]:
                summary_parts.append(body_html[i])
                i += 1

            # Collect body until next h2, hr, or footnotes
            body_parts = []
            while i < len(body_html):
                next_item = body_html[i]
                if (next_item.startswith('<h2 ')
                        or next_item.startswith('<div class="footnotes"')):
                    break
                body_parts.append(next_item)
                i += 1

            # Strip trailing <hr> from body (it belongs between sections, not inside)
            while body_parts and body_parts[-1] == '<hr>':
                body_parts.pop()
                result_hr = True
            else:
                result_hr = False

            summary_html = '\n'.join(summary_parts)
            body_html_str = '\n'.join(body_parts)
            result.append(
                f'<details open>\n'
                f'<summary>\n{summary_html}\n</summary>\n'
                f'<div class="section-body">\n{body_html_str}\n</div>\n'
                f'</details>'
            )
            if result_hr:
                result.append('<hr>')
            continue

        result.append(item)
        i += 1

    return result
```

- [ ] **Step 3: Call `wrap_sections()` in `render_analysis()`**

Find line 608 in `render_analysis()`:
```python
    body_html = [x for x in body_html if x != "__SUBTITLE_SLOT__"]
```

Add the `wrap_sections` call immediately after:
```python
    body_html = [x for x in body_html if x != "__SUBTITLE_SLOT__"]
    body_html = wrap_sections(body_html)
```

- [ ] **Step 4: Add toggle button to masthead**

Find the `masthead` assembly in `render_analysis()` (around line 631):
```python
    masthead = f"""<div class="masthead">
  <h1>{html.escape(page_title)}</h1>
  {'<p class="meta">' + html.escape(meta_line) + '</p>' if meta_line else ''}
</div>"""
```

Change to:
```python
    masthead = f"""<div class="masthead">
  <h1>{html.escape(page_title)}</h1>
  {'<p class="meta">' + html.escape(meta_line) + '</p>' if meta_line else ''}
  <button class="toggle-btn" id="toggle-all-btn" onclick="toggleAllSections()">Collapse all</button>
</div>"""
```

- [ ] **Step 5: Add toggle JS to `build_js()`**

Find the closing `</script>` tag in `build_js()` (near the end of the function's return string). Add this JS block just before it:

```javascript
// ── Collapse / expand all sections ──────────────────────────────────────
function toggleAllSections() {
  const details = document.querySelectorAll('details');
  const btn = document.getElementById('toggle-all-btn');
  const anyOpen = Array.from(details).some(d => d.open);
  details.forEach(d => { d.open = !anyOpen; });
  btn.textContent = anyOpen ? 'Expand all' : 'Collapse all';
}
```

- [ ] **Step 6: Verify visually**

Run:
```bash
cd /Users/bart/Desktop/claude/tools/wiki-scraper
python3 view_export.py analysis_2026-03-24.md
```

Verify:
1. All sections are expanded by default, each showing header + italic subtitle
2. Clicking a section header collapses/expands that section
3. "Collapse all" button collapses everything to just headers + subtitles
4. "Expand all" button restores all sections
5. The Sources / footnotes section at the bottom is NOT wrapped in a `<details>` block
6. The `▾` / `▸` indicator updates correctly

- [ ] **Step 7: Run the pipeline to update docs/index.html**

```bash
python3 run_daily.py
```

This regenerates `docs/index.html` with the new rendering and pushes it to GitHub Pages.

- [ ] **Step 8: Commit**

```bash
git add view_export.py
git commit -m "feat: collapsible sections with always-visible subtitles for ADHD scanning"
git push
```
