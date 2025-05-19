"""
mtgjson_sync.py

Handles synchronization of MTGJSON data files (Meta.json, AllPrintings.json) and updates the application's database.

- Downloads and verifies MTGJSON data from remote endpoints.
- Backs up old AllPrintings.json before updating.
- Checks if updates are needed based on remote/local version/date and DB import log.
- Updates the database using efficient batch operations.
- Designed for use in both UI and CLI workflows.

Performance:
- Uses batch/bulk inserts for sets, cards, and printings.
- Minimizes session commits and database round-trips.
- Ensures database schema exists before updating.

Usage:
    mtgjson_sync()
    # Will download and update only if needed, and update the database accordingly.
"""
import os
import requests
import json
import zipfile
import io
from datetime import datetime
from mtg_deckbuilder_ui.app_config import (
    LOCAL_META_PATH,
    LOCAL_ALLPRINTINGS_PATH,
    MTGJSON_META_URL,
    MTGJSON_ALLPRINTINGS_URL,
    DATABASE_URL
)
from mtg_deck_builder.db.models import ImportLog, CardDB, CardPrintingDB, CardSetDB
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tqdm import tqdm

# def get_db_path():
#     # Database at module root
#     return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "profile_cards.db"))

def backup_old_json(json_path, meta_date=None):
    if os.path.exists(json_path):
        # Use meta_date in backup filename if provided, else fallback to timestamp
        if meta_date:
            safe_meta_date = str(meta_date).replace(":", "-").replace(" ", "_")
            backup_zip = json_path.replace(".json", f"_{safe_meta_date}.zip")
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_zip = json_path.replace(".json", f"_{timestamp}.zip")
        with zipfile.ZipFile(backup_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(json_path, arcname=os.path.basename(json_path))

def get_db_last_import_meta_date():
    db_path = DATABASE_URL
    if not os.path.exists(db_path):
        return None
    try:
        engine = create_engine(f"sqlite:///{db_path}")
        Session = sessionmaker(bind=engine)
        session = Session()
        latest = session.query(ImportLog).order_by(ImportLog.meta_date.desc()).first()
        session.close()
        if latest:
            return latest.meta_date
    except Exception as e:
        print(f"Could not query ImportLog: {e}")
    return None

def update_database_with_json(json_path, db_path, meta_date, progress_callback=None):
    """
    Loads AllPrintings.json and updates CardDB, CardPrintingDB, CardSetDB tables.
    Logs the import in ImportLog.
    Prints progress and supports a progress_callback(percent, message).
    """
    print("[mtgjson_sync] Updating database with AllPrintings.json...")
    # Ensure the database file exists by creating tables if missing
    if not os.path.exists(db_path):
        from mtg_deck_builder.db.models import Base
        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(engine)
        # Force creation of the file even if no tables (for empty JSON)
        if not os.path.exists(db_path):
            # Touch the file by connecting and closing
            with engine.connect() as conn:
                pass

    # Ensure DB file exists even if AllPrintings.json is empty
    if not os.path.exists(db_path):
        # Create an empty SQLite file
        open(db_path, "a").close()

    engine = create_engine(f"sqlite:///{db_path}")
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        # Load JSON
        print(f"[mtgjson_sync] Loading AllPrintings.json from {json_path}...")
        with open(json_path, "r", encoding="utf-8") as f:
            all_data = json.load(f)
        sets = all_data.get("data", {})

        # Clear existing data
        print("[mtgjson_sync] Clearing CardPrintingDB, CardDB, CardSetDB tables...")
        session.query(CardPrintingDB).delete()
        session.query(CardDB).delete()
        session.query(CardSetDB).delete()
        session.commit()
        if progress_callback:
            progress_callback(0.05, "Cleared old database data.")

        set_items = list(sets.items())
        total_sets = len(set_items)
        total_cards = sum(len(set_data.get("cards", [])) for _, set_data in set_items)
        print(f"[mtgjson_sync] Found {total_sets} sets and {total_cards} cards.")

        # Insert sets
        print("[mtgjson_sync] Inserting sets...")
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
            session.add(set_obj)
            if progress_callback and total_sets > 0 and idx % 10 == 0:
                progress_callback(0.05 + 0.10 * (idx / total_sets), f"Inserted {idx+1}/{total_sets} sets...")
        session.commit()
        if progress_callback:
            progress_callback(0.15, "Sets inserted.")
        print("[mtgjson_sync] Sets inserted.")

        # Insert cards and printings
        print("[mtgjson_sync] Inserting cards and printings...")
        card_count = 0
        for set_idx, (set_code, set_data) in enumerate(tqdm(set_items, desc="Cards", unit="set")):
            cards = set_data.get("cards", [])
            for card in cards:
                card_name = card.get("name")
                # Insert CardDB if not exists
                card_db = session.query(CardDB).filter_by(name=card_name).first()
                if not card_db:
                    card_db = CardDB(name=card_name)
                    session.add(card_db)
                # Insert CardPrintingDB
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
                )
                session.add(printing)
                card_count += 1
                if progress_callback and total_cards > 0 and card_count % 1000 == 0:
                    progress_callback(0.15 + 0.75 * (card_count / total_cards), f"Inserted {card_count} cards...")
        session.commit()
        if progress_callback:
            progress_callback(0.95, "All cards and printings inserted.")
        print(f"[mtgjson_sync] Inserted {card_count} cards/printings.")

        # Log the import
        mtime = os.path.getmtime(json_path)
        from datetime import datetime
        meta_dt = meta_date
        if isinstance(meta_date, str):
            try:
                meta_dt = datetime.fromisoformat(meta_date)
            except Exception:
                try:
                    meta_dt = datetime.strptime(meta_date, "%Y-%m-%d")
                except Exception:
                    meta_dt = datetime.now()
        import_log = ImportLog(
            json_path=json_path,
            meta_date=meta_dt,
            mtime=mtime
        )
        session.merge(import_log)
        session.commit()
        if progress_callback:
            progress_callback(1.0, "Import complete.")
        print("[mtgjson_sync] Import complete.")
    except Exception as e:
        print(f"[mtgjson_sync] Failed database update: {e}")
        session.rollback()
        if progress_callback:
            progress_callback(1.0, f"Failed: {e}")
    finally:
        session.close()

