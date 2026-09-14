#include "Core/Model.hpp"
#include "Core/Types.hpp"
#include "solver/Solver.hpp"
#include "utils/Utils.hpp"
#include <fstream>


using namespace Industrialist;

int main(int argc, char** argv) {
    if (argc != 4) {
        std::cerr << "Usage: " << argv[0] << " <database.json> <item name or id> <rate per minute>\n";
        std::cerr << "Example: " << argv[0] << " industrialist_db.json Microchip 100\n";
        return 1;
    }

    std::string db_path = argv[1];
    std::string item_query = argv[2];
    double rate_per_min = std::stod(argv[3]);

    std::ifstream in(db_path);
    if (!in) {
        std::cerr << "Could not open database file: " << db_path << "\n";
        return 1;
    }

    json root;
    try {
        in >> root;
    }
    catch (const std::exception& e) {
        std::cerr << "Failed to parse JSON: " << e.what() << "\n";
        return 1;
    }

    Database db = LoadDatabase(root);
    std::cout << "Loaded " << db.items.size() << " items, " << db.machines.size() << " machines, " << db.recipes.size() << " recipes.\n";

    auto item_id = ResolveItemID(db, item_query);
    if (!item_id) {
        std::cerr << "No item found matching '" << item_query << "'\n";
        return 1;
    }

    Solver solver(db);
    SolveResult result = solver.Solve(*item_id, rate_per_min / 60.0);

    PrintReport(db.items.at(*item_id).name, rate_per_min, result);
    return 0;
}