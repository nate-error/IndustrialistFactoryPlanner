sys.path.append('..')
from parse_recipes import parse_production_wrapper

with open("fixtures/gold_production_sample.html", encoding="utf-8") as f:
    html = f.read()

recipes = parse_production_wrapper(html, source_page="10_Karat_Gold")

print(f"Parsed {len(recipes)} recipes:\n")
for r in recipes:
    ins = ", ".join(f"{i.quantity}x {i.item_name}" for i in r.inputs)
    outs = ", ".join(f"{o.quantity}x {o.item_name}" for o in r.outputs)
    print(f"[{r.id}]  ({r.machine_name} / slug={r.machine_slug})")
    print(f"    {ins}")
    print(f"    --{r.duration_seconds}s, {r.power_rate_raw}-->")
    print(f"    {outs}")
    print()

assert len(recipes) == 4, f"expected 4 recipes, got {len(recipes)}"

by_id = {r.id: r for r in recipes}
assert "gold_acid_refinery_01" in by_id
assert "trommel_05" in by_id
assert "industrial_electric_furnace_04" in by_id
assert "pressurized_water_filter_02" in by_id

gar = by_id["gold_acid_refinery_01"]
assert gar.machine_name == "Gold Acid Refinery"
assert gar.duration_seconds == 5.0
assert gar.power_rate_raw == "100kMF/s"
assert gar.power_rate_mf_per_s == 100_000
assert {(i.item_id, i.quantity) for i in gar.inputs} == {
    ("acetic-acid", 2.0), ("water", 6.0), ("rich-soil", 1.0)
}
assert {(o.item_id, o.quantity) for o in gar.outputs} == {
    ("residue", 8.0), ("10-karat-gold", 1.0)
}

trommel = by_id["trommel_05"]
assert len(trommel.inputs) == 2   # water, treated-rock
assert len(trommel.outputs) == 4  # 10-karat-gold, rich-soil, raw-lead, bauxite-residue

print("All assertions passed.")