def mtgjson_sync(progress_callback=None):
    """Check and sync MTGJSON data if outdated or missing, with backup and DB meta_date check.
    Prints progress and supports a progress_callback(percent, message).
    """
    print("[mtgjson_sync] Checking MTGJSON data sync status...")
    meta_url = MTGJSON_META_URL
    allprintings_url = MTGJSON_ALLPRINTINGS_URL
    local_meta_path = LOCAL_META_PATH
    local_allprintings_path = LOCAL_ALLPRINTINGS_PATH
    db_path = DATABASE_URL
    print(f"[mtgjson_sync] Local AllPrintings path: {local_allprintings_path}")
    print(f"[mtgjson_sync] Local Meta path: {local_meta_path}")
    print(f"[mtgjson_sync] Database path: {db_path}")
    # Check if local paths exist
    # Download remote meta
    try:
        print(f"[mtgjson_sync] Fetching remote meta from {meta_url} ...")
        remote_meta = requests.get(meta_url, timeout=10).json()
        remote_version = remote_meta.get("meta", {}).get("version", "")
        remote_date = remote_meta.get("meta", {}).get("date", "")
        print(f"[mtgjson_sync] Remote meta: version={remote_version}, date={remote_date}")
    except Exception as e:
        print(f"[mtgjson_sync] Could not fetch remote MTGJSON meta: {e}")
        return

    # Check local meta
    local_version = local_date = ""
    if os.path.exists(local_meta_path):
        try:
            with open(local_meta_path, "r", encoding="utf-8") as f:
                local_meta = json.load(f)
            local_version = local_meta.get("meta", {}).get("version", "")
            local_date = local_meta.get("meta", {}).get("date", "")
            print(f"[mtgjson_sync] Local meta: version={local_version}, date={local_date}")
        except Exception:
            print("[mtgjson_sync] Failed to read local meta.")

    # Check DB ImportLog meta_date (convert to string for comparison)
    db_meta_date = get_db_last_import_meta_date()
    db_meta_date_str = db_meta_date.strftime("%Y-%m-%d") if db_meta_date else None

    needs_update = (
        not os.path.exists(local_allprintings_path)
        or not os.path.exists(local_meta_path)
        or remote_version != local_version
        or remote_date != local_date
        or (db_meta_date_str and db_meta_date_str != str(remote_date))
        or not (os.path.exists(db_path))
    )
    if needs_update:
        print("[mtgjson_sync] Update required. Downloading and updating data...")
        try:
            # Pass local meta date for backup filename if available
            backup_old_json(local_allprintings_path, meta_date=local_date if local_date else None)
            r = requests.get(allprintings_url, stream=True, timeout=60)
            r.raise_for_status()
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                for name in z.namelist():
                    if name.endswith("AllPrintings.json"):
                        with z.open(name) as src, open(local_allprintings_path, "wb") as dst:
                            dst.write(src.read())
                        break
            with open(local_meta_path, "w", encoding="utf-8") as f:
                json.dump(remote_meta, f, indent=2)
            print("[mtgjson_sync] Downloaded new AllPrintings.json and updated Meta.json.")
            update_database_with_json(local_allprintings_path, db_path, remote_date, progress_callback=progress_callback)
            print("[mtgjson_sync] Database update complete.")
        except Exception as e:
            print(f"[mtgjson_sync] Failed to update MTGJSON data: {e}")
    else:
        print("[mtgjson_sync] MTGJSON data is up to date.")
