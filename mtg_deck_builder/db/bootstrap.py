import logging
from mtg_deck_builder.db.setup import setup_database
from mtg_deck_builder.db.models import CardDB, CardSetDB, CardPrintingDB, ImportLog
from mtg_deck_builder.db.loader import is_reload_needed, update_import_time, load_inventory
from sqlalchemy.orm import sessionmaker
import json
from datetime import datetime
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

logging.basicConfig(level=logging.DEBUG, format='[%(levelname)s][%(threadName)s] %(message)s')

def bootstrap(
    json_path: str,
    inventory_path: str = None,
    db_url: str = "sqlite:///cards.db",
    use_tqdm: bool = True
):
    logging.debug(f"Starting bootstrap with json_path={json_path}, inventory_path={inventory_path}, db_url={db_url}")
    engine = setup_database(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        mtime = os.path.getmtime(json_path)
    except FileNotFoundError:
        logging.error(f"File not found: {json_path}")
        return

    if not is_reload_needed(session=session, json_path=json_path,  mtime=mtime):
        logging.info("No Cards update needed. Skipping reload.")

    else:
        logging.debug(f"Reloading cards from {json_path}...")
        with open(json_path, 'r', encoding='utf-8') as f:
            all_data = json.load(f)
        meta_date_str = all_data.get("meta", {}).get("date")
        meta_date = datetime.strptime(meta_date_str, "%Y-%m-%d")
        logging.debug("Reloading cards...")
        session.query(CardPrintingDB).delete()
        session.query(CardDB).delete()
        session.query(CardSetDB).delete()

        sets_data = all_data.get("data", {})
        card_count = 0
        set_count = 0
        skipped_cards = 0

        results = {"cards": [], "printings": [], "skipped": 0}
        card_name_cache = set()
        card_name_cache_lock = Lock()

        def process_cards(card_entries, set_code, set_info, set_entry):
            local_cards = []
            local_printings = []
            local_skipped = 0
            card_iter = card_entries
            if tqdm and use_tqdm:
                card_iter = tqdm(card_entries, desc=f"Cards in {set_code}", unit="card", leave=False)
            else:
                logging.debug(f"Processing {len(card_entries)} cards in set {set_code}...")
            for card_data in card_iter:
                uid = card_data.get("uuid")
                card_name = card_data.get("name")
                if not uid or not card_name:
                    local_skipped += 1
                    continue

                # Ensure CardDB exists for this card name (thread-safe, global)
                with card_name_cache_lock:
                    if card_name not in card_name_cache:
                        card_obj = CardDB(name=card_name)
                        local_cards.append(card_obj)
                        card_name_cache.add(card_name)

                # Add CardPrintingDB for this printing
                printing = CardPrintingDB(
                    uid=uid,
                    card_name=card_name,
                    artist=card_data.get("artist"),
                    number=card_data.get("number"),
                    set_code=set_code,
                    card_type=card_data.get("type"),
                    rarity=card_data.get("rarity"),
                    mana_cost=card_data.get("manaCost"),
                    power=str(card_data.get("power")) if card_data.get("power") is not None else None,
                    toughness=str(card_data.get("toughness")) if card_data.get("toughness") is not None else None,
                    abilities=card_data.get("keywords"),
                    flavor_text=card_data.get("flavorText"),
                    text=card_data.get("text"),
                    colors=card_data.get("colors"),  # This is the actual printed colors
                    color_identity=card_data.get("colorIdentity"),  # <-- Use colorIdentity for deck-building
                    legalities=card_data.get("legalities"),
                    rulings=card_data.get("rulings"),
                    foreign_data=card_data.get("foreignData"),
                )
                printing.set = set_entry
                local_printings.append(printing)
            return (local_cards, local_printings, local_skipped)

        set_iter = list(sets_data.items())
        if tqdm and use_tqdm:
            set_iter = tqdm(set_iter, desc="Sets", unit="set")
        else:
            logging.debug(f"Processing {len(set_iter)} sets...")

        futures = []
        set_entries = []
        with ThreadPoolExecutor() as executor:
            for set_code, set_info in set_iter:
                card_entries = set_info.pop("cards", [])
                set_entry = CardSetDB(
                    set_code=set_code,
                    set_name=set_info.get("name"),
                    release_date=datetime.strptime(set_info.get("releaseDate"), "%Y-%m-%d") if set_info.get("releaseDate") else None,
                    block=set_info.get("block"),
                    set_metadata=set_info
                )
                session.add(set_entry)
                set_entries.append(set_entry)
                set_count += 1
                futures.append(executor.submit(process_cards, card_entries, set_code, set_info, set_entry))

            for future in (tqdm(futures, desc="Processing Sets", unit="set") if tqdm and use_tqdm else futures):
                local_cards, local_printings, local_skipped = future.result()
                results["cards"].extend(local_cards)
                results["printings"].extend(local_printings)
                results["skipped"] += local_skipped

        msg = f"Adding {len(results['cards'])} cards and {len(results['printings'])} printings to the database..."
        if tqdm and use_tqdm:
            tqdm.write(msg)
        else:
            logging.debug(msg)
        for card in results["cards"]:
            session.add(card)
        for printing in results["printings"]:
            session.add(printing)
        card_count = len(results["printings"])
        skipped_cards = results["skipped"]

        # Set newest_printing_uid for each card (DB-level cache)
        logging.debug("Setting newest_printing_uid for each card...")
        card_name_to_printings = {}
        for printing in results["printings"]:
            card_name_to_printings.setdefault(printing.card_name, []).append(printing)
        for card in results["cards"]:
            printings = card_name_to_printings.get(card.name, [])
            if printings:
                # Find the newest printing by release_date
                try:
                    newest = max(
                        printings,
                        key=lambda p: getattr(getattr(p, "set", None), "release_date", None) or getattr(p, "release_date", None) or "",
                        default=None
                    )
                except Exception:
                    newest = printings[0]
                card.newest_printing_uid = newest.uid
        logging.debug("Finished setting newest_printing_uid.")

        update_import_time(session=session, json_path=json_path, meta_date=meta_date, mtime=mtime)
        msg = f"Imported {card_count} card printings across {set_count} sets."
        if tqdm and use_tqdm:
            tqdm.write(msg)
        else:
            logging.info(msg)
        if skipped_cards:
            msg = f"Skipped {skipped_cards} card entries due to missing UUID or name."
            if tqdm and use_tqdm:
                tqdm.write(msg)
            else:
                logging.warning(msg)

    if inventory_path:
        logging.debug(f"Loading inventory from {inventory_path}...")
        load_inventory(session, inventory_path)

    logging.debug("Committing database changes...")
    session.commit()
    session.close()
    logging.info("Bootstrap complete.")

