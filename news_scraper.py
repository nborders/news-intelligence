#!/usr/bin/env python3
from __future__ import annotations  # allows str | None syntax on Python 3.7–3.9
"""
Multi-Source News Scraper for Claude
=====================================
Fetches articles from a curated set of news sources with different
institutional perspectives, packages everything into a zip for Claude to read.

Sources included:
  npr         NPR News (US public media)
  meduza      Meduza (independent Russian journalism, based in Latvia)
  globaltimes Global Times (Chinese state media — useful for seeing the spin)
  telegram    Public Telegram channels (independent/Russian perspectives)

Usage:
    python3 news_scraper.py                        # all sources
    python3 news_scraper.py --sources npr meduza   # specific sources only
    python3 news_scraper.py --max-articles 10      # fewer articles per source

Requirements:
    pip install requests beautifulsoup4
"""

import argparse
import json
import re
import shutil
import sys
import time
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Missing dependencies. Run:  pip install requests beautifulsoup4")
    sys.exit(1)

# Always save output next to this script
SCRIPT_DIR = Path(__file__).parent.resolve()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}

# ─── Source Definitions ───────────────────────────────────────────────────────
#
# Each source has:
#   index_url   : the page to scrape article links from
#   base_url    : used to resolve relative links
#   link_filter : function(href) -> bool, returns True if the link is an article
#   label       : human-readable name
#   note        : what perspective/bias to keep in mind when reading

SOURCES = {
    "npr": {
        "label": "NPR News",
        "note": "US public media. Centrist, US-domestic focus. Good primary reporting.",
        "index_url": "https://text.npr.org",
        "base_url": "https://text.npr.org",
        "link_filter": lambda href: (
            href and (
                re.match(r'^/nx-s1-\d+', href) or   # current article format
                re.match(r'^/g-s1-\d+', href) or    # alternate current format
                re.match(r'^/\d{9,}$', href)        # old 10-digit numeric IDs
            )
        ),
    },

    "meduza": {
        "label": "Meduza (English)",
        "note": "Independent Russian journalism in exile, based in Riga, Latvia. "
                "Critical of Kremlin. Best source for Russian independent perspective.",
        "index_url": "https://meduza.io/en",
        "base_url": "https://meduza.io",
        "link_filter": lambda href: (
            href and
            re.match(r'^/en/(news|feature|cards|shapito|explainer)/', href)
        ),
    },

    "globaltimes": {
        "label": "Global Times (China)",
        "note": "Chinese Communist Party-aligned tabloid. More opinionated than Xinhua. "
                "Read it to see how China frames events — not as neutral reporting.",
        "index_url": "https://www.globaltimes.cn",
        "base_url": "https://www.globaltimes.cn",
        "link_filter": lambda href: (
            href and
            re.match(r'^/page/\d{4}/\d{2}/', href)   # GT article pattern
        ),
    },

    "isw": {
        "label": "Institute for the Study of War (ISW)",
        "note": "US-based nonpartisan defense think tank. Daily conflict updates on Ukraine "
                "and other active wars. Strong on military ground truth — order of battle, "
                "territorial changes, operational analysis. Not opinion; primary sourcing.",
        "bsky_handle": "thestudyofwar.bsky.social",
        "bluesky": True,
    },

    "factcheck": {
        "label": "FactCheck.org",
        "note": "Nonpartisan fact-checking from the Annenberg Public Policy Center. "
                "Useful for identifying specific false or misleading claims in circulation — "
                "especially useful alongside Global Times and political coverage.",
        "index_url": "https://www.factcheck.org/feed/",
        "rss": True,
    },

    "onion": {
        "label": "The Onion",
        "note": "American satirical news. Read it to see which narratives are culturally "
                "visible enough to satirize — satire is a leading indicator of what the "
                "public has absorbed. Often sharper than straight coverage on tone and spin.",
        "index_url": "https://theonion.com",
        "base_url": "https://theonion.com",
        "link_filter": lambda href: (
            href and
            href.startswith("/") and
            len(href) > 10 and
            not any(href.startswith(p) for p in [
                "/tag/", "/author/", "/category/", "/page/", "/search/",
                "/about", "/advertise", "/privacy", "/terms"
            ])
        ),
    },

    # ── Telegram channels ─────────────────────────────────────────────────────
    # t.me/s/CHANNEL renders as static HTML — no login needed for public channels.
    # Add or swap channels here as needed.
    #
    # Current defaults:
    #   meduzaio        Meduza's Telegram feed (Russian-language, raw/faster)
    #   currenttime_tv  Current Time (RFE/RL Russian service — independent)
    #   nexta_tv        NEXTA (Belarusian independent, strong Ukraine/Russia coverage)
    #   grey_zone       Rybar/Grey Zone (pro-Russian military — read as counter-view)

    "telegram_meduza": {
        "label": "Telegram: Meduza",
        "note": "Meduza's Telegram channel — Russian language, faster than website. "
                "Independent Russian journalism.",
        "index_url": "https://t.me/s/meduzaio",
        "base_url": "https://t.me",
        "telegram": True,
    },

    "telegram_currenttime": {
        "label": "Telegram: Current Time (RFE/RL Russia)",
        "note": "Radio Free Europe / Radio Liberty Russian service. "
                "US-funded but editorially independent. Russian-language.",
        "index_url": "https://t.me/s/currenttime",
        "base_url": "https://t.me",
        "telegram": True,
    },

    "telegram_nexta": {
        "label": "Telegram: NEXTA",
        "note": "Belarusian independent media in exile. Strong Ukraine/Russia coverage. "
                "Anti-Lukashenko, anti-Kremlin.",
        "index_url": "https://t.me/s/nexta_tv",
        "base_url": "https://t.me",
        "telegram": True,
    },
}

