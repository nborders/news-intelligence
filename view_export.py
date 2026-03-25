#!/usr/bin/env python3
"""
Export Viewer
=============
Renders a Claude analysis markdown file (or raw zip) as a self-contained
HTML page and opens it in your browser.

PRIMARY USE — render a Claude-written analysis with footnotes:
    python3 view_export.py                         # auto-finds latest analysis_*.md
    python3 view_export.py analysis_2026-03-13.md  # specific analysis file

SECONDARY USE — browse raw scraped zip content:
    python3 view_export.py news_export.zip
    python3 view_export.py Portal_Current_events_export.zip

Analysis markdown format:
    Body text uses [^1] for inline footnote markers.
    Sources section uses [^1]: [Title](URL) for definitions.
    Images: ![Caption](https://...) — loaded from source URL
    Videos: [VIDEO: Title](https://youtube.com/...)
    Audio:  [AUDIO: Title](https://...)
    See analysis_template.md for a full example.

No dependencies beyond the standard library.
"""

import argparse
import html
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()

# ─── Shared CSS ────────────────────────────────────────────────────────────────

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Lexend:wght@300;400;500;600;700;800;900&display=swap');
* { box-sizing: border-box; margin: 0; padding: 0; }

/* ── Night mode / earth tone palette ──────────────────────────────────────
   Background : #1a1714  (very dark warm brown — like a dim reading lamp)
   Surface    : #242019  (slightly lighter, for callout boxes)
   Text       : #e8dfc8  (warm cream — high contrast, not harsh white)
   Muted      : #8a7f6a  (earth mid-tone for labels/meta)
   Amber      : #c98a2e  (heading accent)
   Rust       : #b84a2a  (WATCH callout)
   Sage       : #7a9a40  (ABSURD/humor callout)
   Sky        : #6eadd4  (links — readable blue on dark)
   ──────────────────────────────────────────────────────────────────────── */

body {
  font-family: Lexend, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: #1a1714; color: #e8dfc8; font-size: 19px; line-height: 2.0;
  letter-spacing: 0.12em;
  word-spacing: 0.16em;
}

/* ── Sidebar ──────────────────────────────────────────────────────────── */
#sidebar {
  position: fixed; top: 0; left: 0; bottom: 0; width: 256px;
  background: #100e0c; color: #b8aa90; overflow-y: auto; padding: 20px 0;
  border-right: 1px solid #302820;
}
#sidebar h2 {
  font-size: 10px; text-transform: uppercase; letter-spacing: .12em;
  color: #5a5040; padding: 0 18px 10px;
}
#sidebar a {
  display: block; padding: 7px 18px; color: #b8aa90;
  text-decoration: none; font-size: 13px; line-height: 1.5;
  border-left: 4px solid transparent;
}
#sidebar a:hover { background: #1e1a14; border-left-color: #c98a2e; color: #e8dfc8; }
#sidebar .section-link { font-weight: 700; margin-top: 8px; }
#sidebar .sub-link { padding-left: 30px; color: #7a6e58; font-size: 12px; }

/* ── Main content ─────────────────────────────────────────────────────── */
#main { margin-left: 256px; padding: 0 56px 64px; max-width: 820px; }

/* ── Masthead (h1 + meta) — visually separate from all other content ── */
.masthead {
  padding: 44px 0 28px;
  border-bottom: 3px solid #c98a2e;
  margin-bottom: 48px;
}
.masthead h1 {
  font-size: 38px; font-weight: 900; color: #f5ecd5;
  line-height: 1.15; letter-spacing: -0.02em;
  text-shadow: 0 1px 8px rgba(0,0,0,.4);
}
/* Decorative rule above the title */
.masthead::before {
  content: "";
  display: block;
  width: 56px; height: 4px;
  background: #c98a2e;
  border-radius: 2px;
  margin-bottom: 18px;
}
.masthead .meta {
  color: #8a7f6a; font-size: 14px; margin-top: 10px; line-height: 1.6;
  letter-spacing: 0.03em; text-transform: uppercase;
}

