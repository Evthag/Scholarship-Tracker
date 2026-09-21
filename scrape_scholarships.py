#!/usr/bin/env python3
"""
Scholarship scraper -> updates README.md with a live table.

How it works
------------
1. Reads scripts/sources_config.json for a list of pages to scrape.
2. For each enabled source, fetches the page and pulls out scholarship
   cards using the CSS selectors in the config.
3. Merges new results into data/scholarships.json (a running dataset,
   deduped by title+link so re-runs don't create duplicate rows).
4. Sorts by parsed deadline (soonest first; undated items go last) and
   writes a Markdown table into README.md between the
   <!--START_SECTION:scholarships--> / <!--END_SECTION:scholarships-->
   markers, mirroring how SimplifyJobs' internship README bot works.

Run manually:
    pip install -r requirements.txt
    python scripts/scrape_scholarships.py

If a source is JavaScript-rendered
-----------------------------------
requests + BeautifulSoup only see the raw HTML the server sends. If a
site injects scholarship cards with JS after load (view page source and
compare to what you see in-browser), swap that source's `fetch_html`
call for a headless-browser fetch instead, e.g. with Playwright:

    pip install playwright && playwright install chromium
    from playwright.sync_api import sync_playwright
    def fetch_html_js(url):
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(url, wait_until="networkidle")
            html = page.content()
            browser.close()
            return html

and call that instead of fetch_html() for that one source.
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "scripts" / "sources_config.json"
DATA_PATH = ROOT / "data" / "scholarships.json"
README_PATH = ROOT / "README.md"

START_MARKER = "<!--START_SECTION:scholarships-->"
END_MARKER = "<!--END_SECTION:scholarships-->"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; ScholarshipBot/1.0; "
        "+https://github.com/) personal-project-scholarship-tracker"
    )
}


def fetch_html(url: str) -> str | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        print(f"  ! failed to fetch {url}: {e}", file=sys.stderr)
        return None


def text_or_none(el):
    if el is None:
        return None
    return " ".join(el.get_text(strip=True).split()) or None


def matches_keywords(title: str, description: str | None, keywords: list[str]) -> bool:
    """True if any keyword appears in the title or description (case-insensitive).
    An empty keyword list disables filtering (keeps everything)."""
    if not keywords:
        return True
    haystack = f"{title} {description or ''}".lower()
    return any(kw.lower() in haystack for kw in keywords)


def scrape_source(source: dict, keywords: list[str]) -> list[dict]:
    print(f"Scraping: {source['name']} ({source['url']})")
    html = fetch_html(source["url"])
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select(source["list_selector"])
    print(f"  found {len(cards)} candidate cards")

    results = []
    skipped_off_topic = 0
    for card in cards:
        title_el = card.select_one(source["title_selector"])
        title = text_or_none(title_el)
        if not title:
            continue

        description = text_or_none(card.select_one(source.get("description_selector", "")))

        if not matches_keywords(title, description, keywords):
            skipped_off_topic += 1
            continue

        link_el = card.select_one(source["link_selector"])
        link = link_el.get(source.get("link_attr", "href")) if link_el else None
        if link and source.get("base_url"):
            link = urljoin(source["base_url"], link)

        amount = text_or_none(card.select_one(source.get("amount_selector", "")))
        deadline_raw = text_or_none(card.select_one(source.get("deadline_selector", "")))

        results.append(
            {
                "title": title,
                "link": link,
                "amount": amount,
                "deadline_raw": deadline_raw,
                "source": source["name"],
                "first_seen": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            }
        )
    if skipped_off_topic:
        print(f"  - {skipped_off_topic} card(s) skipped (no keyword match)")
    return results


def parse_deadline(raw: str | None):
    """Best-effort parse of a free-text deadline into a date for sorting.
    Returns None if it can't be parsed (item is sorted to the bottom)."""
    if not raw:
        return None
    raw = raw.replace("Deadline:", "").strip()
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    match = re.search(r"([A-Za-z]+ \d{1,2},? \d{4})", raw)
    if match:
        return parse_deadline(match.group(1))
    return None


def load_existing() -> list[dict]:
    if DATA_PATH.exists():
        return json.loads(DATA_PATH.read_text())
    return []


def dedupe_key(item: dict) -> str:
    return f"{item['title'].strip().lower()}|{(item.get('link') or '').strip().lower()}"


def merge(existing: list[dict], new: list[dict]) -> list[dict]:
    by_key = {dedupe_key(i): i for i in existing}
    added = 0
    for item in new:
        key = dedupe_key(item)
        if key not in by_key:
            by_key[key] = item
            added += 1
        else:
            # refresh amount/deadline text in case it changed, keep original first_seen
            by_key[key]["amount"] = item["amount"] or by_key[key].get("amount")
            by_key[key]["deadline_raw"] = item["deadline_raw"] or by_key[key].get("deadline_raw")
    print(f"  + {added} new scholarship(s) this run")
    return list(by_key.values())


def build_table(items: list[dict]) -> str:
    def sort_key(i):
        d = parse_deadline(i.get("deadline_raw"))
        return (d is None, d or datetime.max)

    items_sorted = sorted(items, key=sort_key)

    lines = [
        "| Scholarship | Amount | Deadline | Source | Added |",
        "| --- | --- | --- | --- | --- |",
    ]
    for i in items_sorted:
        title = f"[{i['title']}]({i['link']})" if i.get("link") else i["title"]
        lines.append(
            f"| {title} | {i.get('amount') or '—'} | {i.get('deadline_raw') or '—'} "
            f"| {i.get('source') or '—'} | {i.get('first_seen') or '—'} |"
        )
    return "\n".join(lines)


def update_readme(table_md: str):
    readme = README_PATH.read_text()
    if START_MARKER not in readme or END_MARKER not in readme:
        print("README markers not found -- see README.md template.", file=sys.stderr)
        sys.exit(1)

    before = readme.split(START_MARKER)[0]
    after = readme.split(END_MARKER)[1]
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    new_section = (
        f"{START_MARKER}\n"
        f"*Last updated: {timestamp}*\n\n"
        f"{table_md}\n\n"
        f"{END_MARKER}"
    )
    README_PATH.write_text(before + new_section + after)


def main():
    config = json.loads(CONFIG_PATH.read_text())
    keywords = config.get("keywords", [])
    if keywords:
        print(f"Keyword filter active: {', '.join(keywords)}\n")

    all_new = []
    for source in config["sources"]:
        if not source.get("enabled", False):
            print(f"Skipping disabled source: {source['name']}")
            continue
        all_new.extend(scrape_source(source, keywords))

    existing = load_existing()
    merged = merge(existing, all_new)

    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(merged, indent=2))

    table_md = build_table(merged)
    update_readme(table_md)
    print(f"Done. {len(merged)} total scholarships tracked.")


if __name__ == "__main__":
    main()
