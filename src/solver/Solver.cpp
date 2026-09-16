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

    const Recipe* Solver::GetRecipe(const std::string& recipeId) const {
        auto it = db_.recipes.find(recipeId);
        if (it != db_.recipes.end()) {
            return &it->second;
        }

        auto synthIt = synthetic_recipes_.find(recipeId);
        if (synthIt != synthetic_recipes_.end()) {
            return &synthIt->second;
        }

        return nullptr;
    }

    void Solver::BuildProducerIndex() {
        producers_.clear();
        synthetic_recipes_.clear();

        // Index standard recipes
        for (const auto& [recipe_id, recipe] : db_.recipes) {
            for (const auto& out : recipe.outputs) {
                producers_[out.item_id].push_back(recipe_id);
            }
        }

        // Synthesize recipes for Variable Extractors (Mineshaft Drill)
        for (const auto& [ve_id, ve] : db_.variable_extractors) {
            std::string machineName = ve.machine_id;
            if (db_.machines.count(ve.machine_id)) {
                machineName = db_.machines.at(ve.machine_id).name;
            }

            for (const auto& dp : ve.depth_profiles) {
                std::string recipeId = "ve:" + ve.machine_id + ":depth_" + std::to_string(static_cast<int>(dp.depth_m));

                Recipe syntheticRecipe;
                syntheticRecipe.id = recipeId;
                syntheticRecipe.machine_name = machineName;
                syntheticRecipe.machine_slug = ve.machine_id;

                double duration = dp.cycle_seconds.value_or(1.0);
                if (duration <= 0.0) duration = 1.0;
                syntheticRecipe.duration_seconds = duration;

                // Power rate from depth profile or machine default
                if (dp.power_mf_per_s.has_value()) {
                    syntheticRecipe.power_rate_mf_per_s = dp.power_mf_per_s;
                }
                else if (db_.machines.count(ve.machine_id) && db_.machines.at(ve.machine_id).power_input_mf_per_s) {
                    syntheticRecipe.power_rate_mf_per_s = db_.machines.at(ve.machine_id).power_input_mf_per_s;
                }

                // Mandatory consumables as recipe inputs
                for (const auto& cons : ve.consumables) {
                    if (cons.mandatory) {
                        RecipeIngredient ing;
                        ing.item_id = cons.item_id.value_or("");

                        if (ing.item_id.empty() && !cons.item_name.empty()) {
                            auto resolved = ResolveItemID(db_, cons.item_name);
                            if (resolved) ing.item_id = *resolved;
                        }

                        ing.item_name = cons.item_name;
                        double rate = cons.rate_per_s.value_or(0.0);
                        ing.quantity = rate * duration;

                        if (!ing.item_id.empty()) {
                            syntheticRecipe.inputs.push_back(ing);
                        }
                    }
                }

                // Extractor outputs
                for (const auto& out : dp.outputs) {
                    RecipeIngredient ing;
                    ing.item_id = out.item_id;
                    ing.item_name = out.item_name;
                    ing.quantity = out.rate_per_s * duration;

                    syntheticRecipe.outputs.push_back(ing);
                    producers_[out.item_id].push_back(recipeId);
                }

                synthetic_recipes_[recipeId] = syntheticRecipe;
            }
        }

        // Sort for deterministic iteration order
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
            const Recipe* recipePtr = GetRecipe(recipeId);
            if (!recipePtr)
                continue;

            const Recipe& recipe = *recipePtr;
            double score = CalculateRecipeScore(recipe, itemId, targetRatePerSeconds, db_);

            if (score < lowestScore) {
                lowestScore = score;
                bestRecipeId = recipe.id;
            }
        }

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

        const Recipe* recipePtr = GetRecipe(*recipeIdOpt);
        if (!recipePtr) {
            node.is_raw_resource = true;
            return node;
        }

        const Recipe& recipe = *recipePtr;
        node.recipe_id = recipe.id;
        node.machine_id = recipe.machine_slug;
        node.alternative_recipe_count = altCount;

        // Propagate unmodeled notes if a variable extractor profile was chosen
        if (recipe.machine_slug && db_.variable_extractors.count(*recipe.machine_slug)) {
            const auto& ve = db_.variable_extractors.at(*recipe.machine_slug);
            for (const auto& note : ve.unmodeled_notes) {
                warnings.push_back("Variable extractor '" + ve.machine_id + "' note: " + note);
            }
        }

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

        // Propagate recursively through inputs
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

            const Recipe* recipePtr = GetRecipe(*node.recipe_id);
            if (recipePtr && recipePtr->power_rate_mf_per_s) {
                result.total_power_mf_per_s += node.machines_actual * (*recipePtr->power_rate_mf_per_s);
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