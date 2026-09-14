"""
Validate a Database (schemas.Database).

Returns a list of problem strings. Empty list = clean.
Deliberately does NOT raise/crash on problems, a partially-broken database is still useful to inspect, and the whole point of this is to surface
every issue at once rather than dying on the first one.
"""

from __future__ import annotations

sys.path.append('..')
from schemas import Database


def validate(db: Database) -> list[str]:
    problems: list[str] = []

    item_ids = set(db.items.keys())
    machine_ids = set(db.machines.keys())
    recipe_ids = set(db.recipes.keys())

    # --- Recipe references unknown item ---
    for recipe in db.recipes.values():
        for ing in recipe.inputs + recipe.outputs:
            if ing.item_id not in item_ids:
                problems.append(f"Recipe '{recipe.id}' references unknown item '{ing.item_id}'")

    # --- Recipe references unknown/unmatched machine ---
    for recipe in db.recipes.values():
        if recipe.machine_slug and recipe.machine_slug not in machine_ids:
            problems.append(f"Recipe '{recipe.id}' references machine slug '{recipe.machine_slug}' not present in the machine database "
                f"(machine name seen: '{recipe.machine_name}')")

    # --- Machine references unknown recipe ---
    for machine in db.machines.values():
        for rid in machine.recipe_ids:
            if rid not in recipe_ids:
                problems.append(f"Machine '{machine.id}' references unknown recipe '{rid}'")

    # --- Negative / zero production values ---
    for recipe in db.recipes.values():
        for ing in recipe.inputs + recipe.outputs:
            if ing.quantity <= 0:
                problems.append(f"Recipe '{recipe.id}' has non-positive quantity ({ing.quantity}) for '{ing.item_id}'")

        if recipe.duration_seconds is not None and recipe.duration_seconds <= 0:
            problems.append(f"Recipe '{recipe.id}' has non-positive duration")

    # --- Missing recipe input/output entirely ---
    for recipe in db.recipes.values():
        if not recipe.inputs:
            problems.append(f"Recipe '{recipe.id}' has no inputs (raw resource? confirm intentional)")

        if not recipe.outputs:
            problems.append(f"Recipe '{recipe.id}' has no outputs")

    # --- Recipe missing duration/power (parser gaps) ---
    for recipe in db.recipes.values():
        if recipe.duration_seconds is None:
            problems.append(f"Recipe '{recipe.id}' is missing a parsed duration")

        if recipe.power_rate_raw is None:
            problems.append(f"Recipe '{recipe.id}' is missing a parsed power rate")

    # --- Duplicate IDs across categories (shouldn't happen with dict keys, but catches the case where two different source pages produced
    # the same recipe_id with different contents) ---
    seen_signatures: dict[str, tuple] = {}
    for recipe in db.recipes.values():
        sig = (
            tuple(sorted((i.item_id, i.quantity) for i in recipe.inputs)),
            tuple(sorted((o.item_id, o.quantity) for o in recipe.outputs)),
        )

        if recipe.id in seen_signatures and seen_signatures[recipe.id] != sig:
            problems.append(
                f"Recipe id '{recipe.id}' appears with two different "
                f"input/output signatures across pages {recipe.seen_on_pages} "
                f"— the wiki may reuse this ID for two distinct recipes"
            )

        seen_signatures[recipe.id] = sig

    # --- Orphan items: never appear as input or output of any recipe ---
    used_item_ids = {
        ing.item_id
        for recipe in db.recipes.values()
        for ing in recipe.inputs + recipe.outputs
    }

    for item_id in item_ids - used_item_ids:
        problems.append(f"Item '{item_id}' is never used as a recipe input or output")

    return problems


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) != 2:
        print("Usage: python validate.py <database.json>")
        sys.exit(1)

    with open(sys.argv[1], encoding="utf-8") as f:
        db = Database.model_validate(json.load(f))

    problems = validate(db)
    if not problems:
        print("No problems found.")
    else:
        print(f"{len(problems)} problem(s) found:\n")
        for p in problems:
            print(f" - {p}")
