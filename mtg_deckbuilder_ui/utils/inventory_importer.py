"""
inventory_importer.py

Imports a simple inventory file (lines: "qty Cardname") into the application's database.

- Ensures CardDB entries exist for all inventory items.
- Uses SQLAlchemy ORM for database operations.
- Employs batch/bulk inserts for performance.
- Runs import in a background thread to avoid blocking the UI.
- Supports progress and completion callbacks for UI feedback.

Performance:
- Uses session.bulk_save_objects for batch inserts of inventory items.
- Commits are minimized and performed in batches.
- Designed for efficient ingestion of large inventory lists.

Threading:
- All import operations are performed in a separate thread.
- Callbacks are invoked to report progress and completion.

Usage:
    import_inventory_file(
        inventory_path, db_path,
        progress_callback=..., done_callback=...
    )
"""
import os
import json
import threading
from typing import Callable, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from mtg_deck_builder.db.models import InventoryItemDB, CardDB
from tqdm import tqdm

def import_inventory_file(
    inventory_path: str,
    db_path: str,
    progress_callback: Optional[Callable[[float, str], None]] = None,
    done_callback: Optional[Callable[[bool, str], None]] = None
):
    """
    Imports a basic inventory file (lines: "qty Cardname") into the database in a separate thread.
    Ensures relations between inventory and CardDB.
    Calls progress_callback(percent, message) as progress is made.
    Calls done_callback(success, message) when finished.
    Also prints progress and shows tqdm progress bars in the console.
    """
    def run():
        print("[inventory_importer] Starting inventory import...")
        try:
            engine = create_engine(f"sqlite:///{db_path}")
            Session = sessionmaker(bind=engine)
            session = Session()
            # Read inventory file
            print(f"[inventory_importer] Reading inventory from {inventory_path}...")
            with open(inventory_path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
            inventory_data = []
            card_db_objs = {}
            total_lines = len(lines)
            for idx, line in enumerate(tqdm(lines, desc="Inventory", unit="line")):
                if not line:
                    continue
                parts = line.split(" ", 1)
                if len(parts) != 2:
                    continue
                try:
                    qty = int(parts[0])
                except ValueError:
                    continue
                card_name = parts[1].strip()
                if not card_name:
                    continue
                # Ensure CardDB exists for this card
                if card_name not in card_db_objs:
                    card_db = session.query(CardDB).filter_by(name=card_name).first()
                    if not card_db:
                        card_db = CardDB(name=card_name)
                        session.add(card_db)
                    card_db_objs[card_name] = card_db
                inventory_data.append({"card_name": card_name, "quantity": qty, "is_infinite": False})
                if progress_callback and total_lines > 0 and idx % 100 == 0:
                    progress_callback(0.05 + 0.80 * (idx / total_lines), f"Processed {idx+1}/{total_lines} inventory lines...")

            # Clear existing inventory
            print("[inventory_importer] Clearing old inventory data...")
            session.query(InventoryItemDB).delete()
            session.commit()
            if progress_callback:
                progress_callback(0.95, "Cleared old inventory data.")

            # Batch insert inventory items
            print("[inventory_importer] Inserting inventory items...")
            inv_objs = [
                InventoryItemDB(
                    card_name=item["card_name"],
                    quantity=item["quantity"],
                    is_infinite=item["is_infinite"]
                )
                for item in inventory_data
            ]
            session.bulk_save_objects(inv_objs)
            session.commit()
            if progress_callback:
                progress_callback(1.0, "Inventory import complete.")
            print("[inventory_importer] Inventory import complete.")
            if done_callback:
                done_callback(True, "Inventory database update complete.")
        except Exception as e:
            print(f"[inventory_importer] ERROR: {e}")
            if done_callback:
                done_callback(False, f"Failed inventory database update: {e}")
        finally:
            try:
                session.close()
            except Exception:
                pass

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread
