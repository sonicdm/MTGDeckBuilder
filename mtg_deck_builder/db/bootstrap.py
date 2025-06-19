"""
Database bootstrap utilities for Magic: The Gathering deck builder.

This module provides functions to initialize and populate the card database from JSON data sources, and optionally load inventory data. It manages database setup, data import, and ensures that the database is only reloaded when necessary.
"""
import logging
from contextlib import contextmanager
from threading import Lock
from typing import Dict, List, Optional, Any, Callable, Tuple, Set
from pathlib import Path

from mtg_deck_builder.db.setup import setup_database
from mtg_deck_builder.db.models import CardDB, CardSetDB, CardPrintingDB, ImportLog
from mtg_deck_builder.db.loader import update_import_time, load_inventory
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.engine import Engine
import json
from datetime import datetime, date
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

logger = logging.getLogger(__name__)

# Global lock for bootstrap operations
_bootstrap_lock = Lock()

class BootstrapError(Exception):
    """Base exception for bootstrap operations."""
    pass

class FileNotFoundError(BootstrapError):
    """Raised when a required file is not found."""
    pass

class InvalidDataError(BootstrapError):
    """Raised when data is invalid or malformed."""
    pass

class DatabaseError(BootstrapError):
    """Raised when a database operation fails."""
    pass

@contextmanager
def transaction_scope(session: Session) -> Session:
    """Context manager for database transactions.
    
    Args:
        session: SQLAlchemy database session.
        
    Yields:
        The session for use in the transaction.
        
    Raises:
        DatabaseError: If the transaction fails.
    """
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise DatabaseError(f"Transaction failed: {str(e)}") from e

def parse_date(date_str: Optional[str]) -> Optional[date]:
    """Parse a date string into a date object.
    
    Args:
        date_str: Date string in YYYY-MM-DD format.
        
    Returns:
        Parsed date object or None if invalid.
    """
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except Exception:
        return None

def pad_set_name(name: str, max_length: int) -> str:
    """Pad a set name to a fixed length.
    
    Args:
        name: Set name to pad.
        max_length: Maximum length to pad to.
        
    Returns:
        Padded set name.
    """
    return (name or "").ljust(max_length)

def process_cards(
    card_entries: List[Dict[str, Any]],
    set_code: str,
    set_info: Dict[str, Any],
    set_entry: CardSetDB
) -> Tuple[List[CardPrintingDB], int]:
    """Process a batch of card entries for a set.
    
    Args:
        card_entries: List of card data dictionaries.
        set_code: Code of the set being processed.
        set_info: Set information dictionary.
        set_entry: CardSetDB instance for the set.
        
    Returns:
        Tuple of (list of CardPrintingDB instances, number of skipped cards).
    """
    local_printings = []
    local_skipped = 0
    
    for card_data in card_entries:
        uid = card_data.get("uuid")
        card_name = card_data.get("name")
        if not uid or not card_name:
            local_skipped += 1
            continue
            
        try:
            printing = CardPrintingDB(
                uuid=uid,
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
                flavor_text=card_data.get("flavorText") or "",
                text=card_data.get("text") or "",
                colors=card_data.get("colors"),
                color_identity=card_data.get("colorIdentity"),
                legalities=card_data.get("legalities"),
                rulings=card_data.get("rulings"),
                foreign_data=card_data.get("foreignData"),
                keywords=card_data.get("keywords"),
                ascii_name=card_data.get("asciiName"),
                attraction_lights=card_data.get("attractionLights"),
                availability=card_data.get("availability"),
                booster_types=card_data.get("boosterTypes"),
                border_color=card_data.get("borderColor"),
                card_parts=card_data.get("cardParts"),
                color_indicator=card_data.get("colorIndicator"),
                converted_mana_cost=card_data.get("convertedManaCost"),
                defense=card_data.get("defense"),
                duel_deck=card_data.get("duelDeck"),
                edhrec_rank=card_data.get("edhrecRank"),
                edhrec_saltiness=card_data.get("edhrecSaltiness"),
                face_converted_mana_cost=card_data.get("faceConvertedManaCost"),
                face_flavor_name=card_data.get("faceFlavorName"),
                face_mana_value=card_data.get("faceManaValue"),
                face_name=card_data.get("faceName"),
                finishes=card_data.get("finishes"),
                flavor_name=card_data.get("flavorName"),
                frame_effects=card_data.get("frameEffects"),
                frame_version=card_data.get("frameVersion"),
                hand=card_data.get("hand"),
                has_alternative_deck_limit=card_data.get("hasAlternativeDeckLimit"),
                has_content_warning=card_data.get("hasContentWarning"),
                has_foil=card_data.get("hasFoil"),
                has_non_foil=card_data.get("hasNonFoil"),
                identifiers=card_data.get("identifiers"),
                is_alternative=card_data.get("isAlternative"),
                is_full_art=card_data.get("isFullArt"),
                is_funny=card_data.get("isFunny"),
                is_online_only=card_data.get("isOnlineOnly"),
                is_oversized=card_data.get("isOversized"),
                is_promo=card_data.get("isPromo"),
                is_rebalanced=card_data.get("isRebalanced"),
                is_reprint=card_data.get("isReprint"),
                is_reserved=card_data.get("isReserved"),
                is_starter=card_data.get("isStarter"),
                is_story_spotlight=card_data.get("isStorySpotlight"),
                is_textless=card_data.get("isTextless"),
                is_timeshifted=card_data.get("isTimeshifted"),
                language=card_data.get("language"),
                layout=card_data.get("layout"),
                leadership_skills=card_data.get("leadershipSkills"),
                life=card_data.get("life"),
                loyalty=card_data.get("loyalty"),
                original_printings=card_data.get("originalPrintings"),
                original_release_date=card_data.get("originalReleaseDate"),
                original_text=card_data.get("originalText"),
                original_type=card_data.get("originalType"),
                other_face_ids=card_data.get("otherFaceIds"),
                printings=card_data.get("printings"),
                promo_types=card_data.get("promoTypes"),
                purchase_urls=card_data.get("purchaseUrls"),
                related_cards=card_data.get("relatedCards"),
                rebalanced_printings=card_data.get("rebalancedPrintings"),
                security_stamp=card_data.get("securityStamp"),
                side=card_data.get("side"),
                signature=card_data.get("signature"),
                source_products=card_data.get("sourceProducts"),
                subsets=card_data.get("subsets"),
                subtypes=card_data.get("subtypes"),
                supertypes=card_data.get("supertypes"),
                types=card_data.get("types"),
                variations=card_data.get("variations"),
                watermark=card_data.get("watermark"),
            )
            printing.set = set_entry
            local_printings.append(printing)
        except Exception as e:
            logger.error(f"Error processing card {card_name}: {str(e)}")
            local_skipped += 1
            
    return local_printings, local_skipped

