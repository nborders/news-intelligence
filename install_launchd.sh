#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_LABEL="com.nick.daily-brief"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_LABEL.plist"
OLD_PLIST_PATH="$HOME/Library/LaunchAgents/com.nick.morning-brief.plist"
LOG_PATH="$REPO_DIR/morning_brief.log"

echo "=== Daily Brief — launchd installer ==="
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
  <array>
    <dict>
      <key>Hour</key>
      <integer>6</integer>
      <key>Minute</key>
      <integer>0</integer>
    </dict>
    <dict>
      <key>Hour</key>
      <integer>16</integer>
      <key>Minute</key>
      <integer>30</integer>
    </dict>
  </array>

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

# Remove old morning-brief job if it exists
if [ -f "$OLD_PLIST_PATH" ]; then
  launchctl unload "$OLD_PLIST_PATH" 2>/dev/null || true
  rm "$OLD_PLIST_PATH"
  echo "✓ removed old com.nick.morning-brief job"
fi

# Unload first if already registered (ignore error if not loaded)
launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH"

echo "✓ registered with launchctl"
echo ""
echo "Done. Daily brief will run at 6:00am and 4:30pm."
echo "To run manually at any time: python3 $REPO_DIR/run_daily.py"
echo "To check logs: tail -f $LOG_PATH"
