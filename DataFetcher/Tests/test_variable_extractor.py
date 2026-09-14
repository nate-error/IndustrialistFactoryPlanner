import sys

sys.path.append('..')
from Core.schemas import VariableExtractorProfile, ExtractorDepthProfile, ExtractorDepthOutput
from parse_extractor_depth_table import parse_extractor_depth_tables
from variable_extractors_data import MINESHAFT_DRILL_CONSUMABLES, MINESHAFT_DRILL_NOTES

html = open("fixtures/mineshaft_drill_depth_tables_sample.html", encoding="utf-8").read()
depth_rows = parse_extractor_depth_tables(html)

profile = VariableExtractorProfile(
    machine_id="Mineshaft_Drill",
    depth_profiles=[
        ExtractorDepthProfile(
            depth_m=row["depth_m"], power_mf_per_s=row["power_mf_per_s"],
            cycle_seconds=row["cycle_seconds"],
            outputs=[ExtractorDepthOutput(**o) for o in row["outputs"]],
        )
        for row in depth_rows
    ],
    consumables=MINESHAFT_DRILL_CONSUMABLES,
    unmodeled_notes=MINESHAFT_DRILL_NOTES,
)

assert len(profile.depth_profiles) == 3
assert {c.item_name for c in profile.consumables} == {
    "Drill Heads", "Water", "Acetic Acid", "Hydrochloric Acid", "Sulfuric Acid", "Machine Oil"
}

drill_heads = next(c for c in profile.consumables if c.item_name == "Drill Heads")
assert drill_heads.mandatory is True
assert drill_heads.rate_per_s is None  # honestly unmodeled, not guessed

machine_oil = next(c for c in profile.consumables if c.item_name == "Machine Oil")
assert machine_oil.affects_yield is True
assert machine_oil.rate_per_s == 2.0

acid_options = [c for c in profile.consumables if c.item_name != "Drill Heads" and c.item_name != "Machine Oil"]
assert len(acid_options) == 4  # Water + 3 acids, all mandatory=False (mutually exclusive picks)
assert all(not c.mandatory for c in acid_options)

assert profile.unmodeled_notes == ["Machine has a 5th output port (fluid) that is currently unused / outputs nothing."]

# round-trip through JSON like the real pipeline does
round_tripped = VariableExtractorProfile.model_validate_json(profile.model_dump_json())
assert round_tripped == profile

print("test_variable_extractor.py: all assertions passed")
print(f"  {len(profile.depth_profiles)} depth profiles, {len(profile.consumables)} consumables")