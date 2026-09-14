"""
Cross-checks category-gallery discovery against recipe references.

Two independent ways of finding out a machine exists:
  1. Walk the category galleries recursively (discover_machines.py) 
  2. Scan every item page's recipes and note every machine_slug a recipe points to (parse_recipes.py)

Usage:
    python test_machine_parser.py # full run (all items)
    python test_machine_parser.py 50 # quick check: only scan the first 50 items
"""

from __future__ import annotations
import sys
import traceback

sys.path.append('..')
from fetch import fetch
from parse_machine_gallery import parse_gallery
from parse_items_list import parse_items_list
from parse_recipes import parse_production_wrapper
from discover_machines import discover_machines

BASE = "https://industrialist.miraheze.org"


def get_all_discovered_machines() -> dict[str, dict]:
    """{wiki_slug: {"name", "category", "wiki_url"}} for every machine reachable via the category gallery walk (i.e. what scrape.py would actually fetch)."""
    html = fetch(f"{BASE}/wiki/Machines_%26_Models")
    categories = parse_gallery(html)
    print(f"Top-level categories found: {[c['name'] for c in categories]}\n")

    all_machines: dict[str, dict] = {}
    for cat in categories:
        try:
            leaves = discover_machines(cat["wiki_url"], cat["name"], fetch_fn=fetch)
        except Exception as e:
            print(f"  !! ERROR walking category '{cat['name']}' ({cat['wiki_url']}): {e}")
            traceback.print_exc()
            continue

        print(f"  {cat['name']}: {len(leaves)} machines discovered")
        for m in leaves:
            if m["wiki_slug"] in all_machines and all_machines[m["wiki_slug"]]["category"] != cat["name"]:
                print(f"    (!) '{m['name']}' appears under multiple categories: "
                      f"{all_machines[m['wiki_slug']]['category']} AND {cat['name']}")
            all_machines[m["wiki_slug"]] = {"name": m["name"], "category": cat["name"], "wiki_url": m["wiki_url"]}

    return all_machines


def get_all_recipe_referenced_machine_slugs(item_limit: int | None = None) -> dict[str, set[str]]:
    """slug -> set of recipe ids that reference it, scanned straight off item pages, completely independent of the category-gallery code path."""
    html = fetch(f"{BASE}/wiki/Items")
    items = parse_items_list(html)
    if item_limit:
        items = items[:item_limit]

    print(f"\nScanning {len(items)} item pages for recipe -> machine references...")
    referenced: dict[str, set[str]] = {}
    for i, item in enumerate(items, 1):
        try:
            item_html = fetch(item["wiki_url"])
        except Exception as e:
            print(f"  !! ERROR fetching item '{item['name']}': {e}")
            continue

        recipes = parse_production_wrapper(item_html, source_page=item["wiki_slug"])
        for r in recipes:
            if r.machine_slug:
                referenced.setdefault(r.machine_slug, set()).add(r.id)

        if i % 25 == 0:
            print(f"  ...{i}/{len(items)} items scanned")

    return referenced


def main():
    item_limit = int(sys.argv[1]) if len(sys.argv) > 1 else None

    discovered = get_all_discovered_machines()
    referenced = get_all_recipe_referenced_machine_slugs(item_limit=item_limit)

    print(f"\n{'='*60}")
    print(f"Discovered via category galleries: {len(discovered)} machines")
    print(f"Referenced by at least one recipe:  {len(referenced)} machine slugs")

    missing = set(referenced) - set(discovered)
    if missing:
        print(f"\n!! {len(missing)} machine slug(s) referenced by recipes but NEVER discovered by the category gallery walk:")

        for slug in sorted(missing):
            ids = sorted(referenced[slug])
            print(f"   - {slug}  (e.g. recipes: {ids[:5]}{' ...' if len(ids) > 5 else ''})")
    else:
        print("\nAll recipe-referenced machines were successfully discovered. No gaps found.")

    extra = set(discovered) - set(referenced)
    print(f"\n({len(extra)} discovered machines have no recipe referencing them in this scan -- expected if you used an item_limit, or if a machine genuinely has no recipes yet.)")


if __name__ == "__main__":
    main()