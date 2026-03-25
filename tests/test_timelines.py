"""Tests for render_timeline() in view_export.py"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import datetime
from unittest.mock import patch
from view_export import render_timeline

FIXED_TODAY = "2026-03-24"

def _render(lang_line, lines):
    """Render with today fixed to 2026-03-24."""
    with patch("view_export.datetime") as mock_dt:
        mock_dt.date.today.return_value = datetime.date(2026, 3, 24)
        mock_dt.date.fromisoformat.side_effect = datetime.date.fromisoformat
        return render_timeline(lang_line, lines)

def test_header_article_name_and_wiki_link():
    html = _render(
        "timeline 2026 Iran war | https://en.wikipedia.org/wiki/2026_Iran_war",
        ["2026-02-13 | Campaign begins | Some note | https://en.wikipedia.org/wiki/2026_Iran_war"]
    )
    assert "Timeline · 2026 Iran war" in html
    assert 'href="https://en.wikipedia.org/wiki/2026_Iran_war"' in html
    assert "tl-wiki" in html

def test_entry_renders_date_and_title():
    html = _render(
        "timeline Test | https://en.wikipedia.org/wiki/Test",
        ["2026-02-13 | Campaign begins | A note | https://en.wikipedia.org/wiki/Test"]
    )
    assert "Feb 13" in html
    assert "Campaign begins" in html
    assert 'class="vtl-date"' in html
    assert 'class="vtl-event"' in html

def test_today_entry_gets_today_class_and_marker():
    html = _render(
        "timeline Test | https://en.wikipedia.org/wiki/Test",
        [f"{FIXED_TODAY} | Today thing | A note | https://en.wikipedia.org/wiki/Test"]
    )
    assert "today" in html
    assert "◀" in html
    assert "Today" in html  # full date in data-tip-date

def test_non_today_entry_has_no_today_class():
    html = _render(
        "timeline Test | https://en.wikipedia.org/wiki/Test",
        ["2026-02-13 | Past event | A note | https://en.wikipedia.org/wiki/Test"]
    )
    assert 'class="vtl-row today"' not in html

def test_data_tip_attributes_set():
    html = _render(
        "timeline Test | https://en.wikipedia.org/wiki/Test",
        ["2026-02-13 | My title | My note | https://en.wikipedia.org/wiki/Sub"]
    )
    assert 'data-tip-title="My title"' in html
    assert 'data-tip-note="My note"' in html
    assert 'data-tip-url="https://en.wikipedia.org/wiki/Sub"' in html

def test_empty_lines_skipped():
    html = _render(
        "timeline Test | https://en.wikipedia.org/wiki/Test",
        ["", "2026-02-13 | Event | Note | https://en.wikipedia.org/wiki/Test", ""]
    )
    # Should still render the one valid entry
    assert "Event" in html
    # Should not have extra empty rows
    assert html.count('class="vtl-row') == 1

def test_html_escaping():
    html = _render(
        "timeline Test & More | https://en.wikipedia.org/wiki/Test",
        ['2026-02-13 | Title <b>bold</b> | Note "quoted" | https://en.wikipedia.org/wiki/Test']
    )
    assert "<b>" not in html
    assert "&lt;b&gt;" in html
    assert "&quot;" in html

if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"  ✓ {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  ✗ {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    if failed:
        sys.exit(1)
