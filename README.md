
# MTGDecks: Automated Magic: The Gathering Deck Builder

This project provides tools for building, analyzing, and exporting Magic: The Gathering decks using YAML configuration, your personal card inventory, and the full MTG card database.

---

## Features

- **YAML-Driven Deck Building:**  
  Define deck structure, card priorities, mana base, and constraints in a flexible YAML template.
- **Inventory-Aware:**  
  Restrict deck building to cards you actually own, using your exported Arena collection.
- **Smart Land Balancing:**  
  Automatically calculates and fills the correct number of lands, balancing by color requirements.
- **Key Card Prioritization:**  
  Use regex or plain text rules to boost or penalize cards during deck selection.
- **Deck Analysis:**  
  Get statistics on mana curve, color balance, card types, and more.
- **MTG Arena Export:**  
  Export your deck in a format ready for import into MTG Arena.
- **Inventory Export:**  
  Export your owned cards to CSV for backup or analysis.

---

## Data Sources

### AllPrintings.json

- Download the latest `AllPrintings.json` from [mtgjson.com/downloads/all-files/](https://mtgjson.com/downloads/all-files/).
- Place it in `atomic_json_files/AllPrintings.json` inside this project.

### Card Inventory

- The card inventory file can come from any source that exports deck lists in MTG Arena format.
- **Draftsim Arena Tutor** lets you export your library to clipboard. Paste it into a file in `inventory_files/card inventory.txt`.
- The format should be:  
  `Card Name,Quantity`

---

## Getting Started

1. **Initialize the Database**

   Run the initialization script:

   ```bash
   python scripts/init_db.py
   ```

2. **Set File Paths**

   - Set the file paths for `AllPrintings.json` and your inventory file in `bootstrap.py` if you need to customize locations.

3. **Configure Your Deck**

   - Edit or create a YAML file in `tests/sample_data/` (see [README.yaml.md](README.yaml.md) for full YAML documentation).
   - Example: `b-grave-recursion.yaml`

4. **Build and Analyze Your Deck**

   ```bash
   python profile_yaml_deck_builder.py
   ```

   - This will print your deck list, statistics, and an MTG Arena import string.

5. **Export Your Owned Cards**

   ```bash
   python export_owned_cards_to_csv.py
   ```

   - Outputs `owned_cards.csv` with all cards you own and their quantities.

---

## Project Structure

- `mtg_deck_builder/`  
  Core Python modules for deck building, database, and models.
- `atomic_json_files/AllPrintings.json`  
  Full MTG card database (downloaded from mtgjson.com).
- `inventory_files/card inventory.txt`  
  Your personal card inventory.
- `tests/sample_data/`  
  Example YAML deck templates.
- `profile_yaml_deck_builder.py`  
  Main script for building and analyzing decks.
- `export_owned_cards_to_csv.py`  
  Utility for exporting your owned cards to CSV.
- `README.yaml.md`  
  Full documentation for the YAML deck template format.

---

## Requirements

- Python 3.8+
- SQLAlchemy
- PyYAML

Install dependencies with:

```bash
pip install -r requirements.txt
```

---

## YAML Deck Template

See [README.yaml.md](README.yaml.md) for a full guide and example.

---

## License

MIT License

