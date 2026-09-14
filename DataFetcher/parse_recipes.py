"""
Parses the .production-wrapper widget found on item wiki pages into Recipe objects. This is pure HTML -> data logic with no network calls, so it can be
unit-tested against saved fixtures.
"""

from __future__ import annotations
import re
import sys
from bs4 import BeautifulSoup, Tag

sys.path.append('..')
from Core.schemas import Recipe, RecipeIngredient
from Core.units import parse_power

DURATION_RE = re.compile(r"([\d.]+)\s*s")


def _parse_icon_box(icon_box: Tag) -> RecipeIngredient:
    item_id = icon_box["data-item"]
    qty_text = icon_box.find("span", class_="production-number")
    qty_text = qty_text.get_text(strip=True) if qty_text else "1x"
    quantity = float(qty_text.rstrip("x"))

    # Display name: prefer the <img alt="...">, fall back to the <a title="...">
    img = icon_box.find("img")
    name = img["alt"] if img and img.has_attr("alt") else item_id
    return RecipeIngredient(item_id=item_id, item_name=name, quantity=quantity)


def parse_production_wrapper(
    html: str,
    source_page: str,
    default_machine_name: str | None = None,
    default_machine_slug: str | None = None,
) -> list[Recipe]:
    """
    `html` is the .production-wrapper div's outer HTML (or any HTML containing it).
    `source_page` is the wiki page title/slug this HTML came from, used for provenance (seen_on_pages) so the normalizer can de-duplicate recipes that
    show up on multiple item pages.

    On ITEM pages, each recipe block ends with a `.production-text` link naming the machine (e.g. "(Gold Acid Refinery)"), that's how the
    machine is identified there.

    On MACHINE pages (the "Recipes" section of e.g. Geothermal_Well), that trailing link is absent, the page you're already on IS the machine, so
    the wiki doesn't bother repeating it. Pass `default_machine_name` / `default_machine_slug` when scraping a machine page so those recipes
    aren't silently dropped for "missing" a machine reference.
    """
    soup = BeautifulSoup(html, "lxml")
    recipes: list[Recipe] = []

    for rectangle in soup.find_all("div", class_="production-rectangle"):
        debug_span = rectangle.find("span", class_="production-debug-id")
        if not debug_span or not debug_span.has_attr("data-recipe-id"):
            # No stable ID -> we can't safely de-duplicate this recipe across pages. Skip it and let the validator flag the gap rather than
            # inventing an ID that might not match on other pages.
            continue
        recipe_id = debug_span["data-recipe-id"]

        inputs: list[RecipeIngredient] = []
        outputs: list[RecipeIngredient] = []
        duration_seconds = None
        power_rate_raw = None
        machine_name = None
        machine_slug = None
        seen_arrow = False

        for child in rectangle.children:
            if not isinstance(child, Tag):
                continue

            if child.name == "span" and "ext-floatingui-reference" in child.get("class", []):
                icon_box = child.find("div", class_=lambda c: c and "production-icon-box" in c)
                if icon_box is None:
                    continue
                ingredient = _parse_icon_box(icon_box)
                (outputs if seen_arrow else inputs).append(ingredient)

            elif child.name == "div" and "production-arrow-container" in child.get("class", []):
                seen_arrow = True
                arrow_texts = child.find_all("div", class_="production-arrow-text")
                if len(arrow_texts) >= 1:
                    m = DURATION_RE.search(arrow_texts[0].get_text(strip=True))
                    if m:
                        duration_seconds = float(m.group(1))
                if len(arrow_texts) >= 2:
                    power_rate_raw = arrow_texts[1].get_text(strip=True)

            elif child.name == "div" and "production-text" in child.get("class", []):
                link = child.find("a")
                if link:
                    machine_name = link.get_text(strip=True).strip("()")
                    href = link.get("href", "")
                    if href.startswith("/wiki/"):
                        machine_slug = href[len("/wiki/"):]

            # production-plus and ext-floatingui-content: intentionally ignored

        if machine_name is None:
            if default_machine_name is not None:
                machine_name = default_machine_name
                machine_slug = default_machine_slug
            else:
                # A recipe block with no machine link AND no fallback context is malformed.
                continue

        power_rate_mf_per_s = parse_power(power_rate_raw)[1] if power_rate_raw else None

        recipes.append(
            Recipe(
                id=recipe_id,
                machine_name=machine_name,
                machine_slug=machine_slug,
                inputs=inputs,
                outputs=outputs,
                duration_seconds=duration_seconds,
                power_rate_raw=power_rate_raw,
                power_rate_mf_per_s=power_rate_mf_per_s,
                seen_on_pages=[source_page],
            )
        )

    return recipes
