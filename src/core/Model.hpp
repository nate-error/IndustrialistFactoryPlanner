#pragma once

#include "core/Types.hpp"
#include "nlohmann/json.hpp"

namespace Industrialist {
// --- JSON parsing helpers ---

    using json = nlohmann::json;

    template <typename T>
    std::optional<T> GetOpt(const json& j, const char* key) {
        if (!j.contains(key) || j.at(key).is_null())
            return std::nullopt;

        return j.at(key).get<T>();
    }

    inline RecipeIngredient ParseIngredients(const json& j) {
        RecipeIngredient r;
        r.item_id = j.value("item_id", "");
        r.item_name = j.value("item_name", "");
        r.quantity = j.value("quantity", 0.0);

        return r;
    }

    inline Recipe ParseRecipe(const json& j) {
        Recipe r;
        r.id = j.value("id", "");
        r.machine_name = j.value("machine_name", "");
        r.machine_slug = GetOpt<std::string>(j, "machine_slug");
        r.duration_seconds = GetOpt<double>(j, "duration_seconds");
        r.power_rate_raw = GetOpt<std::string>(j, "power_rate_raw");
        r.power_rate_mf_per_s = GetOpt<double>(j, "power_rate_mf_per_s");

        if (j.contains("inputs"))
            for (const auto& i : j.at("inputs"))
                r.inputs.push_back(ParseIngredients(i));

        if (j.contains("outputs"))
            for (const auto& o : j.at("outputs"))
                r.outputs.push_back(ParseIngredients(o));

        if (j.contains("seen_on_pages"))
            for (const auto& p : j.at("seen_on_pages"))
                r.seen_on_pages.push_back(p.get<std::string>());

        return r;
    }

    inline Item ParseItem(const json& j) {
        Item it;
        it.id = j.value("id", "");
        it.name = j.value("name", "");
        it.wiki_slug = GetOpt<std::string>(j, "wiki_slug");
        it.wiki_url = GetOpt<std::string>(j, "wiki_url");
        it.money = GetOpt<double>(j, "money");
        it.research_points = GetOpt<double>(j, "research_points");
        it.category = GetOpt<std::string>(j, "category");
        it.icon_url = GetOpt<std::string>(j, "icon_url");

        return it;
    }

    inline Machine ParseMachine(const json& j) {
        Machine m;
        m.id = j.value("id", "");
        m.name = j.value("name", "");
        m.tier = GetOpt<int>(j, "tier");
        m.category = GetOpt<std::string>(j, "category");
        m.wiki_url = GetOpt<std::string>(j, "wiki_url");
        m.icon_url = GetOpt<std::string>(j, "icon_url");
        m.cost_money = GetOpt<double>(j, "cost_money");
        m.required_research = GetOpt<std::string>(j, "required_research");
        m.required_research_slug = GetOpt<std::string>(j, "required_research_slug");
        m.size_width = GetOpt<double>(j, "size_width");
        m.size_height = GetOpt<double>(j, "size_height");
        m.pollution_percent_per_hour = GetOpt<double>(j, "pollution_percent_per_hour");
        m.power_input_raw = GetOpt<std::string>(j, "power_input_raw");
        m.power_input_mf_per_s = GetOpt<double>(j, "power_input_mf_per_s");
        m.power_output_raw = GetOpt<std::string>(j, "power_output_raw");
        m.power_output_mf_per_s = GetOpt<double>(j, "power_output_mf_per_s");
        m.power_capacity_raw = GetOpt<std::string>(j, "power_capacity_raw");
        m.power_capacity_mf = GetOpt<double>(j, "power_capacity_mf");

        if (j.contains("products"))
        {
            for (const auto& p : j.at("products")) {
                MachineProduct mp;
                mp.display_text = p.value("display_text", "");

                if (p.contains("linked_item_slugs"))
                    for (const auto& s : p.at("linked_item_slugs")) mp.linked_item_slugs.push_back(s.get<std::string>());

                m.products.push_back(mp);
            }
        }

        if (j.contains("recipe_ids"))
            for (const auto& r : j.at("recipe_ids")) m.recipe_ids.push_back(r.get<std::string>());

        if (j.contains("infobox_raw_extra"))
            for (auto& [k, v] : j.at("infobox_raw_extra").items()) m.infobox_raw_extra[k] = v.get<std::string>();

        return m;
    }

