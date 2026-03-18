#!/usr/bin/env python3
"""
Automated Analysis
==================
Reads Portal_Current_events_export.zip and news_export.zip,
calls Claude API to produce a Wikipedia-anchored current events briefing,
and saves analysis_YYYY-MM-DD.md to this directory.

Usage:
    python3 analyze.py                # uses today's date
    python3 analyze.py --date 2026-03-18   # specific date label

Requires ANTHROPIC_API_KEY in the environment or in a .env file
at ~/Desktop/claude/tools/wiki-scraper/.env (KEY=value format).
"""

import argparse
import os
import sys
import zipfile
from datetime import date
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
MODEL = "claude-opus-4-6"
MAX_TOKENS = 8000

# ── Prompt ─────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are producing a daily current events intelligence briefing.

Wikipedia's Current Events portal is the editorial spine — it determines what is significant enough to track. All other sources add depth, perspective, and verification to topics Wikipedia is already covering.

Only surface topics from other sources if they are clearly absent from Wikipedia AND consequential — meaning the event has real impact on people's lives or the shape of the world, regardless of how much press it has received. A massacre with no Western coverage belongs. A celebrity feud does not. Filter: OpEds, gossip, human-interest stories with no broader consequence, propaganda with no factual basis.

OUTPUT FORMAT — follow exactly:

# Current Events Analysis — [Month Day, Year]
*Wikipedia-anchored briefing · Sources: wiki export + news export*

---

## [Topic from Wikipedia Current Events]
*[One-line italic subtitle — the sharpest frame for this story]*

[2–4 paragraphs. Wikipedia as spine, other sources as branches. Footnote every factual claim with [^N].]

[Callout boxes where warranted:]
> **KEY:** for strategic insights the reader needs to sit with
> **WATCH:** for under-covered events that have real consequences
> **ABSURD:** for The Onion / cultural saturation signals

---

## [Next Topic]
...

---

## Dispatch from the Absurd
*A humor reading on what has reached cultural saturation*

> **ABSURD:** [The Onion headline or cultural signal + what it tells us]

---

## Sources

[^1]: [Wikipedia — Portal:Current Events](https://en.wikipedia.org/wiki/Portal:Current_events)
[^2]: [Source Title](https://url)
...

IMPORTANT RULES:
- Every factual claim must have a [^N] citation
- Section headings should be specific and sharp, not generic ("Iran War: The Hormuz Trap" not "Iran")
- Subtitles (the italic line after each h2) should be the most insight-dense sentence in that section
- KEY callouts: strategic or structural insight. WATCH callouts: consequential + undercovered. ABSURD: cultural signal.
- Write for an informed, analytical reader — not a general audience
- Do not pad. If a topic doesn't warrant a full section, fold it into "## Other Consequential Events"

IMAGES — include one relevant image per major section on its own line, using this exact format:
![Descriptive caption](https://upload.wikimedia.org/wikipedia/commons/EXACT/PATH.jpg)
Only use Wikipedia Commons image URLs you are highly confident exist from your training data.
Place images after the first paragraph of a section. Omit if uncertain of the URL.

VIDEOS / AUDIO — when scraped content references a video or audio piece worth hearing, include it using:
[VIDEO: Descriptive title](https://youtube.com/watch?v=EXACT_ID)
[AUDIO: Descriptive title](https://direct-audio-url)
Only include if you have a specific real URL from the scraped source content — never fabricate URLs.
"""


# ── Zip reading ─────────────────────────────────────────────────────────────────

def read_zip(zip_path: Path, max_chars: int = 180_000) -> str:
    if not zip_path.exists():
        return f"[ZIP NOT FOUND: {zip_path.name}]\n"

    parts = []
    total = 0
    with zipfile.ZipFile(zip_path) as zf:
        names = sorted(
            n for n in zf.namelist()
            if n.endswith(".txt") and "MANIFEST" not in n and "__META" not in n
        )
        for name in names:
            text = zf.read(name).decode("utf-8", errors="replace")
            header = f"\n\n{'='*60}\nSOURCE: {name}\n{'='*60}\n"
            chunk = header + text
            if total + len(chunk) > max_chars:
                remaining = max_chars - total
                if remaining > len(header) + 200:
                    parts.append(chunk[:remaining])
                    parts.append("\n\n[... truncated due to length ...]\n")
                break
            parts.append(chunk)
            total += len(chunk)

    return "".join(parts)


# ── API key loading ─────────────────────────────────────────────────────────────

def load_api_key() -> str:
    """Return ANTHROPIC_API_KEY from environment or .env file."""
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key:
        return key

    env_file = SCRIPT_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line.startswith("ANTHROPIC_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")

    return ""


# ── Main ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate daily news analysis via Claude API")
    parser.add_argument("--date", default=None, help="Date label for output file (YYYY-MM-DD, default: today)")
    args = parser.parse_args()

    target_date = args.date or date.today().strftime("%Y-%m-%d")
    output_path = SCRIPT_DIR / f"analysis_{target_date}.md"

    api_key = load_api_key()
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not found.")
        print("  Set it in the environment, or add it to:")
        print(f"  {SCRIPT_DIR / '.env'}  (one line: ANTHROPIC_API_KEY=sk-ant-...)")
        sys.exit(1)

    # Import here so missing package gives a clear error
    try:
        import anthropic
    except ImportError:
        print("ERROR: anthropic package not installed.")
        print(f"  Run: {SCRIPT_DIR / '.venv/bin/pip'} install anthropic")
        sys.exit(1)

    wiki_zip = SCRIPT_DIR / "Portal_Current_events_export.zip"
    news_zip = SCRIPT_DIR / "news_export.zip"

    print(f"Reading wiki export ({wiki_zip.name})...")
    wiki_content = read_zip(wiki_zip)
    print(f"  {len(wiki_content):,} chars")

    print(f"Reading news export ({news_zip.name})...")
    news_content = read_zip(news_zip)
    print(f"  {len(news_content):,} chars")

    # Format the date nicely for the prompt
    try:
        from datetime import datetime
        nice_date = datetime.strptime(target_date, "%Y-%m-%d").strftime("%B %d, %Y").replace(" 0", " ")
    except Exception:
        nice_date = target_date

    user_message = f"""Today is {nice_date}.

Analyze the following exports and write the complete current events briefing.

== WIKIPEDIA CURRENT EVENTS EXPORT (the spine) ==
{wiki_content}

== NEWS EXPORT (the branches) ==
{news_content}

Write the full analysis now."""

    print(f"\nCalling {MODEL} (this takes ~30–60 seconds)...")
    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    analysis = message.content[0].text
    output_path.write_text(analysis, encoding="utf-8")

    tokens_in  = message.usage.input_tokens
    tokens_out = message.usage.output_tokens
    print(f"Done. Tokens: {tokens_in:,} in / {tokens_out:,} out")
    print(f"Saved: {output_path.name}")

    return output_path


if __name__ == "__main__":
    main()
