# db/loader.py
import os
import logging
from datetime import datetime
from typing import Optional
from mtg_deck_builder.db.models import ImportLog, InventoryItemDB
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

def is_reload_needed(session: Session, json_path: str, meta_date: datetime = None, mtime: float = None) -> bool:
    existing_log = session.query(ImportLog).filter_by(json_path=json_path).order_by(ImportLog.mtime.desc()).first()
    if existing_log is None:
        return True
    return existing_log.mtime < mtime

def update_import_time(session: Session, json_path: str, meta_date: datetime = None, mtime: float = None) -> None:
    """
    Update or create an import log entry for this import operation.
    Uses merge to update existing entries or create new ones.
    
    Args:
        session: SQLAlchemy session
        json_path: Path to the imported JSON file
        meta_date: Date from the file's meta section
        mtime: File modification time
        
    Raises:
        SQLAlchemyError: If there's an error updating the import log
    """
    try:
        # First check if a record exists
        existing = session.query(ImportLog).filter_by(json_path=json_path).first()
        if existing:
            # Update existing record
            existing.meta_date = meta_date
            existing.mtime = mtime
        else:
            # Create new record
            log_entry = ImportLog(json_path=json_path, meta_date=meta_date, mtime=mtime)
            session.add(log_entry)
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to update import log: {e}")
        raise

def load_inventory(session: Session, inventory_path: str) -> None:
    """
    Load inventory data from a file into the database.
    
    Args:
        session: SQLAlchemy session
        inventory_path: Path to the inventory file
    """
    if not os.path.exists(inventory_path):
        logger.error(f"Inventory file not found: {inventory_path}")
        return

    with open(inventory_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line in lines:
        parts = line.strip().split(' ', 1)
        if len(parts) != 2:
            continue
        quantity, name = parts
        try:
            quantity = int(quantity)
        except ValueError:
            logger.warning(f"Invalid quantity in inventory file: {line.strip()}")
            continue

        session.merge(InventoryItemDB(card_name=name, quantity=quantity, is_infinite=(name in {"Plains", "Island", "Swamp", "Mountain", "Forest"})))

    session.commit()