#pragma once
#include <iostream>
#include <string>
#include <algorithm>
#include <cctype>
#include <optional>
#include <iomanip>

namespace Industrialist {

    constexpr double MACHINE_COUNT_PENALTY = 5.0;
    constexpr double BYPRODUCT_PENALTY = 5.0;
    constexpr double RESIDUE_PENALTY = 100.0;
    constexpr double INPUT_COMPLEXITY_PENALTY = 5.0;
    constexpr double POWER_PENALTY = 0.00001;
    constexpr double MONEY_PENALTY = 0.00005;
    constexpr double POLLUTION_PENALTY = 0.1;
    constexpr double RATE_PRECISION_PENALTY = 0.01; // How far its off from the target; tie breaker


    inline std::string ToLower(std::string s) {
        std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c) { return std::tolower(c); });
        return s;
    }

    // Accepts an item id (e.g. "10-karat-gold"), a wiki slug (e.g. "10_Karat_Gold"), or a display name (e.g. "10 Karat Gold", case-insensitive) and returns the
    // canonical item_id used as the key in Database::items.
    inline std::optional<std::string> ResolveItemID(const Database& db, const std::string& query) {
        if (db.items.count(query)) return query;

        std::string queryLowerCase = ToLower(query);
        for (const auto& [id, item] : db.items) {
            if (ToLower(item.name) == queryLowerCase)
                return id;

            if (item.wiki_slug && ToLower(*item.wiki_slug) == queryLowerCase)
                return id;
        }

        return std::nullopt;
    }

    // Calculate the score for a machine based on input/output complexity, money, energy, pollution, and residue output. These are default values that will later be 
    // modifiable by the user's need (this is an attempt at making a somewhat optimized score calculation)
    inline double CalculateRecipeScore(const Recipe& recipe, const std::string& itemId, double targetRatePerSeconds, const Database& db) {
        // Calculate production rate
        double outputQty = 0.0;
        for (const auto& output : recipe.outputs) {
            if (output.item_id == itemId) {
                outputQty = output.quantity;
                break;
            }
        }

        double duration = recipe.duration_seconds.value_or(0.0);
        if (duration <= 0.0 || outputQty <= 0.0)
            return std::numeric_limits<double>::max();

        double perMachineRate = outputQty / duration;

        // Theoretical machines needed to meet target rate (continuous scale prevents discontinuous jump penalties)
        double machinesNeeded = std::ceil(targetRatePerSeconds / perMachineRate);

        // Machine Count / Footprint Penalty
        // Higher weight forces solver to favor space efficient machines over massive arrays (tier 1 machines would always win otherwise)
        
        double machineCountPenalty = machinesNeeded * MACHINE_COUNT_PENALTY;

        // Structural Complexity Penalties
        // Penalize secondary outputs (extra outputs add unwanted transport/clogging complexity)
        double byproductPenalty = static_cast<double>(recipe.outputs.size() - 1) * BYPRODUCT_PENALTY;

        // Extra penalty for unusable or difficult residue items
        double residuePenalty = 0.0;
        for (const auto& byproduct : recipe.outputs) {
            if (byproduct.item_name == "residue") {
                residuePenalty += RESIDUE_PENALTY;
            }
        }

        // Penalize recipes requiring many input items (complex supply chains)
        double inputComplexityPenalty = static_cast<double>(recipe.inputs.size()) * INPUT_COMPLEXITY_PENALTY;

        // Normalized operational & capital penalties (scaled by throughput required)
        double powerPenalty = (recipe.power_rate_mf_per_s.value_or(0.0) * machinesNeeded) * POWER_PENALTY;

        double moneyPenalty = 0.0;
        double pollutionPenalty = 0.0;

        if (recipe.machine_slug && db.machines.count(*recipe.machine_slug)) {
            const Machine& machine = db.machines.at(*recipe.machine_slug);

            // Machine cost normalized by number of machines required
            moneyPenalty = (machine.cost_money.value_or(0.0) * machinesNeeded) * MONEY_PENALTY;

            // Pollution normalized by operational machine overhead
            pollutionPenalty = (machine.pollution_percent_per_hour.value_or(0.0) * machinesNeeded) * POLLUTION_PENALTY; 
        }

        // Rate Precision Score
        // Small penalty if single machine throughput severely overshoots target (light tie breaker)
        double rateDiff = std::abs(perMachineRate - targetRatePerSeconds) * RATE_PRECISION_PENALTY;

        std::cout << "Recipe: " << recipe.id
            << " | Base Cost Score: " << moneyPenalty
            << " | Inputs Penalty: " << inputComplexityPenalty
            << " | Per machine rate " << perMachineRate
            << " | Machine amount Penalty: " << machineCountPenalty
            << " | Pollution: " << pollutionPenalty 
            << " | TOTAL: " << rateDiff + machineCountPenalty + byproductPenalty + residuePenalty + inputComplexityPenalty + powerPenalty + moneyPenalty + pollutionPenalty
            << std::endl;

        // Lower total score = better recipe
        return rateDiff + machineCountPenalty + byproductPenalty + residuePenalty + inputComplexityPenalty + powerPenalty + moneyPenalty + pollutionPenalty;
    }


    // Display stuff

    inline void PrintTree(const ResolvedNode& node, int depth = 0) {
        std::string indent(depth * 2, ' ');
        std::cout << indent << "- " << node.item_name << ": " << std::fixed << std::setprecision(2) << (node.rate_per_s * 60.0) << "/min";

        if (node.is_raw_resource) {
            std::cout << "  [raw resource]";
        }
        else if (node.is_cycle_break) {
            std::cout << "  [CYCLE - stopped here]";
        }
        else if (node.recipe_id) {
            std::cout << "  via " << node.recipe_id.value() << "  (" << node.machines_theoretical << " machines theoretical, " << node.machines_actual << " actual)";

            if (node.alternative_recipe_count > 0) {
                std::cout << "  [" << node.alternative_recipe_count << " other recipe(s) also produce this]";
            }
        }
        std::cout << "\n";

        for (const auto& child : node.children) {
            PrintTree(child, depth + 1);
        }
    }

    inline void PrintReport(const std::string& targetName, double ratePerMin, const SolveResult& result) {
        std::cout << "\n========================================\n";
        std::cout << "TARGET\n----------------------------------------\n";
        std::cout << targetName << "\n" << ratePerMin << " / min\n";

        std::cout << "\nDEPENDENCY TREE\n----------------------------------------\n";
        PrintTree(result.root);

        std::cout << "\nMACHINES\n----------------------------------------\n";
        if (result.machines_by_recipe.empty()) {
            std::cout << "(none -- target is itself a raw resource)\n";
        }
        else {
            for (const auto& [recipe_id, count] : result.machines_by_recipe) {
                std::cout << count << " x  (recipe: " << recipe_id << ")\n";
            }
        }

        std::cout << "\nRAW RESOURCES\n----------------------------------------\n";
        if (result.raw_resource_rates.empty()) {
            std::cout << "(none found -- check for missing recipe data)\n";
        }
        else {
            for (const auto& [item_id, rate] : result.raw_resource_rates) {
                std::cout << item_id << "  " << std::fixed << std::setprecision(2)
                    << (rate * 60.0) << " / min\n";
            }
        }

        std::cout << "\nPOWER\n----------------------------------------\n";
        std::cout << "Consumption: " << result.total_power_mf_per_s << " MF/s\n";
        std::cout << "(generation/balance not computed yet -- Phase 8)\n";

        std::cout << "\nPOLLUTION\n----------------------------------------\n";
        std::cout << "+" << result.total_pollution_percent_per_hour << " %/hour\n";

        std::cout << "\nCOST\n----------------------------------------\n";
        std::cout << "$" << result.total_cost_money << "\n";

        std::cout << "\nRESEARCH\n----------------------------------------\n";
        if (result.required_research.empty()) {
            std::cout << "(none recorded)\n";
        }
        else {
            for (const auto& r : result.required_research) std::cout << r << "\n";
        }

        if (!result.warnings.empty()) {
            std::cout << "\nWARNINGS\n----------------------------------------\n";
            for (const auto& w : result.warnings) std::cout << "! " << w << "\n";
        }

        std::cout << "========================================\n";
    }
} // namespace Industrialist
