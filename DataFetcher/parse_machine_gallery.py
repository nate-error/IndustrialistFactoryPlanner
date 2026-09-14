"""
Parses a MediaWiki <ul class="gallery"> into (name, slug, url) tuples.
Used both for:
  - the top-level category gallery on Machines_%26_Models (Power, Extractors, Factories, ...)
  - each category's sub-gallery of individual machines
Same DOM shape either way, so one parser covers both.
"""

from __future__ import annotations
from bs4 import BeautifulSoup


def parse_gallery(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    out = []
    
    for box in soup.find_all("li", class_="gallerybox"):
        link = box.find("a", href=True)

        if not link:
            continue

        href = link["href"]
        slug = href[len("/wiki/"):] if href.startswith("/wiki/") else href
        name = link.get("title") or link.get_text(strip=True)
        img = box.find("img")
        icon_url = img["src"] if img and img.has_attr("src") else None

        out.append({
            "name": name,
            "wiki_slug": slug,
            "wiki_url": f"https://industrialist.miraheze.org{href}",
            "icon_url": f"https:{icon_url}" if icon_url and icon_url.startswith("//") else icon_url,
        })
    return out
