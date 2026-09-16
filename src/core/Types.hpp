#pragma once

#include <string>
#include <vector>
#include <unordered_map>
#include <optional>

namespace Industrialist {

    struct RecipeIngredient {
        std::string item_id;
        std::string item_name;
        double quantity = 0.0;
    };

    struct Recipe {
        std::string id;
        std::string machine_name;
        std::optional<std::string> machine_slug;
        std::vector<RecipeIngredient> inputs;
        std::vector<RecipeIngredient> outputs;
        std::optional<double> duration_seconds;
        std::optional<std::string> power_rate_raw;
        std::optional<double> power_rate_mf_per_s;
        std::vector<std::string> seen_on_pages;
    };

    struct Item {
        std::string id;
        std::string name;
        std::optional<std::string> wiki_slug;
        std::optional<std::string> wiki_url;
        std::optional<double> money;
        std::optional<double> research_points;
        std::optional<std::string> category;
        std::optional<std::string> icon_url;
    };

    struct MachineProduct {
        std::string display_text;
        std::vector<std::string> linked_item_slugs;
    };

    struct Machine {
        std::string id;
        std::string name;
        std::optional<int> tier;
        std::optional<std::string> category;
        std::optional<std::string> wiki_url;
        std::optional<std::string> icon_url;
        std::optional<double> cost_money;
        std::optional<std::string> required_research;
        std::optional<std::string> required_research_slug;
        std::optional<double> size_width;
        std::optional<double> size_height;
        std::vector<MachineProduct> products;
        std::optional<double> pollution_percent_per_hour;
        std::optional<std::string> power_input_raw;
        std::optional<double> power_input_mf_per_s;
        std::optional<std::string> power_output_raw;
        std::optional<double> power_output_mf_per_s;
        std::optional<std::string> power_capacity_raw;
        std::optional<double> power_capacity_mf;
        std::vector<std::string> recipe_ids;
        std::unordered_map<std::string, std::string> infobox_raw_extra;
    };

    struct Research {
        std::string id;
        std::string name;
        std::optional<double> cost_rp;
        std::vector<std::string> prerequisites;
        std::vector<std::string> unlocks;
    };

    // -- Start of Mineshaft specific types --

    struct ExtractorDepthOutput {
        std::string item_id;
        std::string item_name;
        std::optional<std::string> wiki_slug;
        double rate_per_s = 0.0;
    };

    struct ExtractorDepthProfile {
        double depth_m = 0.0;
        std::optional<double> power_mf_per_s;
        std::optional<double> cycle_seconds;
        std::vector<ExtractorDepthOutput> outputs;
    };

    struct ExtractorConsumable {
        std::optional<std::string> item_id;
        std::string item_name;
        bool mandatory = false;
        std::optional<double> rate_per_s; // nullopt where the real rate depends on an unmodeled formula (e.g. Drill Heads)
        bool affects_yield = false; // true only for things that change output rate
        std::optional<std::string> note;
    };

    struct VariableExtractorProfile {
        std::string machine_id;
        std::vector<ExtractorDepthProfile> depth_profiles;
        std::vector<ExtractorConsumable> consumables;
        std::vector<std::string> unmodeled_notes;
    };
    // -- End of Mineshaft specific types --

    struct Database {
        std::unordered_map<std::string, Item> items;
        std::unordered_map<std::string, Machine> machines;
        std::unordered_map<std::string, Recipe> recipes;
        std::unordered_map<std::string, Research> research;
        std::unordered_map<std::string, VariableExtractorProfile> variable_extractors;
    };
} // namespace Industrialist
