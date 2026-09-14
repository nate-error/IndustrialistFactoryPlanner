"""
Fetch layer for the scraper.

Contains a persistent `requests.Session` so cookies from an initial Cloudflare "clearance" challenge (if one appears) carry across all requests instead 
of being triggered every call.
A minimum delay between requests (Polite).
Disk caching keyed by URL, so re running the scraper doesn't re fetch the site.
A `requests_html`/`cloudscraper` fallback path, commented, in case plain `requests` still gets a Cloudflare JS-challenge page back (you'll know because the
cached HTML will be a page titled "Just a moment..." instead of real wiki content — `looks_like_cf_challenge()` below checks for this).

If it works, everything downstream (item list, machine list, all detail pages) reuses `fetch()`.
"""

from __future__ import annotations
import time
import hashlib
from pathlib import Path
import requests

CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

MIN_DELAY_SECONDS = 1.5  # Polite behaviour

HEADERS = {
    "User-Agent": (
        "IndustrialistFactoryPlannerBot/0.1 "
        "(https://github.com/nate-error/IndustrialistFactoryPlanner; "
        "contact: your@email.com)"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

_session = requests.Session()
_session.headers.update(HEADERS)
_last_request_time = 0.0


def _cache_path(url: str) -> Path:
    key = hashlib.sha256(url.encode()).hexdigest()
    return CACHE_DIR / f"{key}.html"


def looks_like_cf_challenge(html: str) -> bool:
    markers = ("Just a moment", "cf-browser-verification", "Enable JavaScript and cookies")
    return any(m in html for m in markers)


def fetch(url: str, force_refresh: bool = False) -> str:
    """Fetch a URL, using the disk cache unless force_refresh=True."""
    global _last_request_time
    cache_file = _cache_path(url)

    if not force_refresh and cache_file.exists():
        return cache_file.read_text(encoding="utf-8")

    elapsed = time.monotonic() - _last_request_time
    if elapsed < MIN_DELAY_SECONDS:
        time.sleep(MIN_DELAY_SECONDS - elapsed)

    resp = _session.get(url, timeout=20)
    _last_request_time = time.monotonic()
    resp.raise_for_status()
    html = resp.text

    if looks_like_cf_challenge(html):
        raise RuntimeError(
            f"Got a Cloudflare challenge page for {url}, not real content.\n"
            "Next steps to try, in order:\n"
            "  1. pip install cloudscraper, and swap `_session.get` for a "
            "cloudscraper session's .get() (drop-in replacement).\n"
            "  2. Open the URL in a real browser once, copy the 'cf_clearance' "
            "cookie, and preload it into `_session.cookies`.\n"
            "  3. As a last resort, use playwright/selenium to load the page "
            "and pull `page.content()` instead of requests entirely."
        )

    cache_file.write_text(html, encoding="utf-8")
    return html


if __name__ == "__main__":
    # Smoke test: fetch exactly one page and report what we got.
    test_url = "https://industrialist.miraheze.org/wiki/Items"
    try:
        html = fetch(test_url)
        print(f"Fetched {len(html)} chars OK. First 200 chars:\n{html[:200]}")
    except Exception as e:
        print(f"FAILED: {e}")
