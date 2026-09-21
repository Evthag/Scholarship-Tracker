# 🎓 CS / Data Science / Statistics Scholarship Tracker

Automatically updated list of open scholarships for **Computer Science,
Data Science, Data Analytics, and Statistics** students, scraped from
public listing pages on a daily schedule via GitHub Actions. Every source
is passed through a keyword filter (`scripts/sources_config.json` ->
`"keywords"`) so only on-topic scholarships make it into the table, even
if a source lists scholarships for all majors. Inspired by the
[Summer2027-Internships](https://github.com/SimplifyJobs/Summer2027-Internships)
bot pattern: a scheduled workflow runs a scraper and commits the refreshed
table back to this README.

**How it works:** `.github/workflows/update-scholarships.yml` runs
`scripts/scrape_scholarships.py` every day. The script pulls listings from
the sources configured in `scripts/sources_config.json`, merges them into
`data/scholarships.json` (deduped, so nothing repeats), and rewrites the
table below.

> Sources currently scrape public, no-login listing pages. Add or remove
> sources by editing `scripts/sources_config.json` — see that file's
> comments for how selectors work. Always check a site's `robots.txt` and
> Terms of Service before adding it as a source.

## Open Scholarships

<!--START_SECTION:scholarships-->
*Last updated: 2026-09-21 11:31 UTC*

| Scholarship | Amount | Deadline | Source | Added |
| --- | --- | --- | --- | --- |

<!--END_SECTION:scholarships-->

## Running it yourself

```bash
git clone <your-repo-url>
cd scholarship-bot
pip install -r requirements.txt
python scripts/scrape_scholarships.py
```

## Adding a new source

1. Run `python scripts/inspect_page.py <listing-page-url>` (needs real internet access) to get a candidate card selector.
2. Open the same page in your browser, right-click a scholarship card → **Inspect**, and confirm the selector — note the CSS selector for the title/link/amount/deadline inside it too.
3. Add an entry to `scripts/sources_config.json` with `"enabled": true`.
4. Run `python scripts/scrape_scholarships.py` locally to confirm it picks up correctly filtered results before relying on the scheduled workflow.

## Adjusting the topic filter

Edit the `"keywords"` list in `scripts/sources_config.json`. A scraped
scholarship is kept only if its title or description contains at least
one keyword (case-insensitive). Defaults cover CS, data science, data
analytics, and statistics — add or remove terms (e.g. "bioinformatics",
"cybersecurity") to widen or narrow what shows up.
