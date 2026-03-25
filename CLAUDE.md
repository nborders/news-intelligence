# CLAUDE.md — News Intelligence Workflow

This folder contains a Wikipedia-anchored current events analysis workflow.
When asked to "analyze the latest wiki and news exports," follow everything below exactly.

---

## Your Job

Read the zip files in this folder, write a `analysis_YYYY-MM-DD.md` file, and save it here.
Do not open a browser or run `view_export.py` — the user does that themselves.

**Expected zip files:**
- `Portal_Current_events_export.zip` — news editorial spine (required)
- `news_export.zip` — supplementary news sources (required)
- `2026_in_science_export.zip` — science editorial spine (include Science & Discovery section when present; skip that section if absent)

If the science zip is missing, note briefly at the top of the Science & Discovery section: *"Science export not included in this run — run `python3 wiki_scraper.py https://en.wikipedia.org/wiki/2026_in_science` to add it."*

---

## The Core Architecture

**Wikipedia is the spine. Everything else is a branch.**

The Wikipedia Current Events portal (`Portal_Current_events_export.zip`) is the editorial authority. It determines what's significant enough to track. Every section you write must anchor to a topic Wikipedia is already covering.

The news sources (`news_export.zip`) add depth, perspective, and verification to Wikipedia's topics. They do not set the agenda.

The only exception: if a non-Wikipedia source covers an event that is clearly absent from Wikipedia AND clearly consequential — meaning it has real impact on people's lives or the shape of the world — include it. A massacre with no Western press coverage belongs. A celebrity feud does not.

**What to filter out:** OpEds, gossip, human-interest stories with no broader consequence, propaganda with no factual basis.

---

## Source Guide

Read each source with its bias in mind:

| Source | What it's good for | How to read it |
|--------|-------------------|----------------|
| **Wikipedia Current Events** | Editorial spine — what's significant | Trust the topic selection; verify claims against other sources |
| **Wikipedia — [YEAR] in science** | Science editorial spine — significant discoveries, missions, and findings by month | Same trust model as Current Events. URL pattern: `https://en.wikipedia.org/wiki/[YEAR]_in_science` — update year as the calendar turns |
| **NPR** | US domestic depth, Iran war context | Centrist US public media. Reliable on facts, tends to center US perspective |
| **ISW (Bluesky)** | Military ground truth on Ukraine and Iran war | Nonpartisan defense think tank. Strongest source for order of battle, territorial changes, operational analysis. Not opinion. |
| **Meduza** | Russia insider view, things Russians actually experience | Independent Russian journalism in exile. High credibility on domestic Russian stories — Telegram block, exile communities, war propaganda. |
| **FactCheck.org** | Specific false or misleading claims in circulation | Use to flag when a political claim is documented as false. Especially useful alongside Iran war coverage and US domestic politics. |
| **Global Times** | How China frames events | Chinese Communist Party-aligned tabloid. Read to understand Beijing's framing — not as neutral reporting. Note the spin explicitly when you use it. |
| **The Onion** | Cultural saturation signal | When The Onion jokes about something, it's reached mainstream cultural visibility. That's a data point about narrative saturation, not just a joke. |
| **Telegram (Meduza, Current Time, NEXTA)** | Russian and Belarusian ground-level signals | NEXTA covers Belarus. Current Time is RFE/RL's Russia service. Useful for things not yet in formal reporting. |
| **NASA APOD** | Daily space image + expert explanation | One image per day, selected by NASA scientists. Embed at the top of Science & Discovery. If it's a video day, describe it instead and link to the URL. |
| **Phys.org** | Science news before it hits mainstream press | Aggregates coverage of peer-reviewed research across physics, astronomy, Earth science, biology, tech. Good for finding discoveries 1-3 days before they're on NPR. |
| **The Conversation (US)** | Academic experts writing for general audiences | Peer-reviewed credibility, accessible prose. Use for context and analysis of science and society stories. Not news — depth. |

---

## Analysis Format

### File name
`analysis_YYYY-MM-DD.md` — use today's date.

### Document header
```
# Current Events Analysis — [DATE] · [TIME]
*Wikipedia-anchored briefing · Sources: wiki export + news export*

---
```

`[DATE]` is today's date (e.g. `2026-03-24`). `[TIME]` is the current time in 12-hour format with am/pm (e.g. `6:00am` or `4:30pm`). The pipeline passes the current datetime in the prompt — use whatever time is given there. If no time is provided, use the file modification time or omit the time portion.

### Each section
```
## [Topic Title from Wikipedia]
*[One sentence subtitle — the "what you need to know before reading" context]*

[Body paragraphs. Wikipedia events first, then depth from supplementary sources.
Cite every specific claim with a footnote [^N]. Keep paragraphs to 3-5 sentences.
Write for a reader who wants signal, not noise.]

> **KEY:** [The single most important insight in this section — something that reframes
> the story or explains the stakes. Not a summary — a genuine analytical insight.][^N]

[or]

> **WATCH:** [An event or pattern getting less coverage than its consequences deserve.
> Use this when something significant is being drowned out by bigger stories.][^N]
```