def configure_sqlite_performance(engine: Engine) -> None:
    """Configure SQLite performance settings.
    
    Args:
        engine: SQLAlchemy engine instance.
    """
    if not engine.url.drivername.startswith("sqlite"):
        return
        
    from sqlalchemy import event
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA synchronous = OFF")
        cursor.execute("PRAGMA journal_mode = WAL")
        cursor.execute("PRAGMA temp_store = MEMORY")
        cursor.execute("PRAGMA cache_size = -100000")  # 100MB
        cursor.execute("PRAGMA locking_mode = EXCLUSIVE")
        cursor.close()

def bootstrap(
    json_path: str,
    inventory_path: Optional[str] = None,
    db_url: str = "sqlite:///cards.db",
    use_tqdm: bool = True,
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> None:
    """Initialize and populate the card database from a JSON data source.

    Loads card and set data from a JSON file into the database, using multi-threading for efficiency.
    Handles duplicate checking, sets up relationships, and updates import logs. Optionally loads inventory data.

    Args:
        json_path: Path to the card data JSON file.
        inventory_path: Optional path to the inventory file to load after cards.
        db_url: SQLAlchemy database URL.
        use_tqdm: Whether to use tqdm progress bars.
        progress_callback: Optional function to call with progress updates.
        
    Raises:
        FileNotFoundError: If the JSON file doesn't exist.
        InvalidDataError: If the JSON data is invalid or malformed.
        DatabaseError: If there's a database error.
    """
    from mtg_deck_builder.db import get_session
    json_path = str(json_path)
    inventory_path = str(inventory_path)
    db_url = str(db_url)
    # Use lock to prevent concurrent bootstrap operations
    with _bootstrap_lock:
        logger.debug(f"Starting bootstrap with json_path={json_path}, inventory_path={inventory_path}, db_url={db_url}")
        logger.debug(f"[BOOTSTRAP] Using db_url: {db_url}")
        logger.debug(f"[BOOTSTRAP] Current working directory: {os.getcwd()}")
        logger.debug(f"[BOOTSTRAP] Absolute db path: {os.path.abspath(db_url.replace('sqlite:///', ''))}")
        
        # Setup database and ensure tables exist
        try:
            engine = setup_database(db_url)
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to setup database: {str(e)}") from e

        # Configure SQLite performance if using SQLite
        configure_sqlite_performance(engine)

        with get_session(db_url) as session:
            try:
                mtime = os.path.getmtime(json_path)
            except FileNotFoundError:
                logger.error(f"File not found: {json_path}")
                raise FileNotFoundError(f"JSON file not found: {json_path}")

            # Use transaction to prevent race conditions
            with transaction_scope(session):
                # Check if we need to reload by comparing with the latest import's mtime
                latest_import = session.query(ImportLog).filter_by(json_path=json_path).order_by(ImportLog.mtime.desc()).first()
                if latest_import and latest_import.mtime >= mtime:
                    logger.info("No Cards update needed. Skipping reload.")
                    return

                logger.debug(f"Reloading cards from {json_path}...")
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        all_data = json.load(f)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON file: {e}")
                    raise InvalidDataError(f"Invalid JSON data: {str(e)}") from e
                except Exception as e:
                    logger.error(f"Failed to read JSON file: {e}")
                    raise FileNotFoundError(f"Failed to read JSON file: {str(e)}") from e

                meta_date_str = all_data.get("meta", {}).get("date")
                try:
                    meta_date = datetime.strptime(meta_date_str, "%Y-%m-%d")
                except (ValueError, TypeError) as e:
                    logger.error(f"Invalid meta date format: {e}")
                    raise InvalidDataError(f"Invalid meta date format: {str(e)}") from e

                logger.debug("Reloading cards...")
                try:
                    if progress_callback:
                        progress_callback(0.01, "Clearing existing data...")
                    session.query(CardPrintingDB).delete()
                    session.query(CardDB).delete()
                    session.query(CardSetDB).delete()
                except SQLAlchemyError as e:
                    raise DatabaseError(f"Failed to clear existing data: {str(e)}") from e

                sets_data = all_data.get("data", {})
                set_items = list(sets_data.items())
                total_sets = len(set_items)
                total_cards = sum(len(set_info.get("cards", [])) for _, set_info in set_items)
                if progress_callback:
                    progress_callback(0.02, f"Preparing to process {total_sets} sets and {total_cards} cards...")
                if tqdm and use_tqdm:
                    set_iter = tqdm(set_items, desc="Sets", unit="set", position=0, leave=True)
                else:
                    set_iter = set_items

                # Calculate max set name length for progress bar padding
                max_set_name_len = max((len(set_info.get("name", "")) for _, set_info in set_items), default=0)
                max_set_code_len = max((len(set_code) for set_code, _ in set_items), default=0)

                if progress_callback:
                    progress_callback(0.03, "Building card printing cache...")

                # Pre-build a cache of card printings and their release dates
                card_printings_map: Dict[str, List[str]] = {}
                printing_release_map: Dict[str, Optional[date]] = {}
                for set_code, set_info in set_items:
                    release_date = parse_date(set_info.get("releaseDate"))
                    for card in set_info.get("cards", []):
                        name = card.get("name")
                        if not name:
                            continue
                        uid = card.get("uuid")
                        if not uid:
                            continue
                        card_printings_map.setdefault(name, []).append(uid)
                        printing_release_map[uid] = release_date

                results = {"cards": [], "printings": [], "skipped": 0}
                card_name_cache: Set[str] = set()

                if progress_callback:
                    progress_callback(0.04, "Building unique card list...")

                # Build all unique CardDBs in the main thread
                all_card_names = set()
                for _, set_info in set_items:
                    for card in set_info.get("cards", []):
                        name = card.get("name")
                        if name:
                            all_card_names.add(name)
                results["cards"] = [CardDB(name=name) for name in all_card_names]
                if progress_callback:
                    progress_callback(0.05, f"Found {len(all_card_names)} unique card names.")

                future_to_set = {}
                with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
                    for set_code, set_info in set_iter:
                        set_entry = CardSetDB(
                            set_code=set_code,
                            set_name=set_info.get("name"),
                            release_date=parse_date(set_info.get("releaseDate")),
                            block=set_info.get("block"),
                            set_metadata={k: v for k, v in set_info.items() if k not in ["name", "releaseDate", "block", "cards"]}
                        )
                        session.add(set_entry)
                        card_entries = set_info.get("cards", [])
                        future = executor.submit(process_cards, card_entries, set_code, set_info, set_entry)
                        future_to_set[future] = (set_code, set_info.get("name"))

                    if tqdm and use_tqdm:
                        # Create a fixed-width progress bar at the bottom
                        set_progress = tqdm(
                            total=total_sets,
                            desc="Processing Sets",
                            unit="set",
                            position=1,
                            leave=True,
                            bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]'
                        )
                    else:
                        set_progress = None

                    for idx, future in enumerate(as_completed(future_to_set)):
                        try:
                            local_printings, local_skipped = future.result()
                            results["printings"].extend(local_printings)
                            results["skipped"] += local_skipped
                            set_code, set_name = future_to_set[future]
                            if set_progress:
                                # Print the current set being processed above the progress bar
                                print(f"\033[KProcessing {set_code:<{max_set_code_len}}: {set_name:<{max_set_name_len}}", end='\r')
                                set_progress.update(1)
                            if progress_callback:
                                progress = 0.05 + 0.7 * (idx / max(1, total_sets))
                                progress_callback(progress, f"Processed {set_code:<{max_set_code_len}} ({idx+1}/{total_sets})")
                            elif not set_progress:
                                print(f"Processed {set_code:<{max_set_code_len}} ({idx+1}/{total_sets})")
                        except Exception as e:
                            logger.error(f"Error processing set {future_to_set[future][0]}: {str(e)}")
                            raise DatabaseError(f"Failed to process set: {str(e)}") from e
                            
                    if set_progress:
                        # Clear the current set line and close progress bar
                        print("\033[K", end='\r')
                        set_progress.close()

                logger.debug(f"Processed {len(results['printings'])} printings with {results['skipped']} skipped.\n Committing to database...")
                try:
                    if progress_callback:
                        progress_callback(0.75, "Adding cards to database...")
                    session.add_all(results["cards"])
                    if progress_callback:
                        progress_callback(0.80, "Adding printings to database...")
                    session.add_all(results["printings"])
                except SQLAlchemyError as e:
                    raise DatabaseError(f"Failed to add cards to database: {str(e)}") from e

                if progress_callback:
                    progress_callback(0.85, "Setting up card relationships...")

                logger.debug("Setting up relationships between CardDB and CardPrintingDB...")

                # Set newest_printing_uuid for each CardDB using the pre-built cache
                for card in results["cards"]:
                    printings = card_printings_map.get(card.name, [])
                    if printings:
                        # Find the printing with the latest release date (tiebreaker: max uuid)
                        newest = max(printings, key=lambda uuid: (printing_release_map.get(uuid) or date.min, uuid))
                        card.newest_printing_uuid = newest

                try:
                    if progress_callback:
                        progress_callback(0.90, "Updating import log...")
                    update_import_time(session=session, json_path=json_path, mtime=mtime, meta_date=meta_date)
                    if progress_callback:
                        progress_callback(0.95, "Committing changes...")
                    session.commit()
                except SQLAlchemyError as e:
                    raise DatabaseError(f"Failed to update import time: {str(e)}") from e

                if progress_callback:
                    progress_callback(1.0, f"Card import complete. {len(results['cards'])} unique cards, {len(results['printings'])} printings, {results['skipped']} skipped.")

    # Optionally load inventory after cards
    if inventory_path:
        try:
            load_inventory(session, inventory_path)
            session.commit()
            if progress_callback:
                progress_callback(1.0, "Inventory import complete.")
        except Exception as e:
            logger.error(f"Failed to load inventory: {e}")
            raise DatabaseError(f"Failed to load inventory: {str(e)}") from e


