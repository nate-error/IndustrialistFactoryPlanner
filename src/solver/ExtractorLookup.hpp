#pragma once
#include "Core/Model.hpp"
#include <vector>
#include <string>

namespace Industrialist {

    struct ExtractorMatch {
        std::string machine_id;
        double depth_m = 0.0;
        double rate_per_s = 0.0;
    };

    inline std::vector<ExtractorMatch> FindExtractorSourcesFor(const Database& db, const std::string& itemId) {
        std::vector<ExtractorMatch> matches;
        for (const auto& [machineId, profile] : db.variable_extractors) {
            for (const auto& depth : profile.depth_profiles) {
                for (const auto& out : depth.outputs) {
                    if (out.item_id == itemId) {
                        matches.push_back({ machineId, depth.depth_m, out.rate_per_s });
                    }
                }
            }
        }
        return matches;
    }

} // namespace Industrialist