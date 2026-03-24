# Design Spec: Automated Daily Brief
**Date:** 2026-03-24
**Status:** Approved

---

## Problem

The wiki-scraper workflow requires three manual terminal commands to collect data, then a manual Claude session to produce the analysis, then a manual command to view it in the browser. The goal is a briefing page at a fixed public URL that updates automatically each morning before Nick wakes up.

---

## Solution Summary

A Python orchestrator (`run_daily.py`) runs the full pipeline — scrapers, Claude analysis, HTML generation, git push — triggered at 6am daily by macOS launchd. The output is a single `docs/index.html` served by GitHub Pages at a bookmarkable URL. The script can also be run manually at any time for an on-demand update.

---

## Architecture

### Components

| File | Purpose |
|------|---------|
| `run_daily.py` | Orchestrator — runs pipeline, logs each step |
| `install_launchd.sh` | One-time setup — installs launchd job at 6am |
| `docs/index.html` | GitHub Pages output — overwritten on each run |
| `~/Library/LaunchAgents/com.nick.morning-brief.plist` | macOS scheduler config (outside repo) |

### Pipeline sequence

```
launchd (6am) → run_daily.py
  1. wiki_scraper.py               (current events)
  2. wiki_scraper.py [science URL]  (2026 in science)
  3. news_scraper.py               (all news sources)
  4. claude -p "analyze the latest wiki and news exports"
  5. view_export.py --no-open      (render .md → HTML)
  6. copy output → docs/index.html
  7. git add docs/index.html → commit → push
```

All subprocess calls use `cwd=REPO_DIR` (the wiki-scraper directory), so that CLAUDE.md instructions are in scope and scrapers write their files to the right place.

### Manual invocation

```bash
python3 run_daily.py
```

Identical to the scheduled run. No arguments needed.

---

## Implementation Notes

### Finding the Claude-written analysis file (step 4 → 5)

`claude -p` runs the prompt non-interactively and prints Claude's response to stdout. Claude saves `analysis_YYYY-MM-DD.md` to the project directory per CLAUDE.md conventions, but does not signal the filename over stdout. After the `claude -p` call completes, the orchestrator globs for the newest `analysis_*.md` in `REPO_DIR` to identify the file. A timeout of 5 minutes is applied to the Claude subprocess — if it hangs, the pipeline logs an error and exits.

### Finding the HTML output file (step 5 → 6)

`view_export.py` writes its output to `{analysis_stem}.html` in the same directory as the `.md` file (e.g., `analysis_2026-03-25.md` → `analysis_2026-03-25.html`). The orchestrator derives the expected HTML path from the analysis filename, confirms it exists, then copies it to `docs/index.html`. After the copy, the per-date `.html` file is deleted to prevent accumulation.

### launchd environment

launchd agents run in a stripped environment (`PATH=/usr/bin:/bin:/usr/sbin:/sbin`). `install_launchd.sh` must write the full `PATH` — including the location of the `claude` CLI and any homebrew/pyenv paths — into the `EnvironmentVariables` key of the plist. The script detects these at install time using `which claude` and `which python3`.

The repo uses a `.venv`. All scraper subprocess calls in `run_daily.py` use the venv's Python explicitly (`REPO_DIR/.venv/bin/python3`), not the system Python. `install_launchd.sh` verifies the venv exists before installing.

---

## Logging

Log file: `morning_brief.log` (append mode)

Each run appends a timestamped block:

```
=== 2026-03-25 06:00:01 ===
[06:00:01] START
[06:00:04] scraper: current events — OK
[06:00:12] scraper: science — OK
[06:00:31] scraper: news — OK (1 source failed: telegram_nexta)
[06:01:14] claude: analysis written → analysis_2026-03-25.md
[06:01:16] html: docs/index.html written
[06:01:19] git: pushed to origin/main
[06:01:19] DONE — 78s
```

**Log rotation:** After each run, `morning_brief.log` is trimmed to its last 500 lines by reading the file into memory and rewriting only the tail. This keeps approximately 7 days of run history.

---

## Error Handling

| Failure | Behavior |
|---------|---------|
| A scraper fails | Log warning, continue — partial data is better than nothing |
| Claude invocation fails or times out | Log error, stop — no analysis to push |
| Claude produces no `analysis_*.md` | Log error, stop |
| `view_export.py` fails | Log error, stop — don't push a broken page |
| git push fails | Log error + fire macOS notification via `osascript` — analysis exists locally but user should know |

The macOS notification on git push failure ensures the silent failure mode (days of analyses existing only locally) is surfaced promptly.

---

## .gitignore Changes Required

**These changes must be committed to the repo before the first automated run.** They are part of the GitHub Pages Setup steps below — do that first, then run `install_launchd.sh`.

The current `.gitignore` contains `index.html` (unanchored), which matches `docs/index.html` and would cause the git push step to silently add nothing. This must be changed to `/index.html` (anchored to repo root).

Additionally, `analysis_*.html` must be added to `.gitignore` to prevent per-date HTML files from accumulating in the repo.

`install_launchd.sh` verifies that both changes are present in `.gitignore` before completing setup, and exits with an error if they are not — it does not make or commit these changes itself.

---

## GitHub Pages Setup (one-time, manual)

1. Create `docs/index.html` with a placeholder page
2. Update `.gitignore`: change `index.html` → `/index.html`, add `analysis_*.html`
3. Commit and push
4. In GitHub repo Settings → Pages → Source: Deploy from branch → Branch: `main` → Folder: `/docs`
5. URL: `https://nborders.github.io/news-intelligence/`

---

## launchd Setup (one-time, via script)

```bash
bash install_launchd.sh
```

The script:
- Confirms `.venv` exists in the repo directory
- Detects paths for `claude` CLI and venv Python
- Verifies `.gitignore` has the correct entries (`/index.html`, `analysis_*.html`) — exits with a clear error if not, directing the user to complete the GitHub Pages Setup steps first
- Writes `~/Library/LaunchAgents/com.nick.morning-brief.plist` with correct paths and environment
- Registers with `launchctl load`

The `.plist` is not committed to the repo (it contains absolute paths specific to this machine).

---

## Repo Structure After Implementation

```
wiki-scraper/
  run_daily.py              ← NEW
  install_launchd.sh        ← NEW
  docs/
    index.html              ← NEW (overwritten daily, committed)
    superpowers/specs/      ← design docs
  wiki_scraper.py
  news_scraper.py
  view_export.py
  CLAUDE.md
  .gitignore                (updated: /index.html, analysis_*.html)
```

---

## Out of Scope (future)

- **Update button in the HTML page** — requires a local HTTP server to bridge browser → filesystem. Deferred.
- **Archive of past analyses** — not needed; single page only.
- **Cloud-only pipeline** — Telegram and APOD sources work better from a persistent local session.