# Convenience groupings for --sources flag
SOURCE_GROUPS = {
    "all": list(SOURCES.keys()),
    "web": ["npr", "meduza", "globaltimes", "isw", "factcheck", "onion"],
    "telegram": ["telegram_meduza", "telegram_currenttime", "telegram_nexta"],
    "analysis": ["isw", "factcheck", "onion"],   # analysis/context layer
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def fetch(url: str, session: requests.Session, retries: int = 3) -> str | None:
    for attempt in range(retries):
        try:
            r = session.get(url, headers=HEADERS, timeout=20)
            r.raise_for_status()
            return r.text
        except requests.RequestException as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                print(f"    ✗ Failed: {url} ({e})")
                return None


def html_to_text(html: str, url: str, title_hint: str = "") -> str:
    """Strip HTML to clean readable text."""
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "nav", "footer", "aside",
                     "div.ad", "div.advertisement", "div.related",
                     "div.social", "div.share", "iframe"]):
        tag.decompose()

    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else title_hint or url

    # Try common article body selectors
    body = (
        soup.find("article") or
        soup.find(id="article-body") or
        soup.find(class_=re.compile(r'article[-_]?body|story[-_]?body|post[-_]?content')) or
        soup.find("main") or
        soup.body or
        soup
    )

    raw = body.get_text(separator="\n")
    lines = [l.rstrip() for l in raw.splitlines()]
    cleaned = re.sub(r'\n{3,}', '\n\n', "\n".join(lines)).strip()

    return f"# {title}\nSource: {url}\n\n{cleaned}"


def safe_filename(url: str, label: str = "") -> str:
    """Turn a URL into a safe filename."""
    path = urlparse(url).path
    stem = unquote(path).replace("/", "_").strip("_")
    stem = re.sub(r'[^\w\-]', '_', stem)
    prefix = re.sub(r'[^\w]', '_', label)[:20] + "__" if label else ""
    return (prefix + stem)[:160] + ".txt"


# ─── Telegram scraper ─────────────────────────────────────────────────────────

def scrape_telegram(source_key: str, config: dict, out_path: Path,
                    session: requests.Session, max_posts: int = 20) -> list[str]:
    """
    Scrape a public Telegram channel via t.me/s/CHANNEL static preview.
    Returns list of saved filenames.
    """
    label = config["label"]
    url = config["index_url"]
    print(f"\n  📱 {label}")
    print(f"     {url}")

    html = fetch(url, session)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    messages = soup.find_all("div", class_="tgme_widget_message_wrap")

    saved = []
    channel_slug = url.split("/s/")[-1]
    out_lines = [f"# {label}", f"Source: {url}", f"Scraped: {max_posts} most recent posts\n"]

    for i, msg in enumerate(messages[-max_posts:], 1):   # take the N most recent
        # Extract text
        text_el = msg.find("div", class_="tgme_widget_message_text")
        text = text_el.get_text(separator="\n").strip() if text_el else ""

        # Extract timestamp
        time_el = msg.find("time")
        ts = time_el.get("datetime", "")[:16] if time_el else ""

        # Extract message URL
        link_el = msg.find("a", class_="tgme_widget_message_date")
        msg_url = link_el["href"] if link_el else ""

        if text:
            out_lines.append(f"--- [{ts}] {msg_url}")
            out_lines.append(text)
            out_lines.append("")

    fname = f"{source_key}__{channel_slug}.txt"
    fpath = out_path / fname
    fpath.write_text("\n".join(out_lines), encoding="utf-8")
    size = fpath.stat().st_size
    print(f"     ✓ {len(messages)} posts → {fname} ({size:,} bytes)")
    return [fname]


# ─── RSS scraper ──────────────────────────────────────────────────────────────