### Standard sections to include (when material exists)

1. **One section per major Wikipedia topic** — conflicts, elections, significant deaths, etc. Cover the 3-5 most consequential; don't exhaustively list everything.
2. **Other Consequential Events** — a single section for significant items that don't warrant their own full section. Use `**Bold label:**` format for sub-items.
3. **Science & Discovery** — one consolidated section covering significant developments in science, exploration, and engineering. See Science Coverage guidelines below.
4. **Dispatch from the Absurd** — one humor beat per analysis. Use the `> **ABSURD:**` callout. Find something genuinely funny — dark irony, absurd juxtaposition, a headline that lands wrong. The Center 795/Google Translate story (March 18 analysis) is a good example of the register.

### Callout box syntax (three types)

```
> **KEY:** [insight] — amber box, use for things the reader should not miss
> **WATCH:** [observation] — rust red box, use for undercovered significance
> **ABSURD:** [humor] — sage green box, use once per analysis for the humor beat
```

Only use `KEY` or `WATCH` once or twice per section maximum. They lose meaning if overused.

### Timeline blocks (optional, for major ongoing stories)

For sections covering large, multi-week ongoing events (wars, major political proceedings, economic crises), include a timeline block immediately after the one-sentence subtitle line and before the body paragraphs. Use the fenced `timeline` format:

```timeline [Wikipedia article name] | [Wikipedia article URL]
YYYY-MM-DD | Short event title | 1–3 sentence context note for the hover tooltip | Wikipedia URL for this event
YYYY-MM-DD | Short event title | 1–3 sentence context note | Wikipedia URL
```

**Example:**
```timeline 2026 Iran war | https://en.wikipedia.org/wiki/2026_Israel%E2%80%93Iran_war
2026-02-13 | US–Israel air campaign begins | After Iran's missile barrage strikes Haifa's port district, US and Israeli air forces launch coordinated strikes on IRGC infrastructure across western Iran. | https://en.wikipedia.org/wiki/2026_Israel%E2%80%93Iran_war
2026-02-19 | Iran threatens Hormuz closure | IRGC naval command announces it will mine the strait if strikes continue. Oil surges to $112/barrel. US Fifth Fleet repositions two carrier groups. | https://en.wikipedia.org/wiki/Strait_of_Hormuz
2026-03-24 | Trump declares victory; Israel says weeks remain | Trump posts "MISSION ACCOMPLISHED" as IDF says Iran's reconstitution capability requires 3–4 more weeks. ISW notes diverging timelines. | https://en.wikipedia.org/wiki/2026_Israel%E2%80%93Iran_war
```

**Rules:**
- Carry forward ALL previous entries each run — the timeline accumulates. Append new entries for today; do not remove old ones.
- Entries must be in chronological order, oldest first.
- Dates must be ISO format `YYYY-MM-DD` — the renderer uses them to mark "today" automatically.
- Every entry needs a Wikipedia URL. Use the main article URL if no specific sub-article exists.
- The entry URL (field 4) links from the hover tooltip — choose the most relevant Wikipedia page for that specific event.
- Use the main article URL in the header (field after the language tag) — this links from the timeline box header.
- Only include timelines for sections about major, multi-week ongoing stories. Do NOT include in: Science & Discovery, Dispatch from the Absurd, Other Consequential Events, or one-off single-day events.

### Footnotes

Every specific factual claim needs a footnote. Format:
- Inline: `[^1]` immediately after the claim, before punctuation if possible
- Definition (in Sources section at end): `[^1]: [Article Title](https://full-url)`

Number sequentially from 1. Put all definitions in a `## Sources` section at the end.

Wikipedia citations can point to the portal or the specific sub-article:
- `[^1]: [Wikipedia — Portal:Current Events](https://en.wikipedia.org/wiki/Portal:Current_events)`
- `[^2]: [Wikipedia — 2026 Iran war](https://en.wikipedia.org/wiki/2026_Iran_war)`

---

## Analytical Standards

**Lead with what's surprising or underreported.** The Iran war is obvious. The Pakistan-Afghanistan escalation in the same week, getting 1% of the coverage, is more interesting to surface.

**ISW is your best source for military/conflict ground truth.** When ISW's assessment conflicts with official statements, say so explicitly. Gerasimov claiming imminent Ukrainian collapse while ISW says the front is operationally stable is a story in itself.

**Flag the spin explicitly when using Global Times or state media.** Don't just quote it neutrally. "Global Times frames this as..." or "The Chinese state media position is..."

**FactCheck items are claims, not just corrections.** When FactCheck flags something, ask: what does it tell you about what the administration is trying to assert? That's the story, not just "claim was false."

**The Onion signal.** If The Onion ran something about a topic, note it in Dispatch from the Absurd and explain why it's a saturation signal — what it says about where that narrative has landed culturally.