    inline Research ParseResearch(const json& j) {
        Research r;
        r.id = j.value("id", "");
        r.name = j.value("name", "");
        r.cost_rp = GetOpt<double>(j, "cost_rp");

        if (j.contains("prerequisites"))
            for (const auto& p : j.at("prerequisites"))
                r.prerequisites.push_back(p.get<std::string>());

        if (j.contains("unlocks"))
            for (const auto& u : j.at("unlocks"))
                r.unlocks.push_back(u.get<std::string>());

        return r;
    }

    // -- Start of Mineshaft specific functions --

    inline ExtractorDepthOutput ParseExtractorDepthOutput(const json& j) {
        ExtractorDepthOutput o;
        o.item_id = j.value("item_id", "");
        o.item_name = j.value("item_name", "");
        o.wiki_slug = GetOpt<std::string>(j, "wiki_slug");
        o.rate_per_s = j.value("rate_per_s", 0.0);
        return o;
    }

    inline ExtractorDepthProfile ParseExtractorDepthProfile(const json& j) {
        ExtractorDepthProfile p;
        p.depth_m = j.value("depth_m", 0.0);
        p.power_mf_per_s = GetOpt<double>(j, "power_mf_per_s");
        p.cycle_seconds = GetOpt<double>(j, "cycle_seconds");

        if (j.contains("outputs"))
            for (const auto& o : j.at("outputs"))
                p.outputs.push_back(ParseExtractorDepthOutput(o));

        return p;
    }

    inline ExtractorConsumable ParseExtractorConsumable(const json& j) {
        ExtractorConsumable c;
        c.item_id = GetOpt<std::string>(j, "item_id");
        c.item_name = j.value("item_name", "");
        c.mandatory = j.value("mandatory", false);
        c.rate_per_s = GetOpt<double>(j, "rate_per_s");
        c.affects_yield = j.value("affects_yield", false);
        c.note = GetOpt<std::string>(j, "note");
        return c;
    }

    inline VariableExtractorProfile ParseVariableExtractorProfile(const json& j) {
        VariableExtractorProfile p;
        p.machine_id = j.value("machine_id", "");
        if (j.contains("depth_profiles"))
            for (const auto& d : j.at("depth_profiles"))
                p.depth_profiles.push_back(ParseExtractorDepthProfile(d));

        if (j.contains("consumables"))
            for (const auto& c : j.at("consumables"))
                p.consumables.push_back(ParseExtractorConsumable(c));

        if (j.contains("unmodeled_notes"))
            for (const auto& n : j.at("unmodeled_notes"))
                p.unmodeled_notes.push_back(n.get<std::string>());

        return p;
    }

    // -- End of Mineshaft specific functions --

    inline Database LoadDatabase(const json& root) {
        Database db;
        if (root.contains("items"))
            for (auto& [id, v] : root.at("items").items())
                db.items[id] = ParseItem(v);

        if (root.contains("machines"))
            for (auto& [id, v] : root.at("machines").items())
                db.machines[id] = ParseMachine(v);

        if (root.contains("recipes"))
            for (auto& [id, v] : root.at("recipes").items())
                db.recipes[id] = ParseRecipe(v);

        if (root.contains("research"))
            for (auto& [id, v] : root.at("research").items())
                db.research[id] = ParseResearch(v);

        if (root.contains("variable_extractors"))
            for (auto& [id, v] : root.at("variable_extractors").items())
                db.variable_extractors[id] = ParseVariableExtractorProfile(v);

        return db;
    }

} // namespace Industrialist
