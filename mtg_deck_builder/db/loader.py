"""Database loader utilities."""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from mtg_deck_builder.db.mtgjson_models.base import MTGJSONBase

logger = logging.getLogger(__name__)


def is_reload_needed(current_meta_file: Path, new_meta_file: Path) -> bool:
    """Check if database reload is needed based on meta files."""
    if not current_meta_file.exists():
        return True

    if not new_meta_file.exists():
        return False
    
    try:
        with open(current_meta_file, "r", encoding="utf-8") as f:
            current_meta = json.load(f)
        with open(new_meta_file, "r", encoding="utf-8") as f:
            new_meta = json.load(f)
        
        current_date_str = current_meta.get("meta", {}).get("date")
        new_date_str = new_meta.get("meta", {}).get("date")
        
        if not current_date_str or not new_date_str:
            # If either date is missing, fallback to file mtime
            return os.path.getmtime(str(current_meta_file)) < os.path.getmtime(
                str(new_meta_file)
            )
        
        current_date = datetime.strptime(current_date_str, "%Y-%m-%d")
        new_date = datetime.strptime(new_date_str, "%Y-%m-%d")
        return current_date < new_date
    
    except Exception as e:
        logger.warning(f"Error comparing meta files: {e}")
        # Fallback: reload if new_meta_file is newer by mtime
        try:
            return os.path.getmtime(str(current_meta_file)) < os.path.getmtime(
                str(new_meta_file)
            )
        except Exception:
            return False


def load_database(db_path: Path):
    """Load database from path."""
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Create tables if they don't exist
        MTGJSONBase.metadata.create_all(engine)
        logger.info(f"Database loaded from {db_path}")
        return session
    except Exception as e:
        logger.error(f"Error loading database: {e}")
        session.close()
        raise