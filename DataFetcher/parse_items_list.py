"""
Parses the item-icon-container grid on /wiki/Items into item records.

IMPORTANT: the wiki page slug (from the href, e.g. "10_Karat_Gold", underscored, original case) is a different convention from the `data-item` slug used inside recipe
blocks (e.g. "10-karat-gold", lowercase, hyphenated).
These are not interchangeable. This module derives both: `wiki_slug` (for building/fetching the page URL) and `id` (the data-item-style canonical slug, used
everywhere else, matching recipe ingredients, machine references, etc.)

The derivation (lowercase + spaces->hyphens) is inferred and hasn't been checked against names with unusual characters (e.g. "Iron Plate^2", "GasolineE10").
If validate.py starts reporting recipe ingredients that don't match any item id, the likely cause is this derivation guessing wrong on a specific name's
punctuation, check it against the item's actual recipe data-item attribute and adjust `derive_data_item_id`.
"""

from __future__ import annotations
import re
from bs4 import BeautifulSoup


def derive_data_item_id(name: str) -> str:
    slug = name.strip().lower()
    slug = re.sub(r"\s+", "-", slug)
    return slug


def parse_items_list(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    out = []
    
    for container in soup.find_all("div", class_="item-icon-container"):
        name = container.get("data-name")
        link = container.find("a", href=True)
        if not name or not link:
            continue

        href = link["href"]
        wiki_slug = href[len("/wiki/"):] if href.startswith("/wiki/") else href
        img = container.find("img")
        icon_url = img["src"] if img and img.has_attr("src") else None
        out.append({
            "id": derive_data_item_id(name),
            "name": name,
            "wiki_slug": wiki_slug,
            "wiki_url": f"https://industrialist.miraheze.org{href}",
            "icon_url": f"https:{icon_url}" if icon_url and icon_url.startswith("//") else icon_url,
        })

    return out
