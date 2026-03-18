# News Intelligence Tools

A three-script workflow for building Wikipedia-anchored current events analysis with multi-source perspective. Your Mac fetches the content; Claude reads the zips and writes the analysis; `view_export.py` renders it as a clean browser page with clickable footnotes.

---

## Architecture

**Wikipedia is the spine.** The Current Events portal is the editorial authority — it determines what's significant enough to track. All other sources add depth, perspective, and verification to topics Wikipedia is already covering. Claude only surfaces topics from other sources if they're clearly absent from Wikipedia *and* consequential — meaning the event has real impact on people's lives or the shape of the world, regardless of how much press it's received. A massacre with no Western coverage belongs. A celebrity feud does not. What gets filtered: OpEds, gossip, human-interest stories with no broader consequence, and propaganda with no factual basis.

```
Wikipedia Current Events (spine)
    ├── NPR             ← US public media depth
    ├── Meduza          ← Independent Russian journalism
    ├── Global Times    ← Chinese state framing (read the spin)
    ├── ISW (Bluesky)   ← Military/conflict analysis
    ├── FactCheck.org   ← Political claim verification
    ├── The Onion       ← Cultural saturation signal
    ├── Telegram: Meduza      ← Russian-language feed
    ├── Telegram: Current Time ← RFE/RL Russia service
    └── Telegram: NEXTA        ← Belarusian independent media
```

---

## One-Time Setup (macOS)

```bash
cd ~/Desktop/claude/tools/wiki-scraper

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install requests beautifulsoup4
```

Each new Terminal session, activate first:
```bash
source ~/Desktop/claude/tools/wiki-scraper/.venv/bin/activate
```

---

## The Workflow

### Step 1 — Fetch content (run on your Mac)

```bash
# Wikipedia Current Events + linked sub-articles
python3 wiki_scraper.py

# All news sources
python3 news_scraper.py
```

Both scripts save zips to this folder, overwriting the previous run.

### Step 2 — Ask Claude for analysis

Tell Claude: **"analyze the latest wiki and news exports"**

Claude will:
1. Read `Portal_Current_events_export.zip` (the spine)
2. Read `news_export.zip` (the branches)
3. Write an `analysis_YYYY-MM-DD.md` file using Wikipedia topics as the structure, footnoting every claim back to its source article
4. Save it to this folder

### Step 3 — View in browser

```bash
python3 view_export.py              # auto-finds latest analysis_*.md
python3 view_export.py analysis_2026-03-13.md   # specific file
python3 view_export.py news_export.zip           # browse raw content
```

---

## Script 1: `wiki_scraper.py` — Wikipedia Deep Dive

Fetches the Wikipedia Current Events portal + its first layer of linked articles.

```bash
# Current Events portal (default)
python3 wiki_scraper.py

# Specific article + more linked pages
python3 wiki_scraper.py https://en.wikipedia.org/wiki/2026_Iran_war --max-links 40
```

| Flag | Default | Description |
|------|---------|-------------|
| `--max-links N` | 25 | Sub-articles to fetch |
| `--html` | off | Save raw HTML instead of clean text |
| `--delay N` | 0.8 | Seconds between requests |

---

## Script 2: `news_scraper.py` — Multi-Source News Bundle

```bash
# All sources (default)
python3 news_scraper.py

# Web sources only (NPR + Meduza + Global Times + ISW + FactCheck + Onion)
python3 news_scraper.py --sources web

# Telegram channels only
python3 news_scraper.py --sources telegram

# Mix and match
python3 news_scraper.py --sources npr meduza telegram_nexta
```

### Sources

| Key | Name | Perspective |
|-----|------|-------------|
| `npr` | NPR News | US public media, centrist |
| `meduza` | Meduza (English) | Independent Russian journalism in exile |
| `globaltimes` | Global Times | Chinese state media — read to see the spin |
| `isw` | Institute for the Study of War | Nonpartisan military analysis via Bluesky |
| `factcheck` | FactCheck.org | Nonpartisan fact-checking via RSS |
| `onion` | The Onion | Satire — tracks what narratives have reached cultural visibility |
| `telegram_meduza` | Telegram: Meduza | Meduza's Telegram, Russian-language |
| `telegram_currenttime` | Telegram: Current Time | RFE/RL Russia service |
| `telegram_nexta` | Telegram: NEXTA | Belarusian independent media |

### Groups

| Group | Includes |
|-------|----------|
| `all` | Everything (default) |
| `web` | npr, meduza, globaltimes, isw, factcheck, onion |
| `analysis` | isw + factcheck + onion |
| `telegram` | telegram_meduza + telegram_currenttime + telegram_nexta |

| Flag | Default | Description |
|------|---------|-------------|
| `--max-articles N` | 15 | Articles per web source |
| `--max-posts N` | 20 | Posts per Telegram/Bluesky source |
| `--delay N` | 1.0 | Seconds between requests |

---

## Script 3: `view_export.py` — Analysis Viewer

Renders Claude's `analysis_*.md` as a browser page with sidebar navigation and clickable footnotes. Falls back to raw zip browsing if no analysis file exists.

```bash
python3 view_export.py                          # latest analysis_*.md
python3 view_export.py analysis_2026-03-13.md  # specific analysis
python3 view_export.py news_export.zip          # raw zip browser
python3 view_export.py --no-open               # generate HTML without opening browser
```

---

## Analysis Format

Claude writes analyses to `analysis_YYYY-MM-DD.md` using footnoted markdown. See `analysis_template.md` for the full format. Key conventions:

- `[^1]` in body text → clickable superscript in the viewer
- `[^1]: [Title](URL)` in the Sources section → numbered footnote with backlink
- Sections follow Wikipedia's topic structure, not the news sources' structure

---

## Output Files

```
wiki-scraper/
├── README.md
├── requirements.txt
├── wiki_scraper.py
├── news_scraper.py
├── view_export.py
├── analysis_template.md          ← footnote format reference
├── analysis_YYYY-MM-DD.md        ← Claude's analysis (save to repo)
├── .venv/                        ← don't commit
├── Portal_Current_events_export.zip  ← wiki output (auto-overwritten, not committed)
└── news_export.zip               ← news output (auto-overwritten, not committed)
```

Zips are always overwritten on each run — no accumulation. Analysis `.md` files are committed to the repo as a running record.

---

## Adding a Telegram Channel

Edit `news_scraper.py` and add an entry to `SOURCES`:

```python
"telegram_mychannel": {
    "label": "Telegram: My Channel",
    "note": "What perspective this represents.",
    "index_url": "https://t.me/s/CHANNELNAME",
    "base_url": "https://t.me",
    "telegram": True,
},
```

Then add the key to `SOURCE_GROUPS["telegram"]` if you want it in the `telegram` group.