/* Legacy .meta outside masthead */
.meta { color: #8a7f6a; font-size: 14px; margin-bottom: 36px; line-height: 1.6; }

/* Section headings: dark amber left-bar on a warm surface */
h2 {
  font-size: 22px; font-weight: 800; margin: 48px 0 4px;
  padding: 10px 16px; color: #f0dfb0;
  background: #231f18;
  border-left: 6px solid #c98a2e;
  border-radius: 0 6px 6px 0;
  line-height: 1.35;
}
/* Subtitle: muted descriptor immediately after h2 */
.subtitle {
  font-size: 15px; color: #8a7f6a; font-style: italic;
  margin: 4px 0 20px 22px; line-height: 1.5;
}

h3 {
  font-size: 18px; font-weight: 700; margin: 28px 0 8px;
  color: #d4b87a;
}
p { margin-bottom: 18px; }
hr { border: none; border-top: 1px solid #302820; margin: 36px 0; }
a { color: #6eadd4; }
a:hover { text-decoration: underline; color: #9ac8e8; }
sup a {
  color: #c98a2e; font-size: 12px; font-weight: 700;
  text-decoration: none; padding: 0 2px;
}
sup a:hover { text-decoration: underline; color: #e8a84e; }

/* ── Inline images ────────────────────────────────────────────────────── */
figure.inline-img {
  margin: 24px 0; border-radius: 8px; overflow: hidden;
  background: #100e0c; border: 1px solid #302820;
}
figure.inline-img img {
  display: block; width: 100%; max-height: 420px;
  object-fit: cover; object-position: top;
}
figure.inline-img figcaption {
  font-size: 13px; color: #8a7f6a; padding: 8px 14px;
  font-style: italic; line-height: 1.5;
}

/* ── Video / audio buttons ────────────────────────────────────────────── */
.watch-btn {
  display: inline-flex; align-items: center; gap: 8px;
  background: #1e1a14; border: 1px solid #5a4a2a;
  color: #c98a2e; font-size: 14px; font-weight: 600;
  padding: 7px 14px; border-radius: 6px; cursor: pointer;
  text-decoration: none; transition: background .15s, border-color .15s;
  margin: 4px 0;
}
.watch-btn:hover {
  background: #2a2010; border-color: #c98a2e; color: #e8b84e;
  text-decoration: none;
}
.watch-btn .btn-icon { font-size: 16px; }

/* ── Video modal ──────────────────────────────────────────────────────── */
#video-modal {
  display: none; position: fixed; inset: 0; z-index: 9000;
  background: rgba(0,0,0,.82);
  align-items: center; justify-content: center;
}
#video-modal.open { display: flex; }
.modal-box {
  position: relative; width: 854px; max-width: 92vw;
  border-radius: 10px; overflow: hidden;
  background: #0a0806; border: 1px solid #302820;
  box-shadow: 0 24px 80px rgba(0,0,0,.8);
}
.modal-box .ratio { position: relative; padding-top: 56.25%; }
.modal-box iframe, .modal-box audio {
  position: absolute; inset: 0; width: 100%; height: 100%; border: none;
}
.modal-box audio { height: auto; top: auto; bottom: 0; padding: 20px; }
.modal-close {
  position: absolute; top: 10px; right: 12px; z-index: 10;
  background: rgba(0,0,0,.6); color: #e8dfc8; border: none;
  font-size: 20px; width: 34px; height: 34px; border-radius: 50%;
  cursor: pointer; line-height: 34px; text-align: center;
  transition: background .15s;
}
.modal-close:hover { background: rgba(201,138,46,.4); }

/* ── Callout boxes ────────────────────────────────────────────────────── */

/* Standard blockquote — muted context */
blockquote {
  border-left: 5px solid #4a6a8a; margin: 18px 0;
  padding: 10px 20px; background: #1e2028; color: #b0c0d0;
  font-style: italic; border-radius: 0 6px 6px 0;
}

/* KEY POINT — amber, "you should notice this" */
blockquote.key-point {
  border-left-color: #c98a2e; background: #2a2010;
  color: #f0dfb0; font-style: normal; font-size: 18px;
}
blockquote.key-point strong.label {
  display: block; font-size: 11px; text-transform: uppercase;
  letter-spacing: .12em; color: #c98a2e; margin-bottom: 6px;
}

/* WATCH — rust red, "this matters more than coverage suggests" */
blockquote.watch {
  border-left-color: #b84a2a; background: #271410;
  color: #f0cfc0; font-style: normal;
}
blockquote.watch strong.label {
  display: block; font-size: 11px; text-transform: uppercase;
  letter-spacing: .12em; color: #d0603a; margin-bottom: 6px;
}

/* ABSURD — sage green, humor */
blockquote.absurd {
  border-left-color: #7a9a40; background: #1a2010;
  color: #cce0a8; font-style: normal;
}
blockquote.absurd strong.label {
  display: block; font-size: 11px; text-transform: uppercase;
  letter-spacing: .12em; color: #7a9a40; margin-bottom: 6px;
}

/* ── Footnotes ────────────────────────────────────────────────────────── */
.footnotes {
  margin-top: 48px; padding-top: 24px; border-top: 1px solid #302820;
}
.footnotes h2 {
  border: none; margin-top: 0; font-size: 13px; color: #5a5040;
  background: none; padding: 0; letter-spacing: .08em; text-transform: uppercase;
}
.footnotes ol { padding-left: 22px; margin-top: 12px; }
.footnotes li {
  font-size: 14px; color: #8a7f6a; margin-bottom: 8px;
  padding-left: 4px; line-height: 1.6;
}
.footnotes li a { color: #6eadd4; }
.backref {
  font-size: 12px; margin-left: 8px;
  text-decoration: none !important; color: #5a5040;
}
.backref:hover { color: #c98a2e; }
strong { font-weight: 700; }
em { font-style: italic; }

/* ── Footnote hover tooltip ───────────────────────────────────────────── */
#fn-tooltip {
  display: none; position: absolute;
  background: #1e1a10; border: 1px solid #c98a2e;
  color: #f0dfb0; padding: 7px 14px;
  border-radius: 6px; font-size: 13px; font-style: normal;
  white-space: nowrap; max-width: 520px;
  overflow: hidden; text-overflow: ellipsis;
  z-index: 8000; pointer-events: auto;
  box-shadow: 0 4px 20px rgba(0,0,0,.6);
  line-height: 1.5;
}
#fn-tooltip a { color: #c98a2e; text-decoration: none; }
#fn-tooltip a:hover { text-decoration: underline; color: #e8a84e; }
#fn-tooltip .tip-num {
  font-weight: 700; color: #8a7f6a; margin-right: 6px;
}

@media (max-width: 760px) {
  #sidebar { display: none; }
  #main { margin-left: 0; padding: 24px 20px 64px; }
  .masthead { padding: 28px 0 20px; }
  .masthead h1 { font-size: 26px; }
}
"""

# ─── JavaScript ───────────────────────────────────────────────────────────────

def build_js(fn_defs: dict) -> str:
    fn_json = json.dumps({
        k: {"title": t, "url": u}
        for k, (t, u) in fn_defs.items()
    })
    return f"""
<script>
// ── Footnote hover tooltips ─────────────────────────────────────────────
const FN_DATA = {fn_json};
let _tipTimeout;
const _tip = document.getElementById('fn-tooltip');

function _showTip(anchor) {{
  clearTimeout(_tipTimeout);
  const key = anchor.dataset.fnKey;
  const fn = FN_DATA[key];
  if (!fn) return;
  const num = '<span class="tip-num">[' + key + ']</span>';
  _tip.innerHTML = fn.url
    ? num + '<a href="' + fn.url + '" target="_blank" rel="noopener">' + _esc(fn.title) + ' ↗</a>'
    : num + _esc(fn.title);
  _tip.style.display = 'block';
  // Position: above and left-aligned to anchor
  const r = anchor.getBoundingClientRect();
  const tipW = Math.min(520, _tip.scrollWidth + 30);
  let left = r.left + window.scrollX;
  if (left + tipW > window.innerWidth - 16) left = window.innerWidth - tipW - 16;
  _tip.style.left = Math.max(8, left) + 'px';
  _tip.style.top  = (r.top + window.scrollY - _tip.offsetHeight - 10) + 'px';
}}

function _hideTip() {{
  _tipTimeout = setTimeout(() => {{ _tip.style.display = 'none'; }}, 180);
}}

function _esc(s) {{
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}}

document.querySelectorAll('.fn-ref').forEach(el => {{
  el.addEventListener('mouseenter', () => _showTip(el));
  el.addEventListener('mouseleave', _hideTip);
}});
_tip.addEventListener('mouseenter', () => clearTimeout(_tipTimeout));
_tip.addEventListener('mouseleave', _hideTip);

// ── Video modal ─────────────────────────────────────────────────────────
const _modal     = document.getElementById('video-modal');
const _modalIframe = document.getElementById('modal-iframe');
const _modalAudio  = document.getElementById('modal-audio');

function openMedia(url, type) {{
  if (type === 'audio') {{
    _modalIframe.style.display = 'none';
    _modalAudio.style.display  = 'block';
    _modalAudio.src = url;
    _modalAudio.play();
  }} else {{
    _modalIframe.style.display = 'block';
    _modalAudio.style.display  = 'none';
    _modalIframe.src = url;
  }}
  _modal.classList.add('open');
  document.body.style.overflow = 'hidden';
}}

function closeMedia() {{
  _modal.classList.remove('open');
  _modalIframe.src = '';
  _modalAudio.pause();
  _modalAudio.src  = '';
  document.body.style.overflow = '';
}}

_modal.addEventListener('click', e => {{
  if (e.target === _modal) closeMedia();
}});
document.addEventListener('keydown', e => {{
  if (e.key === 'Escape') closeMedia();
}});
</script>
"""


# ─── Helpers ──────────────────────────────────────────────────────────────────

def youtube_embed(url: str) -> str | None:
    """Return YouTube embed URL if url is a YouTube link, else None."""
    m = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/)([A-Za-z0-9_-]{11})', url)
    if m:
        return f"https://www.youtube.com/embed/{m.group(1)}?rel=0"
    return None


def is_audio_url(url: str) -> bool:
    return bool(re.search(r'\.(mp3|ogg|wav|m4a|aac)(\?|$)', url, re.I))


def make_watch_btn(label: str, url: str) -> str:
    embed = youtube_embed(url)
    if embed:
        safe_embed = html.escape(embed)
        return (f'<button class="watch-btn" onclick="openMedia(\'{safe_embed}\',\'video\')">'
                f'<span class="btn-icon">▶</span>{html.escape(label)}</button>')
    if is_audio_url(url):
        safe_url = html.escape(url)
        return (f'<button class="watch-btn" onclick="openMedia(\'{safe_url}\',\'audio\')">'
                f'<span class="btn-icon">♪</span>{html.escape(label)}</button>')
    # Fallback: open in new tab
    return (f'<a class="watch-btn" href="{html.escape(url)}" target="_blank" rel="noopener">'
            f'<span class="btn-icon">▶</span>{html.escape(label)}</a>')


# ─── Analysis markdown renderer ───────────────────────────────────────────────

def parse_footnote_defs(lines: list[str]) -> dict[str, tuple[str, str]]:
    """
    Extract footnote definitions of the form:
        [^N]: [Title](URL)
        [^N]: Plain text description
    Returns {N: (display_text, url_or_empty)}
    """
    defs = {}
    for line in lines:
        m = re.match(r'^\[\^(\w+)\]:\s*(.*)', line)
        if m:
            key = m.group(1)
            rest = m.group(2).strip()
            lm = re.match(r'^\[([^\]]+)\]\((https?://[^)]+)\)', rest)
            if lm:
                defs[key] = (lm.group(1), lm.group(2))
            else:
                defs[key] = (rest, "")
    return defs


def inline_md(text: str, fn_defs: dict) -> str:
    """Convert inline markdown (bold, italic, links, footnote refs, images) to HTML."""

    # Inline images: ![alt](url)  — rendered as <img>
    text = re.sub(
        r'!\[([^\]]*)\]\((https?://[^)]+)\)',
        lambda m: f'<img src="{m.group(2)}" alt="{html.escape(m.group(1))}" '
                  f'style="max-width:100%;border-radius:4px;" loading="lazy">',
        text
    )

    # VIDEO: links → watch button
    text = re.sub(
        r'\[VIDEO:\s*([^\]]+)\]\((https?://[^)]+)\)',
        lambda m: make_watch_btn(m.group(1).strip(), m.group(2)),
        text
    )

    # AUDIO: links → watch button
    text = re.sub(
        r'\[AUDIO:\s*([^\]]+)\]\((https?://[^)]+)\)',
        lambda m: make_watch_btn(m.group(1).strip(), m.group(2)),
        text
    )

    # Footnote references [^N] → superscript links with data attributes for tooltip
    def fn_ref(m):
        key = m.group(1)
        if key in fn_defs:
            title, url = fn_defs[key]
            dt = html.escape(title, quote=True)
            du = html.escape(url, quote=True)
            return (f'<sup><a class="fn-ref" href="#fn-{key}" id="ref-{key}" '
                    f'data-fn-key="{key}" data-title="{dt}" data-url="{du}">[{key}]</a></sup>')
        return f'<sup><a href="#fn-{key}" id="ref-{key}">[{key}]</a></sup>'
    text = re.sub(r'\[\^(\w+)\]', fn_ref, text)

    # Markdown links [text](url)
    text = re.sub(
        r'\[([^\]]+)\]\((https?://[^)]+)\)',
        lambda m: f'<a href="{m.group(2)}" target="_blank" rel="noopener">{html.escape(m.group(1))}</a>',
        text
    )

    # Bold **text** and __text__
    text = re.sub(r'\*\*(.+?)\*\*|__(.+?)__',
                  lambda m: f'<strong>{m.group(1) or m.group(2)}</strong>', text)

    # Italic *text* and _text_
    text = re.sub(r'\*(.+?)\*|_(.+?)_',
                  lambda m: f'<em>{m.group(1) or m.group(2)}</em>', text)

    return text


def render_analysis(md_path: Path) -> Path:
    """
    Parse a Claude analysis markdown file and render it as annotated HTML
    with a sidebar, clickable footnotes, hover tooltips, images, and video modal.
    """
    raw = md_path.read_text(encoding="utf-8")
    lines = raw.splitlines()

    fn_defs = parse_footnote_defs(lines)

    # ── First pass: collect section headings for sidebar ──
    sections = []
    for line in lines:
        if line.startswith("## ") and not line.startswith("## Sources"):
            sections.append(line[3:].strip())

    nav_links = "\n".join(
        f'<a class="section-link" href="#{slugify(s)}">{html.escape(s)}</a>'
        for s in sections
    )

    # ── Second pass: render body ──
    body_html = []
    in_footnote_section = False
    fn_items = []
    paragraph_buf = []

    # Regex: a line that is ONLY a block image: ![alt](url)
    BLOCK_IMAGE_RE = re.compile(r'^\s*!\[([^\]]*)\]\((https?://[^)]+)\)\s*$')
    # Regex: VIDEO or AUDIO block line
    BLOCK_VIDEO_RE = re.compile(r'^\s*\[(VIDEO|AUDIO):\s*([^\]]+)\]\((https?://[^)]+)\)\s*$')

    def flush_paragraph():
        if paragraph_buf:
            joined = " ".join(paragraph_buf).strip()
            if joined:
                body_html.append(f'<p>{inline_md(html.escape(joined), fn_defs)}</p>')
            paragraph_buf.clear()

    page_title = "Current Events Analysis"
    meta_line = ""

    for line in lines:
        # Skip footnote definition lines from body (handled separately)
        if re.match(r'^\[\^\w+\]:', line):
            continue

        if line.startswith("## Sources") or line.startswith("## Footnotes"):
            in_footnote_section = True
            flush_paragraph()
            continue

        if in_footnote_section:
            continue

        # Block-level image: a line that is only ![alt](url)
        bim = BLOCK_IMAGE_RE.match(line)
        if bim and not in_footnote_section:
            flush_paragraph()
            alt = html.escape(bim.group(1))
            src = html.escape(bim.group(2))
            body_html.append(
                f'<figure class="inline-img">'
                f'<img src="{src}" alt="{alt}" loading="lazy">'
                + (f'<figcaption>{alt}</figcaption>' if alt else '')
                + '</figure>'
            )
            continue

        # Block-level video/audio
        bvm = BLOCK_VIDEO_RE.match(line)
        if bvm and not in_footnote_section:
            flush_paragraph()
            kind  = bvm.group(1)
            label = bvm.group(2).strip()
            url   = bvm.group(3)
            body_html.append(f'<p>{make_watch_btn(label, url)}</p>')
            continue

        if line.startswith("# "):
            flush_paragraph()
            page_title = line[2:].strip()
            # h1 is handled in the masthead block below, skip here
            continue

        elif line.startswith("## "):
            flush_paragraph()
            heading = line[3:].strip()
            sid = slugify(heading)
            body_html.append(f'<h2 id="{sid}">{html.escape(heading)}</h2>')
            body_html.append("__SUBTITLE_SLOT__")

        elif line.startswith("### "):
            flush_paragraph()
            heading = line[4:].strip()
            body_html.append(f'<h3>{html.escape(heading)}</h3>')

        elif line.startswith("---"):
            flush_paragraph()
            body_html.append("<hr>")

        elif line.startswith("> "):
            flush_paragraph()
            content = line[2:].strip()
            key_m = re.match(r'^\*\*(KEY|WATCH|ABSURD):\*\*\s*(.*)', content, re.IGNORECASE)
            if key_m:
                kw = key_m.group(1).upper()
                rest = key_m.group(2).strip()
                css_class = {"KEY": "key-point", "WATCH": "watch", "ABSURD": "absurd"}[kw]
                label = {"KEY": "Key Point", "WATCH": "Watch", "ABSURD": "Dispatch from the Absurd"}[kw]
                inner = f'<strong class="label">{label}</strong>{inline_md(html.escape(rest), fn_defs)}'
                body_html.append(f'<blockquote class="{css_class}">{inner}</blockquote>')
            else:
                body_html.append(
                    f'<blockquote>{inline_md(html.escape(content), fn_defs)}</blockquote>'
                )

        elif line.strip() == "":
            flush_paragraph()

        else:
            stripped = line.strip()
            # Subtitle: italic line (*…*) immediately after an h2 slot
            if (stripped.startswith("*") and stripped.endswith("*")
                    and not stripped.startswith("**")
                    and body_html and body_html[-1] == "__SUBTITLE_SLOT__"):
                body_html[-1] = f'<p class="subtitle">{html.escape(stripped.strip("*").strip())}</p>'
            else:
                if body_html and body_html[-1] == "__SUBTITLE_SLOT__":
                    body_html[-1] = ""
                paragraph_buf.append(stripped)

    flush_paragraph()
    body_html = [x for x in body_html if x != "__SUBTITLE_SLOT__"]

    # ── Build footnotes section ──
    if fn_defs:
        fn_html = ['<div class="footnotes"><h2>Sources</h2><ol>']
        for key in sorted(fn_defs.keys(), key=lambda k: int(k) if k.isdigit() else 0):
            text, url = fn_defs[key]
            if url:
                link = f'<a href="{url}" target="_blank" rel="noopener">{html.escape(text)}</a>'
            else:
                link = html.escape(text)
            backref = f'<a class="backref" href="#ref-{key}">↩</a>'
            fn_html.append(f'<li id="fn-{key}">{link}{backref}</li>')
        fn_html.append("</ol></div>")
        body_html.extend(fn_html)

    # ── Extract meta line from first lines ──
    for line in lines[:5]:
        if line.startswith("*") and line.endswith("*") and not line.startswith("**"):
            meta_line = line.strip("*").strip()
            break

    # ── Assemble page ──
    masthead = f"""<div class="masthead">
  <h1>{html.escape(page_title)}</h1>
  {'<p class="meta">' + html.escape(meta_line) + '</p>' if meta_line else ''}
</div>"""

    modal = """
<div id="video-modal">
  <div class="modal-box">
    <button class="modal-close" onclick="closeMedia()">✕</button>
    <div class="ratio">
      <iframe id="modal-iframe" src="" allowfullscreen allow="autoplay"></iframe>
      <audio id="modal-audio" src="" controls style="display:none"></audio>
    </div>
  </div>
</div>"""

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(page_title)}</title>
<style>{CSS}</style>
</head>
<body>
<div id="fn-tooltip"></div>
{modal}
<nav id="sidebar">
  <h2>Sections</h2>
  {nav_links}
</nav>
<div id="main">
  {masthead}
  {''.join(body_html)}
</div>
{build_js(fn_defs)}
</body>
</html>"""

    out_path = md_path.with_suffix(".html")
    out_path.write_text(page, encoding="utf-8")
    return out_path


def slugify(text: str) -> str:
    return re.sub(r'[^\w]+', '-', text.lower()).strip('-')


# ─── Raw zip browser ──────────────────────────────────────────────────────────

ZIP_CSS = CSS + """
.source-section {
  background: white; border-radius: 10px; margin-bottom: 28px;
  box-shadow: 0 1px 4px rgba(0,0,0,.08); overflow: hidden;
}
.source-header {
  background: #1e2330; color: white; padding: 14px 20px;
}
.source-header h2 { font-size: 15px; font-weight: 600; }
.source-note { font-size: 11px; color: #a0a8c0; margin-top: 3px; font-style: italic; }
.article { padding: 16px 20px; border-top: 1px solid #f0f0f0; }
.article h3 { font-size: 15px; font-weight: 600; margin-bottom: 4px; }
.article h3 a { color: inherit; text-decoration: none; }
.article h3 a:hover { text-decoration: underline; color: #4060c0; }
.article .meta { font-size: 12px; color: #888; margin-bottom: 8px; }
.article .body { font-size: 14px; color: #333; white-space: pre-wrap; }
.post { padding: 14px 20px; border-top: 1px solid #f0f0f0; }
.post .ts { font-size: 11px; color: #aaa; margin-bottom: 4px; }
.post .text { font-size: 14px; color: #333; white-space: pre-wrap; }
.empty { padding: 20px; color: #888; font-style: italic; font-size: 14px; }
"""

def build_zip_html(zip_path: Path) -> Path:
    """Render raw zip contents as a browseable HTML page."""
    sections = []
    nav_items = []

    with zipfile.ZipFile(zip_path) as zf:
        names = sorted(zf.namelist())
        content_files = [n for n in names
                         if n.endswith(".txt") and "MANIFEST" not in n and "__META" not in n]

        for name in content_files:
            text = zf.read(name).decode("utf-8", errors="replace")
            anchor = re.sub(r'[^\w]', '_', name.replace('.txt',''))
            label  = name.replace(".txt","").replace("__"," · ").replace("_"," ")
            nav_items.append(f'<a href="#{anchor}">{html.escape(label)}</a>')

            lines = text.splitlines()
            title = lines[0][2:].strip() if lines and lines[0].startswith("# ") else label
            note  = next((l.split(":",1)[1].strip() for l in lines[:8] if l.startswith("Perspective:")), "")

            items_html = ""
            is_posts = bool(re.search(r'\[20\d\d-\d\d-\d\d', text)) and "Posts:" in text

            if is_posts:
                for m in re.finditer(r'---\s*\[([^\]]*)\]\s*(https?\S*)?\n(.*?)(?=\n---|$)', text, re.DOTALL):
                    ts, url, body = m.group(1), (m.group(2) or "").strip(), m.group(3).strip()
                    link = f'<a href="{html.escape(url)}" target="_blank">↗</a>' if url else ""
                    items_html += (f'<div class="post"><div class="ts">{html.escape(ts)} {link}</div>'
                                   f'<div class="text">{html.escape(body[:500])}</div></div>')
            else:
                current_title = current_url = current_date = ""
                body_lines = []
                def emit_article():
                    nonlocal items_html, current_title, current_url, current_date, body_lines
                    if current_title:
                        body_text = "\n".join(body_lines).strip()[:600]
                        link = f'<a href="{html.escape(current_url)}" target="_blank">{html.escape(current_title)}</a>' if current_url else html.escape(current_title)
                        items_html += (f'<div class="article"><h3>{link}</h3>'
                                       + (f'<div class="meta">{html.escape(current_date)}</div>' if current_date else "")
                                       + (f'<div class="body">{html.escape(body_text)}</div>' if body_text else "")
                                       + '</div>')
                    current_title = current_url = current_date = ""
                    body_lines = []
                for line in lines:
                    if line.startswith("## "):
                        emit_article()
                        current_title = line[3:].strip()
                    elif line.startswith("URL:"):
                        current_url = line.split(":",1)[1].strip()
                    elif line.startswith("Date:"):
                        current_date = line.split(":",1)[1].strip()
                    elif current_title and not line.startswith("#"):
                        body_lines.append(line)
                emit_article()

            if not items_html:
                items_html = '<div class="empty">No content found.</div>'

            note_html = f'<div class="source-note">{html.escape(note)}</div>' if note else ""
            sections.append(
                f'<div class="source-section" id="{anchor}">'
                f'<div class="source-header"><h2>{html.escape(title)}</h2>{note_html}</div>'
                f'{items_html}</div>'
            )

    nav_html = "\n".join(nav_items)
    page = f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8">
<title>{html.escape(zip_path.stem)}</title>
<style>{ZIP_CSS}</style>
</head>
<body>
<nav id="sidebar"><h2>Sources</h2>{nav_html}</nav>
<div id="main">
<h1>{html.escape(zip_path.stem.replace('_',' ').title())}</h1>
<p class="meta">Raw export — {zip_path.name}</p>
{''.join(sections)}
</div></body></html>"""

    out = zip_path.parent / (zip_path.stem + "_view.html")
    out.write_text(page, encoding="utf-8")
    return out


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="View a Claude analysis or raw news/wiki export in your browser."
    )
    parser.add_argument(
        "file", nargs="?",
        help="analysis_*.md or export.zip (default: auto-finds latest analysis, then latest zip)"
    )
    parser.add_argument("--no-open", action="store_true", help="Generate HTML without opening browser")
    args = parser.parse_args()

    if args.file:
        path = SCRIPT_DIR / args.file if not Path(args.file).is_absolute() else Path(args.file)
    else:
        analyses = sorted(SCRIPT_DIR.glob("analysis_*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
        zips     = sorted(SCRIPT_DIR.glob("*.zip"),         key=lambda p: p.stat().st_mtime, reverse=True)
        path = analyses[0] if analyses else (zips[0] if zips else None)

    if not path or not path.exists():
        print("No analysis file or zip found in this folder.")
        sys.exit(1)

    print(f"Reading: {path.name}")

    if path.suffix == ".md":
        out = render_analysis(path)
    else:
        out = build_zip_html(path)

    print(f"Generated: {out.name}")

    if not args.no_open:
        subprocess.run(["open", str(out)])
        print("Opening in browser...")


if __name__ == "__main__":
    main()
