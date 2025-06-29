"""
Database setup utilities for Magic: The Gathering deck builder.

This module provides functions to initialize the database and ensure all required tables exist.
It is safe to call setup_database multiple times; it will not drop or overwrite existing data.
"""

import sqlalchemy.engine
from sqlalchemy import create_engine, inspect
from mtg_deck_builder.db.mtgjson_models.base import MTGJSONBase
import logging
from collections import defaultdict
import json
from pathlib import Path
from sqlalchemy.orm import sessionmaker, joinedload
from tqdm import tqdm
from sqlalchemy import func, desc, and_

__all__ = ["setup_database", "force_update_schema"]

def force_update_schema(db_url: str, poolclass=None, connect_args=None, base=MTGJSONBase) -> sqlalchemy.engine.Engine:
    """
    Forces a complete update of the database schema by dropping and recreating all tables.
    WARNING: This will delete all data in the database.

    Args:
        db_url (str): SQLAlchemy database URL (e.g., 'sqlite:///path/to/db.sqlite').
        poolclass: Optional SQLAlchemy pool class.
        connect_args: Optional SQLAlchemy connect arguments.

    Returns:
        sqlalchemy.engine.Engine: The SQLAlchemy engine connected to the database.
    """
    logging.warning("Force updating database schema - this will delete all existing data!")
    
    if poolclass and connect_args:
        engine = create_engine(db_url, poolclass=poolclass, connect_args=connect_args)
    elif poolclass:
        engine = create_engine(db_url, poolclass=poolclass)
    elif connect_args:
        engine = create_engine(db_url, connect_args=connect_args)
    else:
        engine = create_engine(db_url)

    # Drop all tables and recreate them
    base.metadata.drop_all(engine)
    base.metadata.create_all(engine)
    return engine

def setup_database(db_url: str, base=MTGJSONBase, poolclass=None, connect_args=None) -> sqlalchemy.engine.Engine:
    """
    Ensures all tables exist in the database specified by db_url.

    This function creates any missing tables defined in the ORM models.
    It does NOT drop or destroy existing tables or data.
    Safe to call multiple times, including in production or test environments.

    Args:
        db_url (str): SQLAlchemy database URL (e.g., 'sqlite:///path/to/db.sqlite').
        poolclass: Optional SQLAlchemy pool class.
        connect_args: Optional SQLAlchemy connect arguments.

    Returns:
        sqlalchemy.engine.Engine: The SQLAlchemy engine connected to the database.
    """
    if poolclass and connect_args:
        engine = create_engine(db_url, poolclass=poolclass, connect_args=connect_args)
    elif poolclass:
        engine = create_engine(db_url, poolclass=poolclass)
    elif connect_args:
        engine = create_engine(db_url, connect_args=connect_args)
    else:
        engine = create_engine(db_url)

    # Check which tables exist
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    # Create only the tables that are missing
    for table in base.metadata.tables.values():
        if table.name not in existing_tables:
            logging.info(f"Table '{table.name}' not found. Creating it now.")
            table.create(engine)
    
    return engine


def _safe_list_field(value):
    """Safely convert a value to a list, handling various input formats."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return []
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
        # Fallback: treat as CSV
        return [v.strip() for v in value.split(',') if v.strip()]
    return []


def _legalities_to_dict(legality_obj):
    """Convert a legality object to a dictionary."""
    if not legality_obj:
        return {}
    from mtg_deck_builder.db.mtgjson_models.cards import MTGJSONCardLegality
    return {
        col.name: getattr(legality_obj, col.name)
        for col in MTGJSONCardLegality.__table__.columns
        if col.name != 'uuid' and getattr(legality_obj, col.name) is not None
    }


def build_summary_cards_from_mtgjson(mtgjson_db_path: Path):
    """
    Build summary cards from the MTGJSON database and add them to the same database.
    
    This function reads the raw MTGJSON card data and creates summary cards that
    aggregate information across all printings of each card. The summary cards
    are stored in the same database for efficient querying.
    
    Args:
        mtgjson_db_path: Path to the MTGJSON SQLite database (contains raw data and will contain summary cards)
    """
    from mtg_deck_builder.db.mtgjson_models.cards import MTGJSONCard, MTGJSONSet, MTGJSONSummaryCard
    
    # Convert path to SQLite URL
    db_url = f"sqlite:///{mtgjson_db_path}"
    
    # Setup database (ensures summary_cards table exists)
    engine = setup_database(db_url, base=MTGJSONBase)
    
    # Create engine and session
    session = sessionmaker(bind=engine)()
    
    BATCH_SIZE = 10000

    try:
        # Clear the summary table
        session.query(MTGJSONSummaryCard).delete()
        session.commit()

        # CTE to rank printings and aggregate set codes using window functions
        ranked_printings_cte = session.query(
            MTGJSONCard.uuid,
            func.row_number().over(
                partition_by=MTGJSONCard.name,
                order_by=desc(MTGJSONSet.releaseDate)
            ).label('rn'),
            func.group_concat(MTGJSONCard.setCode).over(
                partition_by=MTGJSONCard.name
            ).label('all_set_codes')
        ).join(
            MTGJSONSet, MTGJSONCard.setCode == MTGJSONSet.code
        ).subquery('ranked_printings')

        # Query to get the latest printing for each card using the CTE
        latest_printings_query = session.query(
            MTGJSONCard,
            ranked_printings_cte.c.all_set_codes
        ).join(
            ranked_printings_cte,
            MTGJSONCard.uuid == ranked_printings_cte.c.uuid,
        ).filter(ranked_printings_cte.c.rn == 1).options(
            joinedload(MTGJSONCard.legalities)
        )

        logging.info("Fetching latest printings for all cards...")
        latest_printings = latest_printings_query.all()
        logging.info(f"Found {len(latest_printings)} unique cards to process.")

        # Process cards in batches
        total_cards = len(latest_printings)
        with tqdm(total=total_cards, desc="Processing cards", unit="card") as pbar:
            for i in range(0, total_cards, BATCH_SIZE):
                batch_printings = latest_printings[i:i + BATCH_SIZE]
                summary_cards = []

                for newest_printing, all_set_codes in batch_printings:
                    try:
                        summary_card = MTGJSONSummaryCard(
                            name=newest_printing.name,
                            set_code=newest_printing.setCode,
                            rarity=newest_printing.rarity,
                            type=newest_printing.type,
                            mana_cost=newest_printing.manaCost,
                            converted_mana_cost=newest_printing.manaValue,
                            power=newest_printing.power,
                            toughness=newest_printing.toughness,
                            loyalty=newest_printing.loyalty,
                            text=newest_printing.text,
                            flavor_text=newest_printing.flavorText,
                            artist=newest_printing.artist,
                            printing_set_codes=all_set_codes.split(','),
                            color_identity=_safe_list_field(newest_printing.colorIdentity),
                            colors=_safe_list_field(newest_printing.colors),
                            supertypes=_safe_list_field(newest_printing.supertypes),
                            subtypes=_safe_list_field(newest_printing.subtypes),
                            keywords=_safe_list_field(newest_printing.keywords),
                            legalities=_legalities_to_dict(newest_printing.legalities),
                            types=_safe_list_field(newest_printing.types)
                        )
                        summary_cards.append(summary_card)
                    except Exception as e:
                        logging.error(f"Error processing card {newest_printing.name}: {e}")
                        continue
                    pbar.update(1)
                
                # Bulk save the batch, but don't commit yet
                if summary_cards:
                    session.bulk_save_objects(summary_cards)

            # Commit once at the very end
            session.commit()

    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

