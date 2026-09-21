#!/usr/bin/env python3
"""
Selector-finding helper. Run this on a machine with real internet access
(it won't work in a sandboxed/offline environment) to get a head start on
filling in scripts/sources_config.json for a new source.

Usage:
    python scripts/inspect_page.py https://example.com/scholarships

What it does:
- Fetches the page.
- Finds repeated container elements (the same tag+class appearing many
  times) -- these are usually the scholarship "cards".
- For the most promising candidate, prints its selector plus a sample of
  the text/links inside one instance, so you can see what titles/amounts/
  deadlines look like and write the rest of the selectors by hand.

This is a starting point, not magic -- always confirm in your browser's
DevTools (right-click a scholarship title -> Inspect) before trusting it.
"""

import sys
from collections import Counter

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; ScholarshipBot/1.0; "
        "+https://github.com/) personal-project-scholarship-tracker"
    )
}


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/inspect_page.py <url>")
        sys.exit(1)

    url = sys.argv[1]
    print(f"Fetching {url} ...")
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # Count how many times each (tag, class-list) combo appears.
    counts = Counter()
    for el in soup.find_all(True):
        classes = el.get("class")
        if not classes:
            continue
        key = (el.name, " ".join(classes))
        counts[key] = counts.get(key, 0) + 1

    # Repeating elements with a plausible count (5-300) are likely cards.
    candidates = [
        (tag, cls, n) for (tag, cls), n in counts.items() if 5 <= n <= 300
    ]
    candidates.sort(key=lambda x: -x[2])

    if not candidates:
        print(
            "No repeating elements found in the raw HTML. This page is "
            "likely rendered by JavaScript after load -- plain requests "
            "won't see the content. Consider a Playwright-based fetch "
            "(see the note in scrape_scholarships.py)."
        )
        return

    print(f"\nTop candidate 'card' selectors (tag.class, occurrence count):\n")
    for tag, cls, n in candidates[:10]:
        print(f"  {tag}.{cls.replace(' ', '.')}   (x{n})")

    top_tag, top_cls, top_n = candidates[0]
    selector = f"{top_tag}.{top_cls.replace(' ', '.')}"
    print(f"\nMost likely card selector: {selector}")
    print("Sample content of the first instance:\n" + "-" * 40)
    sample = soup.select(selector)[0]
    print(sample.get_text(" | ", strip=True)[:500])
    print("-" * 40)
    print(
        "\nLook at the sample above and identify which part is the title, "
        "amount, and deadline. Then inspect that element in your browser "
        "to find its specific class name for the *_selector fields in "
        "sources_config.json."
    )


if __name__ == "__main__":
    main()
