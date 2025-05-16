# db/loader.py
import os
from datetime import datetime
from mtg_deck_builder.db.models import ImportLog, InventoryItemDB
from sqlalchemy.orm import Session

def is_reload_needed(session: Session, json_path: str, meta_date: datetime = None, mtime: float = None) -> bool:
    existing_log = session.query(ImportLog).filter_by(json_path=json_path).order_by(ImportLog.mtime.desc()).first()
    if existing_log is None:
        return True
    return existing_log.mtime < mtime

def update_import_time(session: Session, json_path: str, meta_date: datetime = None, mtime: float = None):
    log_entry = ImportLog(json_path=json_path, meta_date=meta_date, mtime=mtime)
    session.add(log_entry)
    session.commit()

def load_inventory(session: Session, inventory_path: str):
    if not os.path.exists(inventory_path):
        print(f"Inventory file not found: {inventory_path}")
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
            continue

        session.merge(InventoryItemDB(card_name=name, quantity=quantity, is_infinite=(name in {"Plains", "Island", "Swamp", "Mountain", "Forest"})))

    session.commit()