#!/usr/bin/env python3
"""
build_paper.py - assemble The Daily Ringo from template + content fragments.

Usage (from the cron job, after writing fragments):
    python3 build_paper.py --repo /tmp/daily-ringo-repo --fragments /tmp/fragments

Expects in --fragments (each a plain HTML fragment, no <html>/<head>):
    weather.html        - inner content of the weather bar
    lead.html           - tag + h2 + paragraph + read-more for the lead story
    top_stories.html    - 3-4 <div class="story-card">...</div> blocks
    hermes.html         - the three pillar h3s + lists for Hermes Corner
    markets.html        - the markets <table> + optional <p class="note">
    nfl.html            - 2-3 <div class="story-card">...</div> blocks
    dynasty.html        - inner content of the dynasty card

The script:
    1. Reads template.html and issue.txt from the repo.
    2. Computes today's date in Pacific/Auckland and increments the issue number.
    3. Substitutes all placeholders.
    4. Validates the result (no leftover placeholders, all section ids, sane size).
    5. Writes heatseek.html into the repo and updates issue.txt.
Exits 0 on success, 1 on any failure (with a clear message on stderr).
The issue counter is only written after validation passes.
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

FRAGMENTS = {
    "WEATHER": "weather.html",
    "LEAD_STORY": "lead.html",
    "TOP_STORIES": "top_stories.html",
    "HERMES_CORNER": "hermes.html",
    "MARKETS": "markets.html",
    "NFL": "nfl.html",
    "DYNASTY": "dynasty.html",
}

REQUIRED_IDS = ["weather", "tech", "hermes", "markets", "nfl", "dynasty"]
MIN_SIZE_BYTES = 14000
MIN_FRAGMENT_CHARS = 40  # catches empty/placeholder fragments
FORBIDDEN = ["{{", "lorem ipsum", "TODO", "PLACEHOLDER"]


def fail(msg: str) -> None:
    print(f"BUILD FAILED: {msg}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="Path to the cloned dragons-den-board repo")
    ap.add_argument("--fragments", required=True, help="Directory containing content fragment files")
    args = ap.parse_args()

    repo = Path(args.repo)
    frag_dir = Path(args.fragments)

    template_path = repo / "template.html"
    issue_path = repo / "issue.txt"
    output_path = repo / "heatseek.html"

    if not template_path.exists():
        fail(f"template.html not found in {repo}")

    html = template_path.read_text(encoding="utf-8")

    # --- Load and substitute fragments ---
    for token, filename in FRAGMENTS.items():
        frag_path = frag_dir / filename
        if not frag_path.exists():
            fail(f"missing fragment: {filename}")
        content = frag_path.read_text(encoding="utf-8").strip()
        if len(content) < MIN_FRAGMENT_CHARS:
            fail(f"fragment too short ({len(content)} chars): {filename}")
        html = html.replace("{{" + token + "}}", content)

    # --- Date, issue number, freshness stamp (Pacific/Auckland) ---
    now = datetime.now(ZoneInfo("Pacific/Auckland"))
    date_human = now.strftime("%A, %B %-d, %Y")
    generated_at = now.strftime("%H:%M NZT · %-d %b %Y")

    try:
        issue_no = int(issue_path.read_text().strip()) + 1
    except (FileNotFoundError, ValueError):
        issue_no = 1

    html = html.replace("{{DATE_HUMAN}}", date_human)
    html = html.replace("{{ISSUE_NO}}", str(issue_no))
    html = html.replace("{{GENERATED_AT}}", generated_at)

    # --- Validate ---
    for bad in FORBIDDEN:
        if bad.lower() in html.lower():
            fail(f"forbidden text remains in output: '{bad}'")
    for section_id in REQUIRED_IDS:
        if not re.search(rf'id="{section_id}"', html):
            fail(f"required section id missing: #{section_id}")
    if "</html>" not in html:
        fail("output is not a complete HTML document (no closing </html>)")
    if len(html.encode("utf-8")) < MIN_SIZE_BYTES:
        fail(f"output suspiciously small ({len(html.encode('utf-8'))} bytes, "
             f"minimum {MIN_SIZE_BYTES})")

    # --- Write (only after validation) ---
    output_path.write_text(html, encoding="utf-8")
    issue_path.write_text(str(issue_no) + "\n", encoding="utf-8")

    print(f"OK: wrote {output_path} — Issue No. {issue_no}, "
          f"{len(html.encode('utf-8'))} bytes, generated {generated_at}")


if __name__ == "__main__":
    main()
