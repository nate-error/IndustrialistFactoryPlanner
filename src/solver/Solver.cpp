#include "Solver.hpp"

#include "utils/Utils.hpp"

namespace Industrialist {

    SolveResult Solver::Solve(const std::string& targetItemId, double targetRatePerSeconds) {
        SolveResult result;
        std::unordered_set<std::string> path; // Current DFS ancestors, for cycle detection
        result.root = Resolve(targetItemId, targetRatePerSeconds, path, result.warnings);
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

    std::optional<std::string> Solver::PickRecipeFor(const std::string& itemId, double targetRatePerSeconds, size_t& altCount) {
        auto it = producers_.find(itemId);

        if (it == producers_.end() || it->second.empty()) {
            altCount = 0;
            return std::nullopt;
        }

        altCount = it->second.size() - 1;

        std::string bestRecipeId;
        double lowestScore = std::numeric_limits<double>::max();

        for (const auto& recipeId : it->second) {
            auto recipeIterator = db_.recipes.find(recipeId);

            if (recipeIterator == db_.recipes.end())
                continue;

            const Recipe& recipe = recipeIterator->second;

            double score = CalculateRecipeScore(recipe, itemId, targetRatePerSeconds, db_);

            if (score < lowestScore) {
                lowestScore = score;
                bestRecipeId = recipe.id;
            }
        }
        // Fallback to first recipe if no valid duration/rate was calculated
        if (bestRecipeId.empty()) {
            return it->second.front();
        }

        return bestRecipeId;
    }

    ResolvedNode Solver::Resolve(const std::string& itemId, double ratePerSeconds, std::unordered_set<std::string>& path, std::vector<std::string>& warnings) {
        ResolvedNode node;
        node.item_id = itemId;
        node.rate_per_s = ratePerSeconds;

        auto itemIterator = db_.items.find(itemId);
        node.item_name = (itemIterator != db_.items.end()) ? itemIterator->second.name : itemId;

        if (path.count(itemId)) {
            node.is_cycle_break = true;
            warnings.push_back("Cycle detected: '" + itemId + "' is its own ancestor in this chain -- stopped recursing here (Phase 6: make production loops).");
            return node;
        }

        size_t altCount = 0;
        std::optional<std::string> recipeIdOpt = PickRecipeFor(itemId, ratePerSeconds, altCount);

        if (!recipeIdOpt) {
            node.is_raw_resource = true;
            return node;
        }

        const Recipe& recipe = db_.recipes.at(*recipeIdOpt);
        node.recipe_id = recipe.id;
        node.machine_id = recipe.machine_slug;
        node.alternative_recipe_count = altCount;

        // Find how much of item_id this recipe produces per run, and over what duration, to get this recipe's per machine output rate
        double outputQtyPerRun = 0.0;
        for (const auto& out : recipe.outputs) {
            if (out.item_id == itemId) {
                outputQtyPerRun = out.quantity;
                break;
            }
        }

        double duration = recipe.duration_seconds.value_or(0.0);
        double perMachineRate = (duration > 0.0) ? (outputQtyPerRun / duration) : 0.0;

        if (perMachineRate <= 0.0) {
            warnings.push_back("Recipe '" + recipe.id + "' has no usable duration/output for '" + itemId + "' -- can't compute machine count, treating as raw resource.");

            node.is_raw_resource = true;
            node.recipe_id.reset();
            node.machine_id.reset();
            return node;
        }

        node.machines_theoretical = ratePerSeconds / perMachineRate;
        node.machines_actual = static_cast<int>(std::ceil(node.machines_theoretical - 1e-9));
        if (node.machines_actual < 1)
            node.machines_actual = 1;

        // Propagate
        path.insert(itemId);
        for (const auto& in : recipe.inputs) {
            double inputRate = node.machines_theoretical * (in.quantity / duration);
            node.children.push_back(Resolve(in.item_id, inputRate, path, warnings));
        }

        path.erase(itemId);

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