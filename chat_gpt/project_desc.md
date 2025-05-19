Got it. Here's the updated **project\_description.md** content, incorporating:

* The correct folder structure (`/deck_configs`, not `/configs`)
* Removal of the deprecated `/atomic_json_files/AtomicCards.json`
* Cleaned and renamed for clarity.

---

### `project_description.md`

# 🧙‍♂️ MTG Deckbuilder – AI-Enhanced Magic: The Gathering Deck Construction Suite

## 🔍 Project Summary

**MTG Deckbuilder** is a comprehensive, modular system for building and managing Magic: The Gathering decks. It supports structured configuration via YAML, a powerful card search and scoring engine, an interactive Gradio 5+ UI, and future integration with GPT-based assistants.

At its core is a robust deck generation pipeline driven by callbacks, scoring rules, and inventory filtering. The user interface is dynamically mapped to the configuration schema and is capable of saving/loading deck builds, validating them against a card database, and offering fine-grained control over deck construction preferences.

---

## 🗂️ Directory Overview

### Root Highlights:

* `/deck_configs/`: All saved deck YAML configurations.
* `/inventory_files/`: Raw text inventories used for building decks.
* `/reference/`: MTGJSON schemas, card type references, and introspection tools.
* `/chat_gpt/`: Vision and future planning documents, including the roadmap.
* `/tests/`: Unit and integration tests for database, config, YAML builder, and UI.
* `/mtg_deck_builder/`: Core logic and architecture:

  * `deck_config/`: Pydantic `DeckConfig` models with validation, YAML I/O.
  * `db/`: SQLAlchemy models and repositories for card lookup.
  * `yaml_builder/`: Deck building engine with support for priority, rarity weighting, fallback strategies, and category-driven design.
  * `utils/`: Support tools for data loading and conversion.
* `/mtg_deckbuilder_ui/`: Gradio UI system:

  * `tabs/`: Modular tabs for config, builder, inventory, and library.
  * `logic/`: Handles syncing UI state with `DeckConfig`.
  * `ui/`: Visual and functional layer, including `config_sync.py`, `deck_output.py`, themes, and helpers.
  * `data/`: Includes cached MTGJSON `AllPrintings.json` and `Meta.json`.
  * `static/`: CSS for theming.
  * `tests/`: Parallel UI-specific testing.
* `cards.db`: SQLite DB generated from MTGJSON data.

---

## 🧩 Key Features

✅ **YAML-based Config System**
✅ **Interactive Gradio UI with Dynamic Sync**
✅ **Deck Constraints: Size, Colors, Legalities, Rarity, Mana Curve**
✅ **Category-Aware Selection (creatures, removal, buffs, etc.)**
✅ **Owned-Only Filtering from Inventory**
✅ **Callback-Driven Deck Assembly Process**
✅ **Card Rarity Boost/Penalty Adjustments**
✅ **Text Scoring with Regex Support**
✅ **Saved Configs as Loadable YAML Files**
✅ **Robust Unit and Integration Tests**

---

## 🤖 Roadmap Integrations

* [ ] ChatGPT-based Assistant UI Tab
* [ ] Natural Language Deck Building (GPT-generated DeckConfig)
* [ ] Deck Viewer Tab
* [ ] Deck Manager Tab with Save/Load/Edit capabilities
* [ ] Settings Tab for OpenAI API key, data sources, and behavior toggles

---

## 🧪 Testing Philosophy

Test coverage includes:

* DeckConfig validation and YAML roundtrip
* Full deck generation with sample inventories
* Constraint enforcement (priority cards, legality)
* Callbacks for no-commons, minimum score, card count limits
* Deck output validation against fixed card DB snapshots

Located in:

* `/tests/`
* `/tests/sample_data/`
* `/tests/orm/` for DB bootstrapping

---

## ⚙️ Future-Proofing

* Swappable data backends (MTGJSON, Scryfall planned)
* Custom callbacks and hooks per build phase
* Configurable fallback and scoring logic
* Modular tab UI built with Gradio 5.x

---


