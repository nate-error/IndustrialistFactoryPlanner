"""
    python scrape.py # scrape everything, write industrialist_db.json
    python scrape.py --limit 20 # only process the first 20 items (dev/testing)

Design choices:
  - Every raw page fetch goes through fetch.fetch(), so caching/rate limiting/bot detection handling is centralized (see fetch.py's docstring !!READ
    THAT FIRST if this script errors out on the very first request!!).
  - Recipes are de duplicated by id as they're discovered across multiple item pages (a recipe shows up once per item it touches).
"""

from __future__ import annotations
import argparse
import json
import re
import os

from Core.fetch import fetch
from parse_items_list import parse_items_list
from parse_machine_gallery import parse_gallery
from parse_recipes import parse_production_wrapper
from parse_machine_infobox import parse_machine_infobox
from parse_extractor_depth_table import parse_extractor_depth_tables
from variable_extractors_data import KNOWN_VARIABLE_EXTRACTORS, MINESHAFT_DRILL_CONSUMABLES, MINESHAFT_DRILL_NOTES
from Core.discover_machines import discover_machines
from Core.schemas import Database, Item, Machine, MachineProduct, VariableExtractorProfile, ExtractorDepthProfile, ExtractorDepthOutput

BASE = "https://industrialist.miraheze.org"

# This is a regex based scrape of raw item pages for "Money" / "RP". See NOTE in scrape_item_page() below.

MONEY_RE = re.compile(r"Money[^\d]{0,10}(\d[\d,.]*)", re.IGNORECASE)
RP_RE = re.compile(r"\bRP\b[^\d]{0,10}(\d[\d,.]*)", re.IGNORECASE)


def scrape_items_list() -> list[dict]:
    html = fetch(f"{BASE}/wiki/Items")
    return parse_items_list(html)


def scrape_machine_categories() -> list[dict]:
    html = fetch(f"{BASE}/wiki/Machines_%26_Models")
    return parse_gallery(html)


def scrape_machines_in_category(category: dict) -> list[dict]:
    """
    Recursively walks this category's gallery (and any sub galleries nested beneath it) to find every individual machine page. See discover_machines.py for why
    this needs to be recursive rather than a single level gallery parse.
    """
    machines = discover_machines(category["wiki_url"], category["name"], fetch_fn=fetch)
    for m in machines:
        m["category"] = category["name"]  # tag with the TOP-level category, not any intermediate sub-gallery name

    return machines


def scrape_machine_page(machine_meta: dict, db: Database) -> None:
    """
    Fetches one machine's own page and merges in:
      - infobox stats (cost, size, power, pollution, research, products)
      - recipes defined on this page (which have no trailing machine name link, since the page itself is the machine
    """
    html = fetch(machine_meta["wiki_url"])
    info = parse_machine_infobox(html)

    existing = db.machines.get(machine_meta["wiki_slug"])
    recipe_ids = list(existing.recipe_ids) if existing else []

    db.machines[machine_meta["wiki_slug"]] = Machine(
        id=machine_meta["wiki_slug"],
        name=info.get("name") or machine_meta["name"],
        tier=info.get("tier"),
        category=machine_meta.get("category"),
        wiki_url=machine_meta["wiki_url"],
        icon_url=machine_meta.get("icon_url"),
        cost_money=info.get("cost_money"),
        required_research=info.get("required_research"),
        required_research_slug=info.get("required_research_slug"),
        size_width=info.get("size_width"),
        size_height=info.get("size_height"),
        products=[MachineProduct(display_text=p["text"], linked_item_slugs=p["linked_item_slugs"])
                  for p in info.get("products", [])],
        pollution_percent_per_hour=info.get("pollution_percent_per_hour"),
        power_input_raw=info.get("power_input_raw"),
        power_input_mf_per_s=info.get("power_input_mf_per_s"),
        power_output_raw=info.get("power_output_raw"),
        power_output_mf_per_s=info.get("power_output_mf_per_s"),
        power_capacity_raw=info.get("power_capacity_raw"),
        power_capacity_mf=info.get("power_capacity_mf"),
        recipe_ids=recipe_ids,
        infobox_raw_extra=info.get("raw", {}),
    )

    own_recipes = parse_production_wrapper(
        html,
        source_page=machine_meta["wiki_slug"],
        default_machine_name=info.get("name") or machine_meta["name"],
        default_machine_slug=machine_meta["wiki_slug"],
    )

    for r in own_recipes:
        if r.id in db.recipes:
            db.recipes[r.id].seen_on_pages.append(machine_meta["wiki_slug"])
        else:
            db.recipes[r.id] = r
            db.machines[machine_meta["wiki_slug"]].recipe_ids.append(r.id)

    # Mineshaft specification
    if machine_meta["wiki_slug"] in KNOWN_VARIABLE_EXTRACTORS:
        depth_rows = parse_extractor_depth_tables(html)
        depth_profiles = [
            ExtractorDepthProfile(
                depth_m=row["depth_m"],
                power_mf_per_s=row["power_mf_per_s"],
                cycle_seconds=row["cycle_seconds"],
                outputs=[ExtractorDepthOutput(**o) for o in row["outputs"]],
            )
            for row in depth_rows
        ]
        # Consumables are currently hand authored per machine (see variable_extractors_data.py for why); this dict lookup is the only place that machine specific choice happens.
        consumables = MINESHAFT_DRILL_CONSUMABLES if machine_meta["wiki_slug"] == "Mineshaft_Drill" else []
        notes = MINESHAFT_DRILL_NOTES if machine_meta["wiki_slug"] == "Mineshaft_Drill" else []
 
        db.variable_extractors[machine_meta["wiki_slug"]] = VariableExtractorProfile(
            machine_id=machine_meta["wiki_slug"],
            depth_profiles=depth_profiles,
            consumables=consumables,
            unmodeled_notes=notes,
        )



