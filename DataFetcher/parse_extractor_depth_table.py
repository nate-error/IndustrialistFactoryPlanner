"""
Parses the depth -> output-rates wikitables found on variable-depth extractor pages (Mineshaft Drill is the only known example so far, but this is written
generically in case others turn up.

Each depth range (300m-2000m, 2200m-3000m, ...) is its own <table class="wikitable">, containing one row per depth: a <th> with the depth ("300M"), a conditions
<td> (power draw + cycle duration), and an output <td> listing several "<a>Item</a>-N/s" entries.

Real-data quirk this handles: at least one row in the live wiki data has a typo, "Rock</a>-11.65s" instead of "-11.65/s" (missing slash). The rate
regex tolerates the missing slash so this doesn't silently drop that output.
"""

from __future__ import annotations
import re
import sys

sys.path.append('..')
from bs4 import BeautifulSoup
from parse_items_list import derive_data_item_id
from Core.units import parse_power

DEPTH_RE = re.compile(r"([\d.]+)\s*M", re.IGNORECASE)
CYCLE_RE = re.compile(r"\+\s*([\d.]+)\s*s")
# Tolerates the real wiki's "-11.65s" typo (missing slash) as well as the normal "-3/s" form.
RATE_RE = re.compile(r"-\s*([\d.]+)\s*/?\s*s\b")


def parse_extractor_depth_tables(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    profiles = []

    for table in soup.find_all("table", class_="wikitable"):
        rows = table.find_all("tr")

        for row in rows:
            depth_th = row.find("th")
            tds = row.find_all("td")

            if depth_th is None or len(tds) != 2:
                continue  # header/title rows, not a data row

            depth_text = depth_th.get_text(strip=True)
            depth_match = DEPTH_RE.search(depth_text)

            if not depth_match:
                continue

            depth_m = float(depth_match.group(1))

            conditions_td, output_td = tds
            _, power_mf = parse_power(conditions_td.get_text())
            cycle_match = CYCLE_RE.search(conditions_td.get_text())
            cycle_seconds = float(cycle_match.group(1)) if cycle_match else None

            outputs = []
            for link in output_td.find_all("a", href=True):
                item_name = link.get_text(strip=True)
                # the rate ("-3/s") is plain text immediately after the <a>, not inside any tag, grab the next sibling text node.
                tail = link.next_sibling
                tail_text = str(tail) if tail else ""
                rate_match = RATE_RE.search(tail_text)

                if not rate_match:
                    continue

                slug = link["href"][len("/wiki/"):] if link["href"].startswith("/wiki/") else link["href"]

                outputs.append({
                    "item_id": derive_data_item_id(item_name),
                    "item_name": item_name,
                    "wiki_slug": slug,
                    "rate_per_s": float(rate_match.group(1)),
                })

            profiles.append({
                "depth_m": depth_m,
                "power_mf_per_s": power_mf,
                "cycle_seconds": cycle_seconds,
                "outputs": outputs,
            })

    return profiles