#!/usr/bin/env python3
from __future__ import annotations  # allows str | None syntax on Python 3.7–3.9
"""
Wikipedia Deep Scraper
======================
Fetches a Wikipedia page and its first layer of linked article pages,
then packages everything into a zip archive for upload to Claude.

Usage:
    python wiki_scraper.py [URL] [options]

Examples:
    python wiki_scraper.py https://en.wikipedia.org/wiki/Portal:Current_events
    python wiki_scraper.py https://en.wikipedia.org/wiki/2026_Iran_war --max-links 30
    python wiki_scraper.py https://en.wikipedia.org/wiki/Portal:Current_events --text-only

Requirements:
    pip install requests beautifulsoup4
"""

import argparse
import os
import re
import shutil
import sys
import time
import zipfile
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote

# Always save output next to this script, regardless of where you run it from
SCRIPT_DIR = Path(__file__).parent.resolve()

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Missing dependencies. Run:  pip install requests beautifulsoup4")
    sys.exit(1)


# ─── Config ───────────────────────────────────────────────────────────────────

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; WikiScraperForClaudeAnalysis/1.0; personal research)"
}

SKIP_LINK_PREFIXES = (
    "/wiki/Special:",
    "/wiki/Help:",
    "/wiki/Wikipedia:",
    "/wiki/Talk:",
    "/wiki/User:",
    "/wiki/User_talk:",
    "/wiki/File:",
    "/wiki/Category:",
    "/wiki/Template:",
    "/wiki/Portal:",   # skip portals in sub-links (we ARE the portal root)
    "#",               # skip anchor-only links
)

# ─── Helpers ──────────────────────────────────────────────────────────────────

def slug(url: str) -> str:
    """Convert a Wikipedia URL to a safe filename stem."""
    path = urlparse(url).path          # e.g. /wiki/2026_Iran_war
    stem = path.replace("/wiki/", "").replace("/", "_")
    stem = unquote(stem)               # decode %XX encoding
    stem = re.sub(r'[^\w\-.]', '_', stem)
    return stem[:180]                  # cap length


def fetch(url: str, session: requests.Session, retries: int = 3) -> str | None:
    """Fetch a URL, return HTML text or None on failure."""
    for attempt in range(retries):
        try:
            r = session.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            return r.text
        except requests.RequestException as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                print(f"  ✗ Failed: {url}  ({e})")
                return None


def extract_article_links(html: str, base_url: str = "https://en.wikipedia.org") -> list[str]:
    """Return unique Wikipedia article links from the page body."""
    soup = BeautifulSoup(html, "html.parser")
    body = soup.find(id="bodyContent") or soup.body or soup
    seen, links = set(), []
    for a in body.find_all("a", href=True):
        href = a["href"]
        if not href.startswith("/wiki/"):
            continue
        if any(href.startswith(p) for p in SKIP_LINK_PREFIXES):
            continue
        full = urljoin(base_url, href.split("#")[0])   # strip fragment
        if full not in seen:
            seen.add(full)
            links.append(full)
    return links


def html_to_text(html: str, url: str) -> str:
    """Strip HTML to clean readable text — much smaller files, easier for Claude."""
    soup = BeautifulSoup(html, "html.parser")

    # Remove noise
    for tag in soup(["script", "style", "sup", "nav", "footer",
                      "table.navbox", "div.reflist", "div.mw-jump-link",
                      "div#toc", "div.hatnote", "span.mw-editsection"]):
        tag.decompose()

    title = soup.find("h1")
    title_text = title.get_text(strip=True) if title else slug(url)

    body = soup.find(id="bodyContent") or soup.body
    raw = body.get_text(separator="\n") if body else soup.get_text(separator="\n")

    # Collapse blank lines
    lines = [l.rstrip() for l in raw.splitlines()]
    cleaned = re.sub(r'\n{3,}', '\n\n', "\n".join(lines)).strip()

    return f"# {title_text}\nSource: {url}\n\n{cleaned}"


# ─── Main ─────────────────────────────────────────────────────────────────────