def bootstrap_inventory(
    inventory_path: str,
    db_url: str = "sqlite:///cards.db",
    use_tqdm: bool = True
) -> None:
    """Load inventory data into the database from a file.

    This function creates its own session and manages it. It ensures tables exist,
    loads inventory, and commits changes.

    Args:
        inventory_path: Path to the inventory file.
        db_url: SQLAlchemy database URL.
        use_tqdm: Whether to use tqdm progress bars.
        
    Raises:
        FileNotFoundError: If the inventory file doesn't exist.
        DatabaseError: If there's a database error.
    """
    from mtg_deck_builder.db import get_session
    logger.debug(f"Starting bootstrap_inventory with inventory_path={inventory_path}, db_url={db_url}")
    
    try:
        engine = setup_database(db_url)  # Ensure tables exist if this is called independently
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to setup database: {str(e)}") from e
        
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        if not os.path.exists(inventory_path):
            logger.error(f"File not found: {inventory_path}")
            raise FileNotFoundError(f"Inventory file not found: {inventory_path}")

        try:
            load_inventory(session, inventory_path)
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to load inventory data: {str(e)}") from e

        logger.debug("Committing database changes...")
        try:
            session.commit()
        except SQLAlchemyError as e:
            raise DatabaseError(f"Failed to commit inventory changes: {str(e)}") from e
            
    finally:
        session.close()
        
    logger.info("Bootstrap inventory complete.")

