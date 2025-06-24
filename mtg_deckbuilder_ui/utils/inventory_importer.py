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
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from mtg_deck_builder.db.models import InventoryItemDB, CardDB, Base
from tqdm import tqdm
from mtg_deckbuilder_ui.app_config import app_config
from mtg_deck_builder.db.bootstrap import bootstrap_inventory


def get_db_session():
    db_path = app_config.get("Paths", "database")
    engine = create_engine(f"sqlite:///{db_path}")
    Session = sessionmaker(bind=engine)
    return Session()


def ensure_tables_exist(engine):
    """
    Make sure the required tables for inventory import exist.
    If they don't, create them.
    """
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    # Check if tables are missing
    required_tables = ["cards", "inventory_items", "card_printings", "sets"]
    missing_tables = [
        table for table in required_tables if table not in existing_tables
    ]

    if missing_tables:
        print(
            f"[inventory_importer] Creating missing tables: {', '.join(missing_tables)}"
        )
        # Create all tables defined in Base metadata
        Base.metadata.create_all(engine)
        return True
    return False


def import_inventory_file(
    inventory_path: str,
    db_path: str = None,
    progress_callback: Optional[Callable[[float, str], None]] = None,
    done_callback: Optional[Callable[[bool, str], None]] = None,
):
    """
    Imports a basic inventory file (lines: "qty Cardname") into the database in a separate thread.
    Ensures relations between inventory and CardDB.
    Calls progress_callback(percent, message) as progress is made.
    Calls done_callback(success, message) when finished.
    Also prints progress and shows tqdm progress bars in the console.
    If db_path is not provided, use the app_config database path.
    """
    if db_path is None:
        db_path = app_config.get("Paths", "database")
        if db_path is None:
            db_path = ""
    engine = create_engine(f"sqlite:///{db_path}")

    # Ensure tables exist before trying to import
    tables_created = ensure_tables_exist(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    # Wipe all inventory before import
    session.query(InventoryItemDB).delete()
    session.commit()

    def run():
        print(
            f"[inventory_importer] DEBUG: Import thread started. inventory_path={inventory_path}, db_path={db_path}"
        )
        try:
            # Log inventory file contents for debugging
            try:
                with open(inventory_path, "r", encoding="utf-8") as debug_f:
                    debug_lines = debug_f.readlines()
                print(
                    f"[inventory_importer] DEBUG: Inventory file has {len(debug_lines)} lines. First 5 lines: {debug_lines[:5]}"
                )
            except Exception as e:
                print(
                    f"[inventory_importer] DEBUG: Could not read inventory file for debug: {e}"
                )
            if progress_callback:
                progress_callback(0.01, "Reading inventory file...")
            print(f"[inventory_importer] Reading inventory from {inventory_path}...")
            with open(inventory_path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
            inventory_data = []
            card_db_objs = {}
            total_lines = len(lines)

            if progress_callback:
                progress_callback(0.05, f"Processing {total_lines} inventory lines...")

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
                inventory_data.append(
                    {"card_name": card_name, "quantity": qty}
                )
                if progress_callback and total_lines > 0 and idx % 100 == 0:
                    progress_callback(
                        0.05 + 0.80 * (idx / total_lines),
                        f"Processed {idx+1}/{total_lines} inventory lines...",
                    )

            # Deduplicate inventory_data by card_name, summing quantities
            deduped_inventory = {}
            for item in inventory_data:
                name = item["card_name"]
                qty = item["quantity"]
                if name in deduped_inventory:
                    deduped_inventory[name]["quantity"] += qty
                else:
                    deduped_inventory[name] = item.copy()
            if len(deduped_inventory) != len(inventory_data):
                print(
                    f"[inventory_importer] DEBUG: Deduplicated inventory: {len(inventory_data)} -> {len(deduped_inventory)} unique cards."
                )
            inventory_data = list(deduped_inventory.values())

            if progress_callback:
                progress_callback(0.87, "Clearing old inventory data...")
            print("[inventory_importer] Clearing old inventory data...")
            session.query(InventoryItemDB).delete()
            session.commit()
            if progress_callback:
                progress_callback(0.92, "Inserting inventory items...")
            print("[inventory_importer] Inserting inventory items...")
            inv_objs = [
                InventoryItemDB(
                    card_name=item["card_name"],
                    quantity=item["quantity"]
                )
                for item in inventory_data
            ]
            session.bulk_save_objects(inv_objs)
            session.commit()
            # After commit, log number of rows in inventory_items table
            try:
                count = session.query(InventoryItemDB).count()
                print(
                    f"[inventory_importer] DEBUG: inventory_items table row count after import: {count}"
                )
            except Exception as e:
                print(
                    f"[inventory_importer] DEBUG: Could not count inventory_items: {e}"
                )
            if progress_callback:
                progress_callback(0.97, "Re-bootstrapping the database...")
            print("[inventory_importer] Re-bootstrapping the database...")

            # Use a try-except for bootstrapping in case it fails
            try:
                bootstrap_inventory(inventory_path)
                bootstrap_success = True
            except Exception as e:
                print(f"[inventory_importer] Warning: Bootstrap failed: {e}")
                bootstrap_success = False

            print("[inventory_importer] Database re-bootstrapped.")
            if progress_callback:
                progress_callback(1.0, "Inventory import and DB bootstrap complete.")
            print("[inventory_importer] Inventory import complete.")
            if done_callback:
                message = "Inventory database update complete."
                if tables_created:
                    message += " Created database tables."
                if bootstrap_success:
                    message += " DB re-bootstrapped."
                done_callback(True, message)
        except Exception as e:
            print(f"[inventory_importer] ERROR: {e}")
            if progress_callback:
                progress_callback(1.0, f"❌ Error: {e}")
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
