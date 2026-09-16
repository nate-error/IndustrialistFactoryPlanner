"""
Parses a `.machine_infobox` block into a MachineInfobox dataclass-ish dict.

Structure observed (Geothermal_Well):
  <div class="machine_infobox tier_N">
    <div class="title">Name<small><span>ROMAN_TIER</span></small></div>
    <div class="image">...</div>
    <div class="category">SectionName</div>   <-- optional, changes "current section" for what follows
    <div class="information bordertop">
      <div class="header">Label</div>
      <div class="input">...value...</div>    <-- usually class="input", but NOT for Size (plain div)
    </div>
    ... repeated ...
  </div>

Known (category, label) pairs seen so far and what they map to:
  (None,    "Cost")              -> cost_money           ($ amount)
  (None,    "Required Research") -> required_research     (display name + wiki anchor)
  (None,    "Size")              -> size_width, size_height (from the .grid sub-widget)
  ("Output","Product(s)")        -> products              (list of item names/links)
  (None,    "Pollution")         -> pollution              (%/h)
  ("Power", "Input")             -> power_input_raw / power_input_mf_per_s
  ("Power", "Output")            -> power_output_raw / power_output_mf_per_s  (generators; not seen yet)
  (None,    "Capacity")          -> power_capacity_raw / power_capacity_mf  (only makes sense under "Power" too, but the sample has no explicit re-entry
  into "Power" category before it the category persists until changed, so this still resolves correctly)

Anything with a (category, label) pair we don't recognize is kept in `raw` under that key instead of being silently dropped, so future machine pages
with fields we haven't seen yet (dimensions beyond width/height, additional inputs, etc.) don't lose data, they just won't be in the typed fields until
this parser is extended.
"""

from __future__ import annotations
import re
from bs4 import BeautifulSoup, Tag
from Core.units import parse_power

MONEY_RE = re.compile(r"\$([\d,]+(?:\.\d+)?)")
PERCENT_RE = re.compile(r"([\d.]+)\s*%")


def _text(el: Tag) -> str:
    """get_text(strip=True) joins adjacent text nodes with no separator, which
    mangles multi-word values split across tags (e.g. "Hot " + <a>Water</a>
    becomes "HotWater"). This inserts a space between nodes first, then
    collapses any resulting double-spaces."""
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)).strip()




def parse_machine_infobox(html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    box = soup.find("div", class_="machine_infobox")
    if box is None:
        return {}

    result: dict = {
        "name": None,
        "tier": None,
        "cost_money": None,
        "required_research": None,
        "required_research_slug": None,
        "size_width": None,
        "size_height": None,
        "products": [],
        "pollution_percent_per_hour": None,
        "power_input_raw": None,
        "power_input_mf_per_s": None,
        "power_output_raw": None,
        "power_output_mf_per_s": None,
        "power_capacity_raw": None,
        "power_capacity_mf": None,
        "raw": {},  # anything we saw but didn't map to a typed field: {(category, label): text}
    }

    # tier_N class on the outer div, e.g. "machine_infobox tier_2"
    for cls in box.get("class", []):
        if cls.startswith("tier_"):
            try:
                result["tier"] = int(cls.split("_", 1)[1])
            except ValueError:
                print("Well")
                pass

    title = box.find("div", class_="title")
    if title:
        small = title.find("small")
        if small:
            small.extract()  # remove so get_text() below gives just the name
        result["name"] = title.get_text(strip=True)

    current_category = None
    for child in box.find_all("div", recursive=False):
        classes = child.get("class", [])

        if "category" in classes:
            current_category = child.get_text(strip=True)
            continue

        if "information" not in classes:
            continue  # title, image, etc.

        header = child.find("div", class_="header")
        # value container is usually class="input", but Size's isn't classed at all —
        # fall back to "whatever the second div child is" in that case.
        value_div = child.find("div", class_="input")
        if value_div is None:
            divs = child.find_all("div", recursive=False)
            value_div = divs[1] if len(divs) > 1 else None
        if header is None or value_div is None:
            continue

        label = _text(header)
        key = (current_category, label)
        
        if label == "Cost":
            m = MONEY_RE.search(value_div.get_text())
            if m:
                result["cost_money"] = float(m.group(1).replace(",", ""))

        elif label == "Required Research":
            link = value_div.find_all("a")
            # last <a> is the one with the display text (first is often just the icon)
            if link:
                last = link[-1]
                result["required_research"] = _text(last)
                href = last.get("href", "")
                if "#" in href:
                    result["required_research_slug"] = href.split("#", 1)[1]

        elif label == "Size":
            grid = value_div.find("div", class_="grid")
            if grid:
                w = grid.find("div", class_="gridWidth")
                h = grid.find("div", class_="gridHeight")
                if w:
                    result["size_width"] = float(w.get_text(strip=True))
                if h:
                    result["size_height"] = float(h.get_text(strip=True))

        elif label.startswith("Product"):
            # e.g. "Hot <a>Water</a>" -> keep the full display text as the product name; the wiki treats "Hot Water" as a display-level variant of the linked base item
            # "Water", not necessarily a separate item-database entry, flag for validator/normalizer.
            result["products"].append({
                "text": _text(value_div),
                "linked_item_slugs": [
                    a["href"][len("/wiki/"):] for a in value_div.find_all("a", href=True)
                    if a["href"].startswith("/wiki/")
                ],
            })

        elif label == "Pollution":
            m = PERCENT_RE.search(value_div.get_text())
            if m:
                result["pollution_percent_per_hour"] = float(m.group(1))

        elif label == "Input" and current_category == "Power":
            raw, val = parse_power(value_div.get_text())
            result["power_input_raw"], result["power_input_mf_per_s"] = raw, val

        elif label == "Output" and current_category == "Power":
            raw, val = parse_power(value_div.get_text())
            result["power_output_raw"], result["power_output_mf_per_s"] = raw, val

        elif label == "Capacity":
            raw, val = parse_power(value_div.get_text())
            result["power_capacity_raw"], result["power_capacity_mf"] = raw, val

        else:
            result["raw"][f"{current_category}:{label}"] = _text(value_div)

    return result