def scrape_rss(source_key: str, config: dict, out_path: Path,
               session: requests.Session, max_articles: int = 15) -> list[str]:
    """
    Fetch and parse an RSS/Atom feed. No link-following — headline + description only.
    Returns list of saved filenames.
    """
    label = config["label"]
    note = config.get("note", "")
    url = config["index_url"]

    print(f"\n  📡 {label}")
    print(f"     {url}")

    xml_content = fetch(url, session)
    if not xml_content:
        return []

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        print(f"    ✗ RSS parse error: {e}")
        return []

    items = root.findall('.//item')   # RSS 2.0
    if not items:
        items = root.findall('.//{http://www.w3.org/2005/Atom}entry')  # Atom fallback

    out_lines = [
        f"# {label}",
        f"Source: {url}",
        f"Perspective: {note}",
        f"Items: {min(len(items), max_articles)} of {len(items)}",
        "",
    ]

    for item in items[:max_articles]:
        title = (item.findtext('title') or "").strip()
        link  = (item.findtext('link')  or "").strip()
        pub   = (item.findtext('pubDate') or item.findtext('updated') or "").strip()
        desc  = (item.findtext('description') or item.findtext(
                 '{http://www.w3.org/2005/Atom}summary') or "").strip()

        # Strip any HTML tags from description
        if desc:
            desc = BeautifulSoup(desc, "html.parser").get_text(separator=" ").strip()

        out_lines.append(f"## {title}")
        if pub:  out_lines.append(f"Date: {pub}")
        if link: out_lines.append(f"URL: {link}")
        if desc: out_lines.append(desc[:600])
        out_lines.append("")

    fname = f"{source_key}__rss.txt"
    fpath = out_path / fname
    fpath.write_text("\n".join(out_lines), encoding="utf-8")
    size = fpath.stat().st_size
    print(f"     ✓ {len(items)} items → {fname} ({size:,} bytes)")
    return [fname]


# ─── Bluesky scraper ──────────────────────────────────────────────────────────

def scrape_bluesky(source_key: str, config: dict, out_path: Path,
                   session: requests.Session, max_posts: int = 25) -> list[str]:
    """
    Fetch posts from a public Bluesky profile via the AT Protocol public API.
    No authentication required for public accounts.
    Returns list of saved filenames.
    """
    label = config["label"]
    note  = config.get("note", "")
    handle = config["bsky_handle"]
    api_url = (
        f"https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed"
        f"?actor={handle}&limit={max_posts}"
    )

    print(f"\n  🦋 {label}")
    print(f"     bsky.app/profile/{handle}")

    response = fetch(api_url, session)
    if not response:
        return []

    try:
        data = json.loads(response)
    except json.JSONDecodeError as e:
        print(f"    ✗ Bluesky JSON parse error: {e}")
        return []

    feed = data.get("feed", [])

    out_lines = [
        f"# {label}",
        f"Source: https://bsky.app/profile/{handle}",
        f"Perspective: {note}",
        f"Posts: {len(feed)}",
        "",
    ]

    for item in feed:
        post    = item.get("post", {})
        record  = post.get("record", {})
        text    = record.get("text", "").strip()
        created = record.get("createdAt", "")[:16].replace("T", " ")

        # Build a direct link to the post
        uri     = post.get("uri", "")          # at://did:plc:.../app.bsky.feed.post/ID
        post_id = uri.split("/")[-1] if uri else ""
        post_url = f"https://bsky.app/profile/{handle}/post/{post_id}" if post_id else ""

        if text:
            out_lines.append(f"--- [{created}] {post_url}")
            out_lines.append(text)
            out_lines.append("")

    fname = f"{source_key}__bsky.txt"
    fpath = out_path / fname
    fpath.write_text("\n".join(out_lines), encoding="utf-8")
    size = fpath.stat().st_size
    print(f"     ✓ {len(feed)} posts → {fname} ({size:,} bytes)")
    return [fname]


# ─── Web article scraper ──────────────────────────────────────────────────────

