#!/usr/bin/env python3
"""
run_daily.py — Morning brief orchestrator
Runs the full pipeline: scrapers → Claude analysis → HTML → git push.
Can be run manually at any time for an on-demand update.
"""

import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_DIR    = Path(__file__).parent.resolve()
VENV_PYTHON = REPO_DIR / ".venv" / "bin" / "python3"
LOG_FILE    = REPO_DIR / "morning_brief.log"
LOG_MAX     = 500   # lines to keep
CLAUDE_TIMEOUT = 600  # 10 minutes

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

def run(cmd: list, timeout: int | None = 120, stdin_devnull: bool = False) -> tuple[bool, str]:
    """Run a command. Returns (success, stderr_or_stdout_on_error)."""
    try:
        result = subprocess.run(
            cmd,
            cwd=REPO_DIR,
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL if stdin_devnull else None,
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

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%I:%M%p").lstrip("0").lower()  # "6:00am" / "4:30pm"
    prompt = (
        f"analyze the latest wiki and news exports. "
        f"Today is {date_str} and the current time is {time_str}."
    )
    ok, err = run(
        [claude_bin, "--dangerously-skip-permissions", "-p", prompt],
        timeout=CLAUDE_TIMEOUT,
        stdin_devnull=True,
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
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%I:%M%p").lstrip("0").lower()

    for cmd, label in [
        (["git", "add", "docs/index.html"], "git add"),
        (["git", "commit", "-m", f"Daily brief {date_str} {time_str}"], "git commit"),
        (["git", "push"], "git push"),
    ]:
        ok, err = run(cmd, timeout=30)
        if not ok:
            log(f"git: ERROR — {label} failed: {err}")
            notify("Daily Brief", f"{label} failed — analysis is local only. Check morning_brief.log.")
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
