#!/bin/bash
# morning_brief.sh — daily news intelligence pipeline
# Runs at 6:30 AM via launchd. Scrapes → analyzes → generates HTML → updates index.
# Logs to morning_brief.log in this directory.

set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$DIR/.venv/bin/python3"
LOG="$DIR/morning_brief.log"

# Rotate log: keep last 500 lines
if [ -f "$LOG" ]; then
    tail -500 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
fi

exec >> "$LOG" 2>&1

echo ""
echo "========================================"
echo "  Morning Brief — $(date '+%A, %B %-d, %Y at %H:%M')"
echo "========================================"

cd "$DIR"

# Load .env if present (picks up ANTHROPIC_API_KEY)
if [ -f "$DIR/.env" ]; then
    set -a
    # shellcheck disable=SC1090
    source "$DIR/.env"
    set +a
fi

# 1. Wikipedia scrape
echo ""
echo "[1/4] Scraping Wikipedia Current Events..."
"$PYTHON" wiki_scraper.py
echo "      Done."

# 2. News scrape
echo ""
echo "[2/4] Scraping news sources..."
"$PYTHON" news_scraper.py
echo "      Done."

# 3. Claude analysis
echo ""
echo "[3/4] Running Claude analysis..."
"$PYTHON" analyze.py
echo "      Done."

# 4. Generate HTML
echo ""
echo "[4/4] Generating HTML..."
"$PYTHON" view_export.py --no-open
echo "      Done."

# Symlink latest analysis HTML as index.html (served by localhost:8080)
LATEST_HTML=$(ls -t "$DIR"/analysis_*.html 2>/dev/null | head -1)
if [ -n "$LATEST_HTML" ]; then
    ln -sf "$LATEST_HTML" "$DIR/index.html"
    echo ""
    echo "  → $(basename "$LATEST_HTML") → index.html"
fi

echo ""
echo "  Morning brief ready: http://localhost:8080/"
echo "========================================"
