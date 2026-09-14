"""
These are intentionally loose (lots of Optional[...]) because the wiki data is inconsistent in coverage. validate.py is where we decide what's
"good enough" vs a red flag. Keeping the schema permissive means the scraper never crashes on a page that's missing a field; it just produces a
record with holes in it, which the validator then reports.
"""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


class RecipeIngredient(BaseModel):
    item_id: str # slug, e.g. "acetic-acid", matches Item.id
    item_name: str # display name, e.g. "Acetic Acid" (denormalized for convenience/debugging)
    quantity: float # e.g. 2.0 for "2x"


class Recipe(BaseModel):
    id: str # e.g. "gold_acid_refinery_01" (from data-recipe-id)
    machine_name: str # e.g. "Gold Acid Refinery"
    machine_slug: Optional[str] = None # derived from the /wiki/Machine_Name link, if present
    inputs: list[RecipeIngredient] = Field(default_factory=list)
    outputs: list[RecipeIngredient] = Field(default_factory=list)
    duration_seconds: Optional[float] = None
    power_rate_raw: Optional[str] = None # raw string as shown, e.g. "100kMF/s"
    power_rate_mf_per_s: Optional[float] = None # parsed via units.parse_power (MF/kMF/MMF/GMF/TMF/PMF)

    # provenance: which wiki page(s) we saw this recipe block on. A single recipe shows up once per item it touches (once in that item's Sources
    # or Uses section), so this lets the normalizer de duplicate safely.
    seen_on_pages: list[str] = Field(default_factory=list)


class Item(BaseModel):
    id: str # canonical slug matching recipes' data-item attributes, e.g. "10-karat-gold" — NOT the wiki page slug (see wiki_slug)
    name: str # display name, e.g. "10 Karat Gold"
    wiki_slug: Optional[str] = None  # the /wiki/X page slug, e.g. "10_Karat_Gold"; different convention (underscored, original case) than `id`. Needed
     # to construct wiki_url / re-fetch the page; NOT safe to use for matching against recipe ingredients.
    wiki_url: Optional[str] = None
    money: Optional[float] = None
    research_points: Optional[float] = None
    category: Optional[str] = None  # Not on the master Items gallery; fill in later if the wiki exposes it
    icon_url: Optional[str] = None


class MachinePort(BaseModel):
    kind: str # "item" | "fluid" | "power"
    direction: str # "input" | "output"
    resource: Optional[str] = None # item/fluid id this port accepts, if restricted


class MachineProduct(BaseModel):
    display_text: str # e.g. "Hot Water"; may be a display-level variant of a base item rather than a distinct item-database entry (see note in parse_machine_infobox.py)
    linked_item_slugs: list[str] = Field(default_factory=list)


class Machine(BaseModel):
    id: str # slug, e.g. "Geothermal_Well"
    name: str # e.g. "Geothermal Well"
    tier: Optional[int] = None # from the "tier_N" class on the infobox
    category: Optional[str] = None # e.g. "Power", "Extractors", "Factories", ... (from the gallery it was found under)
    wiki_url: Optional[str] = None
    icon_url: Optional[str] = None
    cost_money: Optional[float] = None
    required_research: Optional[str] = None
    required_research_slug: Optional[str] = None
    size_width: Optional[float] = None
    size_height: Optional[float] = None
    products: list[MachineProduct] = Field(default_factory=list)
    pollution_percent_per_hour: Optional[float] = None
    power_input_raw: Optional[str] = None
    power_input_mf_per_s: Optional[float] = None
    power_output_raw: Optional[str] = None
    power_output_mf_per_s: Optional[float] = None
    power_capacity_raw: Optional[str] = None
    power_capacity_mf: Optional[float] = None
    recipe_ids: list[str] = Field(default_factory=list) # recipes that name this machine
    infobox_raw_extra: dict[str, str] = Field(default_factory=dict) # unmapped (category:label) -> text, for forward-compat


class Research(BaseModel):
    id: str
    name: str
    cost_rp: Optional[float] = None
    prerequisites: list[str] = Field(default_factory=list)
    unlocks: list[str] = Field(default_factory=list)


class Database(BaseModel):
    """The full normalized database."""
    items: dict[str, Item] = Field(default_factory=dict)
    machines: dict[str, Machine] = Field(default_factory=dict)
    recipes: dict[str, Recipe] = Field(default_factory=dict)
    research: dict[str, Research] = Field(default_factory=dict)
