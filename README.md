# MTG Deckbuilder: AI-Enhanced Magic: The Gathering Deck Construction Suite

## 🔍 Project Summary

**MTG Deckbuilder** is a comprehensive, modular system for building, analyzing, and managing Magic: The Gathering decks. It leverages a powerful YAML-based configuration for defining deck archetypes and strategies, integrates with your personal card inventory, and utilizes a local SQLite database populated from MTGJSON data. The project features an interactive Gradio-based web UI for easy deck configuration and generation, alongside options for programmatic deck building.

At its core is a robust deck generation pipeline driven by callbacks, card scoring rules, inventory filtering, and detailed configuration options.

---

## 🔥 Features

-   **YAML-Driven Deck Building:** Define deck structure, card priorities, mana base, color identity, legalities, and other constraints in a flexible YAML format.
-   **Interactive Gradio UI:** A user-friendly web interface for loading, editing, and saving deck configurations, building decks, and managing inventory.
-   **Inventory-Aware Construction:** Build decks using only cards you own by importing your MTG Arena collection or a similarly formatted inventory file.
-   **Comprehensive Card Database:** Utilizes MTGJSON's `AllPrintings.json` for up-to-date card information, stored locally in a SQLite database.
-   **Smart Deck Logic:**
    -   Automatic land balancing based on color requirements.
    -   Category-based filling (creatures, removal, card draw, etc.) with target counts.
    -   Prioritization of key cards and strategies.
    -   Filtering by rarity, keywords, card text (including regex), and mana curve.
    -   Owned-only filtering.
-   **Callback-Driven Assembly:** A flexible, hook-based system allows for custom logic at various stages of the deck-building process.
-   **Deck Analysis & Export:**
    -   View deck statistics (mana curve, color balance, card types).
    -   Export decks in MTG Arena import format.
    -   Export your owned card inventory to CSV.
-   **Configuration Management:** Save and load deck configurations as YAML files directly through the UI.

---

## 📂 Project Structure

Key directories and files:

-   `/mtg_deck_builder/`: Core Python modules.
    -   `deck_config/`: Pydantic models for `DeckConfig` (validation, YAML I/O).
    -   `db/`: SQLAlchemy models (`models.py`), database interaction (`repository.py`), setup (`setup.py`), and data loading/bootstrapping (`bootstrap.py`).
    -   `yaml_builder/`: The deck building engine (`yaml_deckbuilder.py`) and helper functions (`helpers.py`, `callbacks.py`).
    -   `models/`: Contains the `Deck` model.
-   `/mtg_deckbuilder_ui/`: Gradio web UI application.
    -   `app.py`: Main Gradio application launcher.
    -   `tabs/`: Modular UI components for different sections (deck builder, config manager, etc.).
    -   `logic/`: UI-specific logic, including `deckbuilder_func.py` for handling UI actions.
    -   `ui/`: UI layout, themes, and synchronization logic (`config_sync.py`).
    -   `deck_configs/`: Default location for saved deck YAML configurations.
    -   `inventory_files/`: Default location for inventory text files.
    -   `data/`: Cached MTGJSON files (`AllPrintings.json`).
-   `/tests/`: Unit and integration tests.
    -   `sample_data/`: Example YAML deck configurations and sample inventory for testing.
-   `profile_yaml_deck_builder.py`: Example script for building a deck programmatically using a YAML config (useful for profiling or CLI usage).
-   `README.yaml.md`: Detailed documentation for the YAML deck configuration format.
-   `cards.db`: The SQLite database file generated from MTGJSON data (typically created in the root or a specified data directory).
-   `requirements.txt`: Python package dependencies.

---

## 🚀 Getting Started

### Prerequisites

-   Python 3.10+
-   Git (for cloning)

### Installation

1.  **Clone the Repository:**
    ```bash
    git clone <your-repository-url>
    cd MTGDecks 
    ```

