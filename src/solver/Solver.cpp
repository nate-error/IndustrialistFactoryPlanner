#include "Solver.hpp"

namespace Industrialist {

    SolveResult Solver::Solve(const std::string& target_item_id, double target_rate_per_s) {
        SolveResult result;
        std::unordered_set<std::string> path; // Current DFS ancestors, for cycle detection
        result.root = Resolve(target_item_id, target_rate_per_s, path, result.warnings);
        Aggregate(result.root, result);

        std::sort(result.required_research.begin(), result.required_research.end());
        result.required_research.erase(std::unique(result.required_research.begin(), result.required_research.end()), result.required_research.end());

        return result;
    }



    void Solver::BuildProducerIndex() {
        for (const auto& [recipe_id, recipe] : db_.recipes) {
            for (const auto& out : recipe.outputs) {
                producers_[out.item_id].push_back(recipe_id);
            }
        }

        for (auto& [item_id, ids] : producers_) {
            std::sort(ids.begin(), ids.end());
        }
    }

    std::optional<std::string> Solver::PickRecipeFor(const std::string& item_id, size_t& alt_count) {
        auto it = producers_.find(item_id);

        if (it == producers_.end() || it->second.empty()) {
            alt_count = 0;
            return std::nullopt;
        }

        alt_count = it->second.size() - 1;

        return it->second.front();
    }

    ResolvedNode Solver::Resolve(const std::string& item_id, double rate_per_s, std::unordered_set<std::string>& path, std::vector<std::string>& warnings) {
        ResolvedNode node;
        node.item_id = item_id;
        node.rate_per_s = rate_per_s;

        auto item_it = db_.items.find(item_id);
        node.item_name = (item_it != db_.items.end()) ? item_it->second.name : item_id;

        if (path.count(item_id)) {
            node.is_cycle_break = true;
            warnings.push_back("Cycle detected: '" + item_id + "' is its own ancestor in this chain -- stopped recursing here (Phase 6: make production loops).");
            return node;
        }

        size_t alt_count = 0;
        auto recipe_id_opt = PickRecipeFor(item_id, alt_count);

        if (!recipe_id_opt) {
            node.is_raw_resource = true;
            return node;
        }

        const Recipe& recipe = db_.recipes.at(*recipe_id_opt);
        node.recipe_id = recipe.id;
        node.machine_id = recipe.machine_slug;
        node.alternative_recipe_count = alt_count;

        // Find how much of item_id this recipe produces per run, and over what duration, to get this recipe's per machine output rate
        double output_qty_per_run = 0.0;
        for (const auto& out : recipe.outputs) {
            if (out.item_id == item_id) {
                output_qty_per_run = out.quantity;
                break;
            }
        }

        double duration = recipe.duration_seconds.value_or(0.0);
        double per_machine_rate = (duration > 0.0) ? (output_qty_per_run / duration) : 0.0;

        if (per_machine_rate <= 0.0) {
            warnings.push_back("Recipe '" + recipe.id + "' has no usable duration/output for '" + item_id + "' -- can't compute machine count, treating as raw resource.");

            node.is_raw_resource = true;
            node.recipe_id.reset();
            node.machine_id.reset();
            return node;
        }

        node.machines_theoretical = rate_per_s / per_machine_rate;
        node.machines_actual = static_cast<int>(std::ceil(node.machines_theoretical - 1e-9));
        if (node.machines_actual < 1)
            node.machines_actual = 1;

        // Propagate
        path.insert(item_id);
        for (const auto& in : recipe.inputs) {
            double input_rate = node.machines_theoretical * (in.quantity / duration);
            node.children.push_back(Resolve(in.item_id, input_rate, path, warnings));
        }

        path.erase(item_id);

        return node;
    }

    void Solver::Aggregate(const ResolvedNode& node, SolveResult& result) {
        if (node.is_raw_resource) {
            result.raw_resource_rates[node.item_id] += node.rate_per_s;
            return;
        }

        if (node.is_cycle_break) {
            return;
        }

        if (node.recipe_id) {
            result.machines_by_recipe[*node.recipe_id] += node.machines_actual;

            const Recipe& recipe = db_.recipes.at(*node.recipe_id);
            if (recipe.power_rate_mf_per_s) {
                result.total_power_mf_per_s += node.machines_actual * (*recipe.power_rate_mf_per_s);
            }

            if (node.machine_id && db_.machines.count(*node.machine_id)) {
                const Machine& m = db_.machines.at(*node.machine_id);
                if (m.cost_money) result.total_cost_money += node.machines_actual * (*m.cost_money);
                if (m.pollution_percent_per_hour)
                    result.total_pollution_percent_per_hour += node.machines_actual * (*m.pollution_percent_per_hour);
                if (m.required_research) result.required_research.push_back(*m.required_research);
            }
            else {
                result.warnings.push_back("Machine '" + node.machine_id.value_or("?") + "' referenced by recipe '" + *node.recipe_id +
                    "' has no machine record (cost/pollution/research omitted for it).");
            }
        }

        for (const auto& child : node.children) {
            Aggregate(child, result);
        }
    }

} // namespace Industrialist