"""
mtgjson_importer.py

Imports MTGJSON AllPrintings.json data into the application's database.

- Handles parsing and transformation of MTGJSON set/card data.
- Uses SQLAlchemy ORM for database operations.
- Employs batch/bulk inserts for performance.
- Runs import in a background thread to avoid blocking the UI.
- Supports progress and completion callbacks for UI feedback.

Performance:
- Uses session.bulk_save_objects for batch inserts of sets, cards, and printings.
- Commits are minimized and performed in batches.
- Designed for efficient large-scale data ingestion.

Threading:
- All import operations are performed in a separate thread.
- Callbacks are invoked to report progress and completion.

Usage:
    import_allprintings_json(
        json_path, db_path, meta_date,
        progress_callback=..., done_callback=...
    )
"""
import os
import json
import threading
from typing import Callable, Optional
from datetime import datetime, date
from tqdm import tqdm  # Progress bar for console
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from mtg_deck_builder.db.models import ImportLog, CardDB, CardPrintingDB, CardSetDB

def import_allprintings_json(
    json_path: str,
    db_path: str,
    meta_date: str,
    progress_callback: Optional[Callable[[float, str], None]] = None,
    done_callback: Optional[Callable[[bool, str], None]] = None
):
    """
    Imports AllPrintings.json into the database in a separate thread.
    Ensures all relations between sets, cards, and printings.
    Uses SQLAlchemy's bulk_save_objects for batch inserts for efficiency.
    Calls progress_callback(percent, message) as progress is made.
    Calls done_callback(success, message) when finished.
    Also prints progress and shows tqdm progress bars in the console.
    """
    def run():
        print("[mtgjson_importer] Starting import of AllPrintings.json...")
        try:
            engine = create_engine(f"sqlite:///{db_path}")
            Session = sessionmaker(bind=engine)
            session = Session()
            # Load JSON
            print(f"[mtgjson_importer] Loading JSON from {json_path}...")
            with open(json_path, "r", encoding="utf-8") as f:
                all_data = json.load(f)
            sets = all_data.get("data", {})

            # Clear existing data
            print("[mtgjson_importer] Clearing existing CardPrintingDB, CardDB, CardSetDB data...")
            session.query(CardPrintingDB).delete()
            session.query(CardDB).delete()
            session.query(CardSetDB).delete()
            session.commit()
            if progress_callback:
                progress_callback(0.05, "Cleared old database data.")

            set_objs = {}
            set_items = list(sets.items())
            card_objs = {}
            total_cards = sum(len(set_data.get("cards", [])) for _, set_data in set_items)
            print(f"[mtgjson_importer] Found {len(set_items)} sets and {total_cards} cards.")

            # Batch insert sets
            set_db_objs = []
            print("[mtgjson_importer] Inserting sets...")
            for idx, (set_code, set_data) in enumerate(tqdm(set_items, desc="Sets", unit="set")):
                release_date = set_data.get("releaseDate")
                if isinstance(release_date, str):
                    try:
                        release_date = datetime.strptime(release_date, "%Y-%m-%d").date()
                    except Exception:
                        release_date = None
                set_obj = CardSetDB(
                    set_code=set_code,
                    set_name=set_data.get("name"),
                    release_date=release_date,
                    block=set_data.get("block"),
                    set_metadata=set_data
                )
                set_objs[set_code] = set_obj
                set_db_objs.append(set_obj)
                if progress_callback and len(set_items) > 0 and idx % 10 == 0:
                    progress_callback(0.05 + 0.10 * (idx / len(set_items)), f"Inserted {idx+1}/{len(set_items)} sets...")
            session.bulk_save_objects(set_db_objs)
            session.commit()
            if progress_callback:
                progress_callback(0.15, "Sets inserted.")
            print(f"[mtgjson_importer] Inserted {len(set_db_objs)} sets.")

            # Batch insert cards and printings
            card_db_objs = {}
            printing_db_objs = []
            card_count = 0
            print("[mtgjson_importer] Inserting cards and printings...")
            for set_idx, (set_code, set_data) in enumerate(tqdm(set_items, desc="Cards", unit="set")):
                cards = set_data.get("cards", [])
                set_obj = set_objs[set_code]
                for card in cards:
                    card_name = card.get("name")
                    # Ensure CardDB exists and is unique
                    if card_name not in card_db_objs:
                        card_db = CardDB(name=card_name)
                        card_db_objs[card_name] = card_db
                    card_db = card_db_objs[card_name]
                    printing = CardPrintingDB(
                        uid=card.get("uuid"),
                        card_name=card_name,
                        artist=card.get("artist"),
                        number=card.get("number"),
                        set_code=set_code,
                        card_type=card.get("type"),
                        rarity=card.get("rarity"),
                        mana_cost=card.get("manaCost"),
                        power=card.get("power"),
                        toughness=card.get("toughness"),
                        abilities=card.get("abilities"),
                        flavor_text=card.get("flavorText"),
                        text=card.get("text"),
                        colors=card.get("colors"),
                        color_identity=card.get("colorIdentity"),
                        legalities=card.get("legalities"),
                        rulings=card.get("rulings"),
                        foreign_data=card.get("foreignData"),
                        card=card_db,
                        set=set_obj
                    )
                    printing_db_objs.append(printing)
                    card_count += 1
                    if progress_callback and total_cards > 0 and card_count % 1000 == 0:
                        progress_callback(0.15 + 0.75 * (card_count / total_cards), f"Inserted {card_count} cards...")
            session.bulk_save_objects(card_db_objs.values())
            session.bulk_save_objects(printing_db_objs)
            session.commit()
            if progress_callback:
                progress_callback(0.95, "All cards and printings inserted.")
            print(f"[mtgjson_importer] Inserted {len(card_db_objs)} unique cards and {len(printing_db_objs)} printings.")

            # Set newest_printing_uid for each card (batch)
            print("[mtgjson_importer] Setting newest_printing_uid for each card...")
            for card_db in tqdm(card_db_objs.values(), desc="Newest Printing", unit="card"):
                printings = [p for p in printing_db_objs if p.card_name == card_db.name]
                if printings:
                    newest = max(
                        printings,
                        key=lambda p: getattr(getattr(p, "set", None), "release_date", None) or ""
                    )
                    card_db.newest_printing_uid = newest.uid
            session.bulk_save_objects(card_db_objs.values())
            session.commit()

            # Log the import
            mtime = os.path.getmtime(json_path)
            import_log = ImportLog(
                json_path=json_path,
                meta_date=meta_date,
                mtime=mtime
            )
            session.merge(import_log)
            session.commit()
            if progress_callback:
                progress_callback(1.0, "Import complete.")
            print("[mtgjson_importer] Import complete.")
            if done_callback:
                done_callback(True, "Database update complete.")
        except Exception as e:
            print(f"[mtgjson_importer] ERROR: {e}")
            if done_callback:
                done_callback(False, f"Failed bespoke database update: {e}")
        finally:
            try:
                session.close()
            except Exception:
                pass

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread

