"""
Data for extractors whose output depends on a parameter (currently: depth) rather than a fixed recipe. Two parts, sourced very differently:

  - depth_profiles: scraped structurally via parse_extractor_depth_table.py from the machine's own wikitable, reliable, re-scrapable.
  - consumables: HAND-TRANSCRIBED from prose paragraphs on the machine's wiki page, because that data isn't in any clean table, it's sentences
    like "Machine Oil is only consumed during drill operation at a rate of 2L/s." There's no reliable way to regex a specific number out of free
    prose without risking silently grabbing the wrong sentence's number, so these are typed in by hand and will NOT auto-update if the wiki changes.
    If Mineshaft Drill's mechanics get rebalanced, this needs a manual edit.
"""

from __future__ import annotations
from Core.schemas import ExtractorConsumable

KNOWN_VARIABLE_EXTRACTORS = {"Mineshaft_Drill"}

MINESHAFT_DRILL_CONSUMABLES = [
    ExtractorConsumable(
    item_id="drill-heads",
    item_name="Drill Heads",
    mandatory=True,
    rate_per_s=1.0 / 500.0,  # ~0.002/s, empirical estimate for Steel Drill Head + Sulfuric/Hydrochloric Acid, amortized over a full dig-until-death + retract-to-surface
    # + redescend cycle. NOT depth-adjusted, 500s is a single ballpark figure, not derived from the durability formula. Flat per-machine rate, independent of target ore
    # throughput (see note above). This will probably overshoot by a lot but better have more than less, at least until i do the proper calculations.
    affects_yield=False,
    note="~500s between replacements for Steel Drill Head + Sulfuric/Hydrochloric Acid (most common setup, Tungsten too expensive, Iron less durable than Steel for"
    "somewhat similar build cost from what i could see). Not depth adjusted; real rate follows the wiki's Durability Loss Rate formula (Drill Multiplier x Acid Multiplier"
    "x Resource Modifier x Speed Modifier), which isn't fully modeled here yet."
),
    # "Water" here is one of five interchangeable choices (Water or one of four Acids), the wiki explicitly calls this "Water/most Acids", i.e.
    # pick exactly one. Consumption rates ARE plainly stated in prose, so these are trustworthy despite being hand-typed.
    ExtractorConsumable(item_id="water", item_name="Water", mandatory=False, rate_per_s=10.0, affects_yield=False,
                        note="One of 5 mutually exclusive durability-boost options; pick one."),
    ExtractorConsumable(item_id="acetic-acid", item_name="Acetic Acid", mandatory=False, rate_per_s=3.0, affects_yield=False,
                        note="One of 5 mutually exclusive durability-boost options; pick one."),
    ExtractorConsumable(item_id="hydrochloric-acid", item_name="Hydrochloric Acid", mandatory=False, rate_per_s=1.5, affects_yield=False,
                        note="One of 5 mutually exclusive durability-boost options; pick one."),
    ExtractorConsumable(item_id="sulfuric-acid", item_name="Sulfuric Acid", mandatory=False, rate_per_s=1.0, affects_yield=False,
                        note="One of 5 mutually exclusive durability-boost options; pick one. Wiki recommends Sulfuric or Hydrochloric Acid over Water."),
    ExtractorConsumable(item_id="machine-oil", item_name="Machine Oil", mandatory=False, rate_per_s=2.0, affects_yield=True,
        note="+10% resource output at +10% durability loss (roughly break-even resources per drill head over its life); also doubles dig/travel speed.",
    ),
    # Dynamite deliberately excluded, affects dig SPEED (how fast the target depth is reached) only, not steady state output rate or resource
    # consumption once at depth. Not relevant to a throughput calculator.
]

# The wiki states: "It has 5 outputs, 4 for the outputted items, and 1 for an unused fluid output." That 5th port produces nothing, recorded here
# so it doesn't look like a scraping gap later, not modeled as a resource.
MINESHAFT_DRILL_NOTES = [
    "Machine has a 5th output port (fluid) that is currently unused / outputs nothing.",
]
