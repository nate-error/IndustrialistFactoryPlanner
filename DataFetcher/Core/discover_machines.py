from __future__ import annotations

import sys

sys.path.append('..')
from parse_machine_gallery import parse_gallery


def page_is_machine_page(html: str) -> bool:
    # Cheap substring check rather than a full BeautifulSoup parse. This gets called on every page in the traversal just to classify it, so keep it fast.
    return 'class="machine_infobox' in html


def discover_machines(start_url: str, start_name: str, fetch_fn, max_depth: int = 4) -> list[dict]:
    """
    Returns a flat list of {"name", "wiki_url", "wiki_slug"} for every leaf machine page found, no matter how many gallery levels deep it was.

    `fetch_fn` is injected (rather than importing fetch.fetch directly) so this can be unit-tested against an in memory fake site with no network
    or disk cache involved.
    """

    visited: set[str] = set()
    leaves: list[dict] = []

    def _walk(url: str, name: str, depth: int, icon_url: str | None) -> None:
        if url in visited or depth > max_depth:
            return
            
        visited.add(url)
        html = fetch_fn(url)

        if page_is_machine_page(html):
            wiki_slug = url.rsplit("/wiki/", 1)[-1]
            leaves.append({"name": name, "wiki_url": url, "wiki_slug": wiki_slug, "icon_url": icon_url})
            return

        # Not a machine page -> treat it as another gallery and recurse.
        for entry in parse_gallery(html):
            _walk(entry["wiki_url"], entry["name"], depth + 1, entry.get("icon_url"))

    _walk(start_url, start_name, 0, None)
    return leaves
