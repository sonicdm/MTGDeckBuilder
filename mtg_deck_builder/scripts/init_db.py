from pathlib import Path
from mtg_deck_builder.db.bootstrap import bootstrap

def main():
    project_root = Path(__file__).resolve().parents[2]
    all_printings = project_root / "atomic_json_files" / "AllPrintings.json"
    inventory_file = project_root / "inventory_files" / "card inventory.txt"

    bootstrap(str(all_printings), str(inventory_file))

if __name__ == "__main__":
    main()