**Don't inflate stakes with unverified claims.** If a story is significant, the real facts are sufficient. Before asserting a geopolitical fact in a callout — nuclear status, treaty membership, alliance standing, UN classification — pause and confirm it. These are exactly the claims readers are most likely to catch and least likely to forgive. The instinct to reach for an intensifier ("two nuclear powers") when the real situation is already alarming ("nuclear-armed state bombing a neighbor") is a sign to slow down, not speed up.

**Length.** A good analysis is 1,200–2,000 words in the body, plus sources. Long enough to be substantive; short enough to read in 20 minutes. The Science & Discovery section should not crowd out the news — keep it to 250–400 words unless a single story truly warrants more.

---

## Science Coverage

### The section format

```
## Science & Discovery
*[One sentence framing what makes this period notable in science]*

![NASA APOD — Title](https://apod.nasa.gov/apod/image/...)
*Title — Photographer/NASA*

**[Domain — e.g., Space, Geology, Anthropology, Engineering]:** [2–4 sentences.
What was found or built, why it matters to humans, what it changes or enables.
Lead with the discovery, not the institution that made it.]

**[Next domain]:** [Same structure.]

> **KEY:** [The single most significant finding this period — something that moves the ball
> forward in a meaningful way, not just "scientists discovered X".][^N]
```

**Always open the section with the NASA APOD image** when the `nasa_apod__apod.txt` file is present in the export. Copy the embed markdown exactly as written in that file's "Embed this in the analysis" block. If the day's APOD is a video, write a one-sentence description and link to the URL instead of embedding. Credit the photographer/institution on the caption line.

Use `**Bold label:**` format to separate domains within the section. You don't need a sub-item for every domain every day — only include what's actually newsworthy.

### Priority domains

Cover these when material exists, in this order — space leads:

1. **Space science and exploration** — missions, discoveries, new images, anything that expands what we know about the universe. This is the primary science focus. New discoveries get their own paragraph; don't bury them.
2. **Human health and medicine** — treatments, disease understanding, breakthroughs that change what's possible for patients
3. **Environmental and climate science** — findings that affect how we understand what's happening to the planet; actionable data, not just more bad news for its own sake
4. **Ancient human anthropology** — fossil finds, genetic analysis, discoveries that rewrite the human timeline or migration story
5. **Pacific Northwest geology** — seismic activity, Cascadia subduction zone research, volcanic monitoring (Mount Rainier, Hood, St. Helens, Baker), landslide risk. **Flag these even if small.** This region has outsized personal and civilizational stakes.
6. **Applied engineering and materials science** — things humans actually built that are surprising, elegant, or solve a hard problem in a new way
7. **Sociological patterns** — peer-reviewed findings about how humans actually behave, organize, or change; not trend pieces, actual data

### The science spine

**Wikipedia's "[YEAR] in science" article is the editorial authority for science**, the same way the Current Events portal is the authority for news. It is curated, chronological, and already filtered for significance. Start there. Anchor science items to things that appear on that page.

URL pattern: `https://en.wikipedia.org/wiki/2026_in_science` — update the year as the calendar turns.

The broader Wikipedia exception still applies: significant peer-reviewed findings, mission milestones, and major geological events belong even if the "in science" page hasn't caught up yet — it sometimes lags by days. The bar is still high: *does this change something, enable something, or reveal something that wasn't known before?* A new study confirming what we already knew doesn't clear it. A find that rewrites a timeline or opens a new treatment path does.

### Tone

Write about science the way you'd explain it to a curious, smart non-specialist. Skip jargon unless you define it. The question to answer is always: *so what does this mean for humans?* — whether that's "we can now treat X" or "we now know our ancestors crossed Y 10,000 years earlier than we thought" or "the Cascadia fault shows a new behavior pattern that changes the risk model."

---

## What a Good Analysis Looks Like

See `analysis_2026-03-18.md` in this folder for the first full example.

Key things it does right:
- Every section leads with the Wikipedia event, then adds depth
- ISW's strategic trap insight (Iran war section) is the kind of thing that doesn't appear in mainstream coverage — that's what the KEY callout is for
- Afghanistan-Pakistan gets a WATCH callout because it's being buried by Iran coverage
- The Center 795/Google Translate story is the Absurd beat — dark, genuinely funny, says something about the Russian state
- The Best Picture title (*One Battle After Another*) as an unintentional perfect description of the Iran war is the kind of lateral observation that makes analysis worth reading

---

## After Writing

1. Save `analysis_YYYY-MM-DD.md` to this folder
2. Tell the user it's ready and they can run `python3 view_export.py` to see it in the browser
3. Do not commit to git unless asked — the user may want to review first

---

## Running the scrapers (reference)

Three scraper runs for a full daily brief:

```bash
# Current events (news spine)
python3 wiki_scraper.py

# Science spine — update year when calendar turns
python3 wiki_scraper.py https://en.wikipedia.org/wiki/2026_in_science

# News + science sources (NASA APOD, Phys.org, The Conversation included by default)
python3 news_scraper.py
```

To run science sources only (faster, useful if you just want to refresh science content):
```bash
python3 news_scraper.py --sources science
```

Then tell Claude: *"analyze the latest wiki and news exports"*
