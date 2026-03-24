# Automated Daily Brief Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the full news scraper → Claude analysis → GitHub Pages pipeline automatically at 6am daily, with a bookmarkable public URL always showing today's analysis.

**Architecture:** A Python orchestrator (`run_daily.py`) runs each step in sequence with per-step logging and appropriate error handling (scrapers soft-fail, Claude/HTML/push hard-fail with notification). A launchd plist fires it at 6am. GitHub Pages serves `docs/index.html` from the main branch.

**Tech Stack:** Python 3 (stdlib only in orchestrator), bash, macOS launchd, GitHub Pages

---

## File Map

| File | Status | Responsibility |
|------|--------|----------------|
| `.gitignore` | Modify | Fix unanchored `index.html` → `/index.html`; add `analysis_*.html` |
| `docs/index.html` | Create | Placeholder page; overwritten by each pipeline run |
| `run_daily.py` | Create | Full pipeline orchestrator with logging and error handling |
| `install_launchd.sh` | Create | One-time setup: writes and registers the launchd plist |

**Not modified:** `wiki_scraper.py`, `news_scraper.py`, `view_export.py`, `CLAUDE.md`

---

## Task 1: Fix .gitignore and create docs/index.html placeholder

**Files:**
- Modify: `.gitignore`
- Create: `docs/index.html`

**Context:** The current `.gitignore` has `index.html` (unanchored), which matches `docs/index.html` and would silently prevent it from being committed. Must be fixed and committed before the pipeline can push the page. GitHub Pages must be enabled manually in the repo settings after this task.

- [ ] **Step 1: Fix .gitignore**

Open `.gitignore`. Change the `index.html` line to `/index.html` and add `analysis_*.html`:

```
# Before:
index.html

# After:
/index.html
analysis_*.html
```

- [ ] **Step 2: Create docs/index.html placeholder**

