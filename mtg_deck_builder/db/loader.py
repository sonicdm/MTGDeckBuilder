# db/loader.py
import json
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

def is_reload_needed(current_meta_file: Path, new_meta_file: Path) -> bool:
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
            return os.path.getmtime(str(current_meta_file)) < os.path.getmtime(str(new_meta_file))
        current_date = datetime.strptime(current_date_str, "%Y-%m-%d")
        new_date = datetime.strptime(new_date_str, "%Y-%m-%d")
        return current_date < new_date
    except Exception as e:
        logger.warning(f"Error comparing meta files: {e}")
        # Fallback: reload if new_meta_file is newer by mtime
        try:
            return os.path.getmtime(str(current_meta_file)) < os.path.getmtime(str(new_meta_file))
        except Exception:
            return False