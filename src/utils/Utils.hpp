#pragma once
#include <iostream>
#include <string>
#include <algorithm>
#include <cctype>
#include <optional>
#include <iomanip>

namespace Industrialist {

    inline std::string ToLower(std::string s) {
        std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c) { return std::tolower(c); });
        return s;
    }

    // Accepts an item id (e.g. "10-karat-gold"), a wiki slug (e.g. "10_Karat_Gold"), or a display name (e.g. "10 Karat Gold", case-insensitive) and returns the
    // canonical item_id used as the key in Database::items.
    inline std::optional<std::string> ResolveItemID(const Database& db, const std::string& query) {
        if (db.items.count(query)) return query;

        std::string q_lower = ToLower(query);
        for (const auto& [id, item] : db.items) {
            if (ToLower(item.name) == q_lower)
                return id;

            if (item.wiki_slug && ToLower(*item.wiki_slug) == q_lower)
                return id;
        }

        return std::nullopt;
    }

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

    inline void PrintReport(const std::string& target_name, double rate_per_min, const SolveResult& result) {
        std::cout << "\n========================================\n";
        std::cout << "TARGET\n----------------------------------------\n";
        std::cout << target_name << "\n" << rate_per_min << " / min\n";

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