Create `docs/index.html` with this content exactly:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Morning Brief</title>
  <style>
    body { background: #1a1714; color: #e8dfc8; font-family: -apple-system, sans-serif;
           display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
    p { font-size: 1.2rem; opacity: 0.6; }
  </style>
</head>
<body>
  <p>First run not yet complete. Check back after 6am.</p>
</body>
</html>
```

- [ ] **Step 3: Commit and push**

```bash
git add .gitignore docs/index.html
git commit -m "feat: add GitHub Pages placeholder, fix .gitignore"
git push
```

- [ ] **Step 4: Enable GitHub Pages (manual — do this in the browser)**

Go to the repo on GitHub → Settings → Pages → Source: Deploy from branch → Branch: `main` → Folder: `/docs` → Save.

Wait ~60 seconds, then visit `https://nborders.github.io/news-intelligence/` (replace `nborders/news-intelligence` with the actual org/repo slug). You should see the placeholder page.

---

## Task 2: Write run_daily.py

**Files:**
- Create: `run_daily.py`

**Context:** This is the core orchestrator. It runs in the wiki-scraper directory. All subprocess calls use `cwd=REPO_DIR` and the venv Python. Scrapers are soft failures (log and continue). Claude, view_export, and git push are hard failures with appropriate escalation. The log is trimmed to 500 lines after each run.

Key paths derived at runtime:
- `REPO_DIR` = directory of `run_daily.py` itself
- `VENV_PYTHON` = `REPO_DIR / ".venv/bin/python3"`
- `CLAUDE_BIN` = resolved from `PATH` via `shutil.which("claude")`

- [ ] **Step 1: Write run_daily.py**

```python
#!/usr/bin/env python3
"""
run_daily.py — Morning brief orchestrator
Runs the full pipeline: scrapers → Claude analysis → HTML → git push.
Can be run manually at any time for an on-demand update.
"""

import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_DIR    = Path(__file__).parent.resolve()
VENV_PYTHON = REPO_DIR / ".venv" / "bin" / "python3"
LOG_FILE    = REPO_DIR / "morning_brief.log"
LOG_MAX     = 500   # lines to keep
CLAUDE_TIMEOUT = 300  # 5 minutes

SCIENCE_URL = "https://en.wikipedia.org/wiki/2026_in_science"


# ── Logging ──────────────────────────────────────────────────────────────────

def log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with LOG_FILE.open("a") as f:
        f.write(line + "\n")


def log_header() -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = f"\n=== {ts} ===\n"
    print(header, end="")
    with LOG_FILE.open("a") as f:
        f.write(header)


def trim_log() -> None:
    if not LOG_FILE.exists():
        return
    lines = LOG_FILE.read_text().splitlines(keepends=True)
    if len(lines) > LOG_MAX:
        LOG_FILE.write_text("".join(lines[-LOG_MAX:]))


# ── Subprocess helpers ────────────────────────────────────────────────────────

def run(cmd: list, timeout: int | None = 120) -> tuple[bool, str]:
    """Run a command. Returns (success, stderr_or_stdout_on_error)."""
    try:
        result = subprocess.run(
            cmd,
            cwd=REPO_DIR,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            return False, (result.stderr or result.stdout).strip()
        return True, ""
    except subprocess.TimeoutExpired:
        return False, f"timed out after {timeout}s"
    except Exception as e:
        return False, str(e)


def notify(title: str, message: str) -> None:
    """Fire a macOS notification."""
    script = f'display notification "{message}" with title "{title}"'
    subprocess.run(["osascript", "-e", script], capture_output=True)


# ── Pipeline steps ────────────────────────────────────────────────────────────

def run_scrapers() -> None:
    """Run all three scrapers. Failures are soft — log and continue."""
    steps = [
        ("scraper: current events",
         [str(VENV_PYTHON), "wiki_scraper.py"]),
        ("scraper: science",
         [str(VENV_PYTHON), "wiki_scraper.py", SCIENCE_URL]),
        ("scraper: news",
         [str(VENV_PYTHON), "news_scraper.py"]),
    ]
    for label, cmd in steps:
        ok, err = run(cmd, timeout=120)
        if ok:
            log(f"{label} — OK")
        else:
            log(f"{label} — WARNING: {err}")


def run_claude() -> Path:
    """
    Run Claude analysis. Returns path to the newly written analysis_*.md.
    Hard failure: exits the pipeline if Claude fails or produces no file.
    """
    claude_bin = shutil.which("claude")
    if not claude_bin:
        log("claude: ERROR — 'claude' not found in PATH")
        sys.exit(1)

    # Snapshot existing analysis files before the run
    before = set(REPO_DIR.glob("analysis_*.md"))

    ok, err = run(
        [claude_bin, "-p", "analyze the latest wiki and news exports"],
        timeout=CLAUDE_TIMEOUT,
    )
    if not ok:
        log(f"claude: ERROR — {err}")
        sys.exit(1)

    # Find the newly created analysis file
    after = set(REPO_DIR.glob("analysis_*.md"))
    new_files = sorted(after - before, key=lambda p: p.stat().st_mtime, reverse=True)
    if not new_files:
        # Fallback: newest overall (in case file was overwritten)
        all_files = sorted(REPO_DIR.glob("analysis_*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not all_files:
            log("claude: ERROR — no analysis_*.md found after run")
            sys.exit(1)
        analysis = all_files[0]
    else:
        analysis = new_files[0]

    log(f"claude: analysis written → {analysis.name}")
    return analysis


def run_view_export(analysis: Path) -> None:
    """
    Render analysis .md → HTML, copy to docs/index.html, delete per-date HTML.
    Hard failure: exits if view_export.py fails or output file not found.
    """
    ok, err = run(
        [str(VENV_PYTHON), "view_export.py", str(analysis), "--no-open"],
        timeout=60,
    )
    if not ok:
        log(f"html: ERROR — view_export.py failed: {err}")
        sys.exit(1)

    html_path = analysis.with_suffix(".html")
    if not html_path.exists():
        log(f"html: ERROR — expected {html_path.name} not found")
        sys.exit(1)

    dest = REPO_DIR / "docs" / "index.html"
    shutil.copy2(html_path, dest)
    html_path.unlink()  # delete per-date file
    log(f"html: docs/index.html written")


def run_git_push() -> None:
    """
    Commit and push docs/index.html. Soft failure with macOS notification.
    """
    date_str = datetime.now().strftime("%Y-%m-%d")

    for cmd, label in [
        (["git", "add", "docs/index.html"], "git add"),
        (["git", "commit", "-m", f"Daily brief {date_str}"], "git commit"),
        (["git", "push"], "git push"),
    ]:
        ok, err = run(cmd, timeout=30)
        if not ok:
            log(f"git: ERROR — {label} failed: {err}")
            notify("Morning Brief", f"git push failed — analysis is local only. Check morning_brief.log.")
            return

    log("git: pushed to origin/main")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    start = datetime.now()
    log_header()
    log("START")

    if not VENV_PYTHON.exists():
        log(f"ERROR — venv not found at {VENV_PYTHON}. Run: python3 -m venv .venv && pip install -r requirements.txt")
        sys.exit(1)

    run_scrapers()
    analysis = run_claude()
    run_view_export(analysis)
    run_git_push()

    elapsed = int((datetime.now() - start).total_seconds())
    log(f"DONE — {elapsed}s")
    trim_log()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Make it executable**

```bash
chmod +x run_daily.py
```

- [ ] **Step 3: Smoke test — dry run without committing**

Comment out the `run_git_push()` call in `main()` temporarily. Run:

```bash
python3 run_daily.py
```

Expected: scrapers run, Claude writes an analysis file, `docs/index.html` is updated, log shows each step. Open `docs/index.html` in a browser to confirm it looks right.

Uncomment `run_git_push()` after confirming.

- [ ] **Step 4: Full test — run with git push enabled**

```bash
python3 run_daily.py
```

Expected: all steps succeed, `morning_brief.log` shows a complete run block, `docs/index.html` is pushed to GitHub, the live URL shows today's analysis.

- [ ] **Step 5: Commit**

```bash
git add run_daily.py
git commit -m "feat: add run_daily.py pipeline orchestrator"
git push
```

---

## Task 3: Write install_launchd.sh

**Files:**
- Create: `install_launchd.sh`

**Context:** launchd agents run in a stripped environment. This script detects the full PATH, claude CLI location, and venv Python at install time, then bakes them into the plist. It verifies prerequisites before writing anything. The plist is written to `~/Library/LaunchAgents/` and registered with `launchctl load`.

- [ ] **Step 1: Write install_launchd.sh**

```bash
#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_LABEL="com.nick.morning-brief"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_LABEL.plist"
LOG_PATH="$REPO_DIR/morning_brief.log"

echo "=== Morning Brief — launchd installer ==="
echo ""

# ── Prerequisite checks ──────────────────────────────────────────────────────

# 1. venv
VENV_PYTHON="$REPO_DIR/.venv/bin/python3"
if [ ! -f "$VENV_PYTHON" ]; then
  echo "ERROR: .venv not found. Set it up first:"
  echo "  python3 -m venv .venv && source .venv/bin/activate && pip install requests beautifulsoup4"
  exit 1
fi
echo "✓ .venv found: $VENV_PYTHON"

# 2. claude CLI
CLAUDE_BIN="$(which claude 2>/dev/null || true)"
if [ -z "$CLAUDE_BIN" ]; then
  echo "ERROR: 'claude' not found in PATH. Install Claude Code CLI first."
  exit 1
fi
echo "✓ claude CLI found: $CLAUDE_BIN"

# 3. .gitignore entries
GITIGNORE="$REPO_DIR/.gitignore"
if ! grep -qxF '/index.html' "$GITIGNORE"; then
  echo ""
  echo "ERROR: .gitignore still has unanchored 'index.html'."
  echo "  Change it to '/index.html' and commit before running this script."
  echo "  (See the GitHub Pages Setup steps in the spec.)"
  exit 1
fi
if ! grep -q 'analysis_\*\.html' "$GITIGNORE"; then
  echo ""
  echo "ERROR: .gitignore is missing 'analysis_*.html'."
  echo "  Add it and commit before running this script."
  exit 1
fi
echo "✓ .gitignore entries verified"

# 4. docs/index.html exists
if [ ! -f "$REPO_DIR/docs/index.html" ]; then
  echo ""
  echo "ERROR: docs/index.html not found. Complete the GitHub Pages Setup steps first."
  exit 1
fi
echo "✓ docs/index.html found"

# ── Build full PATH for plist ────────────────────────────────────────────────

# Capture the current interactive PATH so launchd has it
FULL_PATH="$PATH"

# ── Write plist ──────────────────────────────────────────────────────────────

echo ""
echo "Writing plist to: $PLIST_PATH"

cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${PLIST_LABEL}</string>

  <key>ProgramArguments</key>
  <array>
    <string>${VENV_PYTHON}</string>
    <string>${REPO_DIR}/run_daily.py</string>
  </array>

  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>6</integer>
    <key>Minute</key>
    <integer>0</integer>
  </dict>

  <key>WorkingDirectory</key>
  <string>${REPO_DIR}</string>

  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>${FULL_PATH}</string>
    <key>HOME</key>
    <string>${HOME}</string>
  </dict>

  <key>StandardOutPath</key>
  <string>${LOG_PATH}</string>

  <key>StandardErrorPath</key>
  <string>${LOG_PATH}</string>

  <key>RunAtLoad</key>
  <false/>
</dict>
</plist>
PLIST

echo "✓ plist written"

# ── Register with launchctl ──────────────────────────────────────────────────

# Unload first if already registered (ignore error if not loaded)
launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH"

echo "✓ registered with launchctl"
echo ""
echo "Done. Morning brief will run daily at 6:00am."
echo "To run manually at any time: python3 $REPO_DIR/run_daily.py"
echo "To check logs: tail -f $LOG_PATH"
```

- [ ] **Step 2: Make it executable**

```bash
chmod +x install_launchd.sh
```

- [ ] **Step 3: Verify the script runs without errors**

```bash
bash install_launchd.sh
```

Expected output:
```
=== Morning Brief — launchd installer ===

✓ .venv found: /path/to/wiki-scraper/.venv/bin/python3
✓ claude CLI found: /usr/local/bin/claude
✓ .gitignore entries verified
✓ docs/index.html found

Writing plist to: /Users/.../Library/LaunchAgents/com.nick.morning-brief.plist
✓ plist written
✓ registered with launchctl

Done. Morning brief will run daily at 6:00am.
```

- [ ] **Step 4: Verify the plist is registered**

```bash
launchctl list | grep morning-brief
```

Expected: a line with `com.nick.morning-brief` and exit code 0 (or `-` if not yet run).

- [ ] **Step 5: Commit**

```bash
git add install_launchd.sh
git commit -m "feat: add install_launchd.sh for 6am scheduling"
git push
```

---

## Task 4: End-to-end verification

**Context:** Confirm the live URL works and the launchd job is correctly configured before declaring done.

- [ ] **Step 1: Confirm live GitHub Pages URL**

Visit `https://nborders.github.io/news-intelligence/` (or your actual URL). Confirm today's analysis is visible with proper styling — dark background, callout boxes, footnotes.

- [ ] **Step 2: Confirm morning_brief.log looks right**

```bash
cat morning_brief.log
```

Expected: a complete run block with timestamps, all steps OK, DONE with elapsed time.

- [ ] **Step 3: Test manual re-run**

```bash
python3 run_daily.py
```

Expected: runs successfully, `docs/index.html` updated, new git commit pushed.

- [ ] **Step 4: Confirm launchd will fire correctly (optional dry-run)**

To test launchd execution without waiting for 6am, temporarily trigger it:

```bash
launchctl start com.nick.morning-brief
```

Wait ~2 minutes, then check the log:

```bash
tail -30 morning_brief.log
```

Expected: a new run block appeared. Stop the job if needed:

```bash
launchctl stop com.nick.morning-brief
```
