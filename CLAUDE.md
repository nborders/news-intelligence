# CLAUDE.md — News Intelligence Workflow

This folder contains a Wikipedia-anchored current events analysis workflow.
When asked to "analyze the latest wiki and news exports," follow everything below exactly.

---

## Your Job

Read the zip files in this folder, write a `analysis_YYYY-MM-DD.md` file, and save it here.
Do not open a browser or run `view_export.py` — the user does that themselves.

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
| **Wikipedia** | Editorial spine — what's significant | Trust the topic selection; verify claims against other sources |
| **NPR** | US domestic depth, Iran war context | Centrist US public media. Reliable on facts, tends to center US perspective |
| **ISW (Bluesky)** | Military ground truth on Ukraine and Iran war | Nonpartisan defense think tank. Strongest source for order of battle, territorial changes, operational analysis. Not opinion. |
| **Meduza** | Russia insider view, things Russians actually experience | Independent Russian journalism in exile. High credibility on domestic Russian stories — Telegram block, exile communities, war propaganda. |
| **FactCheck.org** | Specific false or misleading claims in circulation | Use to flag when a political claim is documented as false. Especially useful alongside Iran war coverage and US domestic politics. |
| **Global Times** | How China frames events | Chinese Communist Party-aligned tabloid. Read to understand Beijing's framing — not as neutral reporting. Note the spin explicitly when you use it. |
| **The Onion** | Cultural saturation signal | When The Onion jokes about something, it's reached mainstream cultural visibility. That's a data point about narrative saturation, not just a joke. |
| **Telegram (Meduza, Current Time, NEXTA)** | Russian and Belarusian ground-level signals | NEXTA covers Belarus. Current Time is RFE/RL's Russia service. Useful for things not yet in formal reporting. |

---

## Analysis Format

### File name
`analysis_YYYY-MM-DD.md` — use today's date.

### Document header
```
# Current Events Analysis — [DATE]
*Wikipedia-anchored briefing · Sources: wiki export + news export*

---
```

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
3. **Dispatch from the Absurd** — one humor beat per analysis. Use the `> **ABSURD:**` callout. Find something genuinely funny — dark irony, absurd juxtaposition, a headline that lands wrong. The Center 795/Google Translate story (March 18 analysis) is a good example of the register.

### Callout box syntax (three types)

```
> **KEY:** [insight] — amber box, use for things the reader should not miss
> **WATCH:** [observation] — rust red box, use for undercovered significance
> **ABSURD:** [humor] — sage green box, use once per analysis for the humor beat
```

Only use `KEY` or `WATCH` once or twice per section maximum. They lose meaning if overused.

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

**Length.** A good analysis is 1,000–1,800 words in the body, plus sources. Long enough to be substantive; short enough to read in 15 minutes.

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
