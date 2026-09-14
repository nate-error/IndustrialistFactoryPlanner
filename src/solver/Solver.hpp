#pragma once
#include "Core/Model.hpp"
#include <memory>
#include <unordered_set>
#include <cmath>
#include <algorithm>
#include <sstream>

namespace Industrialist {

    struct ResolvedNode {
        std::string item_id;
        std::string item_name;
        double rate_per_s = 0.0;

        // Only set if this item is actually produced by a recipe (raw resources, and items whose only "recipe" would be a cycle we broke, leave these empty):
        std::optional<std::string> recipe_id;
        std::optional<std::string> machine_id;
        double machines_theoretical = 0.0;
        int machines_actual = 0; // ceil(machines_theoretical)
        size_t alternative_recipe_count = 0;

        bool is_raw_resource = false;
        bool is_cycle_break = false;

        std::vector<ResolvedNode> children; // Resolved inputs, in recipe input order
    };

    struct SolveResult {
        ResolvedNode root;

        std::unordered_map<std::string, int> machines_by_recipe; // recipe_id -> actual machine count
        std::unordered_map<std::string, double> raw_resource_rates; // item_id -> items/sec needed
        double total_power_mf_per_s = 0.0;
        double total_pollution_percent_per_hour = 0.0;
        double total_cost_money = 0.0;
        std::vector<std::string> required_research;
        std::vector<std::string> warnings; // cycles hit, missing data, etc.
    };

    class Solver {
    public:
        explicit Solver(const Database& db) : db_(db) {
            BuildProducerIndex();
        }

        SolveResult Solve(const std::string& target_item_id, double target_rate_per_s);

    private:
        const Database& db_;
        std::unordered_map<std::string, std::vector<std::string>> producers_; // item_id -> recipe_ids that output it

        void BuildProducerIndex();

        std::optional<std::string> PickRecipeFor(const std::string& item_id, size_t& alt_count);

        ResolvedNode Resolve(const std::string& item_id, double rate_per_s, std::unordered_set<std::string>& path, std::vector<std::string>& warnings);

        void Aggregate(const ResolvedNode& node, SolveResult& result);
    };

} // namespace Industrialist