def scrape_item_page(item_meta: dict, db: Database) -> None:
    html = fetch(item_meta["wiki_url"])

    money_match = MONEY_RE.search(html)
    rp_match = RP_RE.search(html)

    db.items[item_meta["id"]] = Item(
        id=item_meta["id"],
        name=item_meta["name"],
        wiki_slug=item_meta["wiki_slug"],
        wiki_url=item_meta["wiki_url"],
        icon_url=item_meta.get("icon_url"),
        money=float(money_match.group(1).replace(",", "")) if money_match else None,
        research_points=float(rp_match.group(1).replace(",", "")) if rp_match else None,
    )

    recipes = parse_production_wrapper(html, source_page=item_meta["wiki_slug"])
    for r in recipes:
        if r.id in db.recipes:
            db.recipes[r.id].seen_on_pages.append(item_meta["wiki_slug"])
        else:
            db.recipes[r.id] = r
            if r.machine_slug:
                machine = db.machines.setdefault(r.machine_slug, Machine(id=r.machine_slug, name=r.machine_name))
                machine.recipe_ids.append(r.id)


def run(limit: int | None = None) -> Database:
    db = Database()

    print("Fetching machine categories...")
    categories = scrape_machine_categories()
    machine_metas: list[dict] = []

    for cat in categories:
        print(f"  {cat['name']} ({cat['wiki_url']})")
        machine_metas.extend(scrape_machines_in_category(cat))

    if limit:
        machine_metas = machine_metas[:limit]

    print(f"  {len(machine_metas)} machines to process")

    for i, m in enumerate(machine_metas, 1):
        print(f"  [{i}/{len(machine_metas)}] {m['name']}")
        scrape_machine_page(m, db)

    print("Fetching items list...")
    items = scrape_items_list()
    
    if limit:
        items = items[:limit]

    print(f"  {len(items)} items to process")

    for i, item_meta in enumerate(items, 1):
        print(f"  [{i}/{len(items)}] {item_meta['name']}")
        scrape_item_page(item_meta, db)

    return db


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="only process N items (dev/testing)")
    parser.add_argument("--out", default="./Data/industrialist_db.json")
    args = parser.parse_args()

    # Make sure the output directory exists
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)

    db = run(limit=args.limit)

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(db.model_dump_json(indent=2))

    print(
        f"\nWrote {len(db.items)} items, "
        f"{len(db.machines)} machines, "
        f"{len(db.recipes)} recipes to {args.out}"
    )