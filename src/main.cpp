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

    std::string dbPath = argv[1];
    std::string itemQuery = argv[2];
    double ratePerMin = std::stod(argv[3]);

    std::ifstream in(dbPath);
    if (!in) {
        std::cerr << "Could not open database file: " << dbPath << "\n";
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

    std::optional<std::string> itemId = ResolveItemID(db, itemQuery);
    if (!itemId) {
        std::cerr << "No item found matching '" << itemQuery << "'\n";
        return 1;
    }

    Solver solver(db);
    SolveResult result = solver.Solve(*itemId, ratePerMin / 60.0);

    PrintReport(db.items.at(*itemId).name, ratePerMin, result);
    return 0;
}