def scrape_web_source(source_key: str, config: dict, out_path: Path,
                      session: requests.Session, max_articles: int = 15,
                      delay: float = 1.0) -> list[str]:
    """
    Fetch a news site index page, extract article links, scrape each article.
    Returns list of saved filenames.
    """
    label = config["label"]
    note = config.get("note", "")
    index_url = config["index_url"]
    base_url = config["base_url"]
    link_filter = config["link_filter"]

    print(f"\n  🌐 {label}")
    print(f"     {index_url}")

    # Save source metadata file
    meta_fname = f"{source_key}__META.txt"
    (out_path / meta_fname).write_text(
        f"# {label}\n\nPerspective note: {note}\n\nIndex: {index_url}\n",
        encoding="utf-8"
    )

    # Fetch index
    index_html = fetch(index_url, session)
    if not index_html:
        return [meta_fname]

    soup = BeautifulSoup(index_html, "html.parser")
    seen, links = set(), []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if link_filter(href):
            full = urljoin(base_url, href.split("?")[0])
            if full not in seen:
                seen.add(full)
                links.append((full, a.get_text(strip=True)[:80]))

    selected = links[:max_articles]
    print(f"     Found {len(links)} article links, fetching {len(selected)}...")

    saved = [meta_fname]
    for i, (url, link_text) in enumerate(selected, 1):
        fname = safe_filename(url, source_key)
        fpath = out_path / fname

        html = fetch(url, session)
        if html is None:
            continue

        fpath.write_text(html_to_text(html, url, link_text), encoding="utf-8")
        size = fpath.stat().st_size
        print(f"     [{i:02d}/{len(selected)}] ✓ {fname[:60]}  ({size:,} bytes)")
        saved.append(fname)
        time.sleep(delay)

    return saved


# ─── Main ─────────────────────────────────────────────────────────────────────

def run(source_keys: list[str], max_articles: int = 15, max_posts: int = 20,
        delay: float = 1.0, out_dir: str = "news_export") -> str:

    out_path = SCRIPT_DIR / out_dir
    if out_path.exists():
        shutil.rmtree(out_path)
    out_path.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update(HEADERS)

    manifest = ["News Export", f"Sources: {', '.join(source_keys)}", "─" * 60]
    all_files = []

    for key in source_keys:
        if key not in SOURCES:
            print(f"  ⚠  Unknown source '{key}', skipping.")
            continue
        config = SOURCES[key]

        if config.get("telegram"):
            files = scrape_telegram(key, config, out_path, session, max_posts)
        elif config.get("bluesky"):
            files = scrape_bluesky(key, config, out_path, session, max_posts)
        elif config.get("rss"):
            files = scrape_rss(key, config, out_path, session, max_articles)
        else:
            files = scrape_web_source(key, config, out_path, session, max_articles, delay)

        all_files.extend(files)
        manifest.append(f"\n[{config['label']}]")
        manifest.extend(f"  {f}" for f in files)

    # Write manifest
    (out_path / "MANIFEST.txt").write_text("\n".join(manifest), encoding="utf-8")

    # Zip
    zip_name = "news_export.zip"
    zip_path = SCRIPT_DIR / zip_name
    file_count = len(list(out_path.iterdir()))

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in out_path.iterdir():
            zf.write(f, arcname=f.name)

    shutil.rmtree(out_path)

    total_size = zip_path.stat().st_size
    print(f"\n✅  Done!  {file_count} files → {zip_path.name}  ({total_size:,} bytes)")
    print(f"   Saved to: {zip_path}")
    print(f"   Tell Claude: 'analyze the latest news export'\n")
    return str(zip_path)


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Fetch news from multiple sources for Claude analysis.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Sources:
  npr                NPR News (US public media)
  meduza             Meduza — independent Russian journalism (English)
  globaltimes        Global Times — Chinese state media
  telegram_meduza    Meduza Telegram channel (Russian-language)
  telegram_currenttime  Current Time / RFE-RL Russia (Russian-language)
  telegram_nexta     NEXTA — Belarusian independent media

Groups:
  all                All sources (default)
  web                npr + meduza + globaltimes only
  telegram           All telegram channels only

Examples:
  python3 news_scraper.py
  python3 news_scraper.py --sources web
  python3 news_scraper.py --sources npr meduza
  python3 news_scraper.py --sources telegram --max-posts 30
        """
    )
    parser.add_argument(
        "--sources", nargs="+", default=["all"],
        help="Source keys or group names (default: all)"
    )
    parser.add_argument(
        "--max-articles", type=int, default=15,
        help="Max articles per web source (default: 15)"
    )
    parser.add_argument(
        "--max-posts", type=int, default=20,
        help="Max posts per Telegram channel (default: 20)"
    )
    parser.add_argument(
        "--delay", type=float, default=1.0,
        help="Seconds between requests (default: 1.0)"
    )

    args = parser.parse_args()

    # Resolve groups
    resolved = []
    for s in args.sources:
        if s in SOURCE_GROUPS:
            resolved.extend(SOURCE_GROUPS[s])
        elif s in SOURCES:
            resolved.append(s)
        else:
            print(f"⚠  Unknown source or group: '{s}'")

    # Deduplicate while preserving order
    seen = set()
    final = [x for x in resolved if not (x in seen or seen.add(x))]

    if not final:
        print("No valid sources selected. Run with --help to see options.")
        sys.exit(1)

    run(final, args.max_articles, args.max_posts, args.delay)


if __name__ == "__main__":
    main()