def scrape(root_url: str, max_links: int = 25, text_only: bool = True,
           delay: float = 0.8, out_dir: str = "wiki_export") -> str:
    """
    Fetch root_url and up to max_links of its sub-articles.
    Returns path to the output zip file.
    """
    # Temp working folder (inside the project dir, cleaned up after zipping)
    out_path = SCRIPT_DIR / out_dir
    if out_path.exists():
        shutil.rmtree(out_path)   # clear any leftover from a previous interrupted run
    out_path.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update(HEADERS)

    ext = ".txt" if text_only else ".html"
    manifest_lines = [f"Wikipedia Export\nRoot: {root_url}\n{'─'*60}"]

    # ── Fetch root page ──────────────────────────────────────────
    print(f"\n📥  Fetching root page...")
    print(f"    {root_url}")
    root_html = fetch(root_url, session)
    if not root_html:
        print("ERROR: Could not fetch root page. Aborting.")
        sys.exit(1)

    root_name = slug(root_url) + ext
    root_file = out_path / root_name

    if text_only:
        root_file.write_text(html_to_text(root_html, root_url), encoding="utf-8")
    else:
        root_file.write_text(root_html, encoding="utf-8")

    root_size = root_file.stat().st_size
    manifest_lines.append(f"[ROOT] {root_name}  ({root_size:,} bytes)")
    print(f"  ✓  Saved root: {root_name}  ({root_size:,} bytes)")

    # ── Collect sub-article links ────────────────────────────────
    all_links = extract_article_links(root_html)
    selected = all_links[:max_links]
    print(f"\n🔗  Found {len(all_links)} article links. Fetching first {len(selected)}...\n")

    # ── Fetch each sub-article ───────────────────────────────────
    for i, url in enumerate(selected, 1):
        fname = slug(url) + ext
        fpath = out_path / fname

        print(f"  [{i:02d}/{len(selected)}] {url.split('/wiki/')[-1]}")

        html = fetch(url, session)
        if html is None:
            manifest_lines.append(f"[FAIL] {url}")
            continue

        if text_only:
            fpath.write_text(html_to_text(html, url), encoding="utf-8")
        else:
            fpath.write_text(html, encoding="utf-8")

        size = fpath.stat().st_size
        manifest_lines.append(f"  {fname}  ({size:,} bytes)  {url}")
        print(f"        ✓  {fname}  ({size:,} bytes)")

        time.sleep(delay)   # be polite to Wikipedia's servers

    # ── Write manifest ───────────────────────────────────────────
    manifest_path = out_path / "MANIFEST.txt"
    manifest_path.write_text("\n".join(manifest_lines), encoding="utf-8")

    # ── Zip everything ───────────────────────────────────────────
    # Fixed name per URL — always overwrites the previous run, no accumulation
    zip_name = f"{slug(root_url)}_export.zip"
    zip_path = SCRIPT_DIR / zip_name

    file_count = len(list(out_path.iterdir()))

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in out_path.iterdir():
            zf.write(f, arcname=f.name)

    # ── Clean up temp folder ─────────────────────────────────────
    shutil.rmtree(out_path)

    total_size = zip_path.stat().st_size
    print(f"\n✅  Done!  {file_count} files → {zip_path.name}  ({total_size:,} bytes)")
    print(f"   Saved to: {zip_path}")
    print(f"   Claude can read this directly — just say 'analyze the latest wiki export'.\n")
    return str(zip_path)


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Fetch a Wikipedia page + its linked articles for Claude analysis."
    )
    parser.add_argument(
        "url",
        nargs="?",
        default="https://en.wikipedia.org/wiki/Portal:Current_events",
        help="Wikipedia URL to scrape (default: Current Events portal)"
    )
    parser.add_argument(
        "--max-links", type=int, default=25,
        help="Max number of sub-article links to follow (default: 25)"
    )
    parser.add_argument(
        "--text-only", action="store_true", default=True,
        help="Save as clean text instead of raw HTML — smaller files (default: on)"
    )
    parser.add_argument(
        "--html", action="store_true",
        help="Save raw HTML instead of text (larger but preserves structure)"
    )
    parser.add_argument(
        "--delay", type=float, default=0.8,
        help="Seconds to wait between requests (default: 0.8 — be polite!)"
    )
    parser.add_argument(
        "--out-dir", default="wiki_export",
        help="Directory to save files before zipping (default: wiki_export/)"
    )

    args = parser.parse_args()
    text_only = not args.html  # --html overrides --text-only default

    scrape(
        root_url=args.url,
        max_links=args.max_links,
        text_only=text_only,
        delay=args.delay,
        out_dir=args.out_dir,
    )


if __name__ == "__main__":
    main()
