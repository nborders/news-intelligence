# Design Spec: Dyslexia/ADHD-Friendly Reader
**Date:** 2026-03-24
**Status:** Approved

---

## Problem

The current HTML output of `view_export.py` is not optimized for a reader with dyslexia and ADHD-PI. The typography uses default spacing and font, and all section content is always fully visible — requiring the reader to parse full paragraphs before knowing whether a section is worth their attention.

---

## Solution Summary

Two targeted changes to `view_export.py`:

1. **Typography improvements** — Lexend font, increased letter spacing, increased word spacing. Evidence-backed for dyslexia. One CSS block change.

2. **Progressive disclosure** — Section bodies become collapsible. The header and subtitle (already present in the analysis format) remain always visible, giving the reader a triage line before committing to the full section. A "collapse all / expand all" toggle at the top enables rapid scanning mode.

---

## What Changes

### File
`view_export.py` only. No changes to `CLAUDE.md`, analysis format, scraper scripts, or `run_daily.py`.

### CSS changes

Add Google Fonts import for Lexend at the top of the CSS block:
```css
@import url('https://fonts.googleapis.com/css2?family=Lexend:wght@300;400;500;600&display=swap');
```

Update body font and spacing:
```css
font-family: Lexend, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
letter-spacing: 0.12em;
word-spacing: 0.16em;
```

All other CSS stays the same — the dark/warm palette (#1a1714 background, #e8dfc8 text) is already appropriate for dyslexia.

### Section rendering changes

Each `##` section gets wrapped in a `<details>` / `<summary>` structure:

```html
<details open>
  <summary>
    <h2>Section Title</h2>
    <p class="subtitle">One-sentence subtitle</p>
  </summary>
  <div class="section-body">
    <!-- paragraphs, callouts, etc. -->
  </div>
</details>
```

- Default state: `open` (all sections expanded on load)
- The subtitle (`*italic line*` immediately after `##` heading in the .md) is extracted and placed inside `<summary>` so it's always visible
- The `<details>` / `<summary>` HTML elements handle collapse/expand natively with no JavaScript required for basic behavior

**Implementation note — post-processing approach required:**
The existing renderer uses a `__SUBTITLE_SLOT__` sentinel in `body_html` to detect subtitles (line ~600 in `view_export.py`). Wrapping the `<h2>` output in `<details>/<summary>` at emit time would break this sentinel detection. The correct approach is a **post-processing pass** over the assembled `body_html` list after the main rendering loop completes: find each `<h2>` element, look ahead for a `<p class="subtitle">` that follows, and wrap both inside `<details><summary>`, with the remaining section content in `<div class="section-body">`. This preserves the existing subtitle detection logic unchanged.

**Important:** The footnotes block is assembled separately after the main `body_html` loop and appended last. Do not apply `<details>` wrapping to it.

### Collapse all / Expand all button

A single button near the top of the page (below the document title) toggles all sections:

- **"Collapse all"** — closes all `<details>` elements, leaving only headers + subtitles visible for rapid scanning
- **"Expand all"** — restores all sections to open
- Button label updates to reflect current state
- Requires ~10 lines of JavaScript

---

## What Doesn't Change

- Analysis `.md` format and CLAUDE.md instructions
- The subtitle format (`*one sentence*` under `##` headings) — already specified and already present in analyses
- Callout boxes (KEY / WATCH / ABSURD) — stay inside section body, collapse with it
- Footnotes and Sources section — Sources section not collapsible (it's reference material, not reading material)
- Dark/warm color palette
- Sidebar navigation
- Overall page structure

---

## Constraints

- `view_export.py` has no external dependencies beyond stdlib — the Lexend font loads from Google Fonts (requires internet connection when viewing). Acceptable for this use case.
- `<details>` / `<summary>` is supported in all modern browsers.
- The subtitle extraction relies on the `*italic line*` being the first non-blank line after the `##` heading. This is consistent with the current analysis format and CLAUDE.md spec.

---

## Out of Scope

- User-adjustable font size / spacing controls (future)
- Color scheme switcher (future)
- Mobile-specific layout changes (future)
- Changes to the analysis content format
