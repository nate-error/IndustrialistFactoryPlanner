sys.path.append('..')
from parse_machine_infobox import parse_machine_infobox

html = open("fixtures/machine_infobox_geothermal_well.html", encoding="utf-8").read()
info = parse_machine_infobox(html)

assert info["name"] == "Geothermal Well"
assert info["tier"] == 2
assert info["cost_money"] == 1500.0
assert info["required_research"] == "Geothermal Plant"
assert info["required_research_slug"] == "Node_Geothermal_Plant"
assert info["size_width"] == 8.0
assert info["size_height"] == 5.0
assert info["products"] == [{"text": "Hot Water", "linked_item_slugs": ["Water"]}]
assert info["pollution_percent_per_hour"] == 0.0
assert info["power_input_raw"] == "\u26a13kMF/s"
assert info["power_input_mf_per_s"] == 3000.0
assert info["power_output_mf_per_s"] is None
assert info["power_capacity_raw"] == "\u26a150kMF"
assert info["power_capacity_mf"] == 50000.0
assert info["raw"] == {}

print("test_parse_machine_infobox.py: all assertions passed")