2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set up Card Data (MTGJSON):**
    *   Download the latest `AllPrintings.json` file from [MTGJSON](https://mtgjson.com/downloads/all-files/).
    *   Place it in the `mtg_deckbuilder_ui/data/` directory (this is the typical location for the UI, but the bootstrap script might look in other default locations like `atomic_json_files/` if run standalone). The `bootstrap.py` script will use this to populate the `cards.db` SQLite database.

4.  **Prepare Your Inventory File (Optional but Recommended):**
    *   Export your card collection from MTG Arena (e.g., using an external tool like Arena Tutor by Draftsim, which can copy your collection to the clipboard).
    *   Paste the collection into a plain text file (e.g., `my_inventory.txt`). The format should be one card per line: `Quantity Card Name` (e.g., `4 Shivan Dragon`).
    *   Place this file in the `mtg_deckbuilder_ui/inventory_files/` directory. You can select this file in the UI.

5.  **Initialize the Database:**
    The first time you run the application or a script that requires the database (like `profile_yaml_deck_builder.py` or the UI), it should trigger the bootstrap process if `cards.db` doesn't exist or if `AllPrintings.json` is newer. This process will parse `AllPrintings.json` and create/update `cards.db`. This can take a few minutes.

### Running the Application

**1. Using the Gradio Web UI (Recommended):**

   Launch the Gradio application:
   ```bash
   python mtg_deckbuilder_ui/app.py
   ```
   Open your browser to the local URL provided (usually `http://localhost:7860` or similar).

   -   **Load/Save Configs:** Use the "Deckbuilder" tab to load existing YAML configurations from `mtg_deckbuilder_ui/deck_configs/` or save your current UI settings as a new YAML file.
   -   **Select Inventory:** Choose your inventory file. The system will then use this for "Owned Cards Only" builds.
   -   **Configure Deck:** Adjust parameters using the UI fields.
   -   **Build Deck:** Click the "Build Deck" button to generate a deck based on the current UI configuration.

**2. Using a Script (Example for Programmatic Building/Profiling):**

   The `profile_yaml_deck_builder.py` script demonstrates how to build a deck programmatically using a YAML configuration file.

   -   Ensure your `AllPrintings.json` is accessible (e.g., in `atomic_json_files/` or update path in script).
   -   Ensure your inventory file is accessible (e.g., in `inventory_files/` or update path in script).
   -   Modify `profile_yaml_deck_builder.py` to point to your desired YAML configuration file (e.g., one from `tests/sample_data/`).
   -   Run the script:
     ```bash
     python profile_yaml_deck_builder.py
     ```
   This will output the decklist, stats, and an MTG Arena import string to the console.

---

## ⚙️ YAML Configuration

The power of the deck builder comes from its YAML configuration. This allows for fine-grained control over every aspect of deck construction.

Refer to the [**MTG YAML Deck Template Guide (README.yaml.md)**](README.yaml.md) for a comprehensive definition of the YAML schema and all available options.

---

## 🎯 Roadmap

Key areas of development:

*   [x] Deck builder UI (no YAML editing required)
*   [ ] Live config editing (advanced features, real-time validation in UI)
*   [ ] Inventory visualizer and manager UI
*   [~] Export/import decklists (MTG Arena export exists; broader import/export TBD)
*   [ ] Sideboard & Commander support (basic legality/size exists; full support for Commander selection, singleton rules for relevant formats, sideboard construction).
*   [ ] Enhanced Deck View tab (grouping, sorting, mana curve visuals).
*   [ ] Card image integration (e.g., via Scryfall API).
*   [ ] In-app card search browser.
*   [ ] AI Assistant / ChatGPT Integration:
    *   Review current deck configuration and provide suggestions.
    *   Generate new deck configurations from natural language prompts.

---

## 🧪 Testing

The project includes a suite of tests to ensure the reliability of its core components:

*   `DeckConfig` validation and YAML serialization/deserialization.
*   Full deck generation logic using sample configurations and inventories.
*   Enforcement of constraints (priority cards, legalities, card limits).
*   Callback functionality.
*   Database interactions and model integrity.

Tests are located in the `/tests/` directory and utilize sample data from `/tests/sample_data/`.

---

## Requirements

-   Python 3.10+
-   Key Python libraries (see `requirements.txt`):
    -   `SQLAlchemy` (for database interaction)
    -   `PyYAML` (for YAML configuration handling)
    -   `Gradio` (for the web UI)
    -   `pandas` (used in UI for dataframes)
    -   `numpy` (dependency for pandas)
    -   `Pydantic V2` (for data validation)

---

## License

This project is licensed under the MIT License. See the `LICENSE` file for details (if one exists, otherwise assume MIT).

