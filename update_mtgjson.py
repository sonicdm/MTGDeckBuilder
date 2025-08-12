#!/usr/bin/env python3
"""
MTGJSON Synchronization Script

This script synchronizes local MTGJSON data with the remote MTGJSON API.
It downloads AllPrintings.sqlite, Keywords.json, CardTypes.json, and Meta.json,
then builds summary cards for efficient querying. Optionally imports an inventory file.

Usage:
    python update_mtgjson.py [--force] [--inventory <inventory_file>]

Options:
    --force       Force update even if data appears to be current
    --inventory   Path to inventory file to import after sync
"""

import os
import sys
import json
import zipfile
import io
import logging
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from tqdm import tqdm
import argparse
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Default paths and URLs
DEFAULT_PATHS = {
    "meta": "data/mtgjson/meta.json",
    "allprintings_sqlite": "data/mtgjson/AllPrintings.sqlite",
    "keywords": "data/mtgjson/keywords.json",
    "cardtypes": "data/mtgjson/cardtypes.json",
    "inventory": "data/inventory/inventory.txt",
}

DEFAULT_URLS = {
    "meta": "https://mtgjson.com/api/v5/Meta.json",
    "sqlite": "https://mtgjson.com/api/v5/AllPrintings.sqlite.zip",
    "keywords": "https://mtgjson.com/api/v5/Keywords.json",
    "cardtypes": "https://mtgjson.com/api/v5/CardTypes.json",
}

class MTGJSONSyncError(Exception):
    """Base exception for MTGJSON synchronization errors."""
    pass

class DownloadError(MTGJSONSyncError):
    """Error during file download."""
    pass

class DatabaseUpdateError(MTGJSONSyncError):
    """Error during database update."""
    pass

def backup_old_sqlite(sqlite_path: Path, meta_date: Optional[datetime] = None) -> None:
    """Backup an existing SQLite file.

    Args:
        sqlite_path: Path to the SQLite file to backup.
        meta_date: Optional meta date to include in backup filename.
    """
    sqlite_path = Path(sqlite_path)
    if not sqlite_path.exists():
        return

    try:
        if meta_date:
            safe_meta_date = meta_date.strftime("%Y%m%d")
            backup_zip = sqlite_path.with_name(sqlite_path.stem + f"_{safe_meta_date}.zip")
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_zip = sqlite_path.with_name(sqlite_path.stem + f"_{timestamp}.zip")

        # Ensure parent directory exists
        backup_zip.parent.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(str(backup_zip), "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(str(sqlite_path), arcname=sqlite_path.name)

        print(f"[mtgjson_sync] Backed up {sqlite_path} to {backup_zip}")

    except Exception as e:
        print(f"[mtgjson_sync] Failed to backup {sqlite_path}: {e}")
        raise DownloadError(f"Failed to backup {sqlite_path}") from e

def download_file(
    url: str,
    local_path: Path,
    is_zip: bool = False,
    progress_callback: Optional[Callable[[float, str], None]] = None,
) -> None:
    """Download a file from URL to local path.

    Args:
        url: URL to download from.
        local_path: Local path to save to.
        is_zip: Whether the file is a zip archive.
        progress_callback: Optional callback for progress updates.
    """
    try:
        print(f"[mtgjson_sync] Downloading {url} to {local_path}")

        # Ensure parent directory exists
        local_path.parent.mkdir(parents=True, exist_ok=True)

        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()

        total_size = int(response.headers.get("content-length", 0))
        downloaded = 0
        
        use_tqdm = progress_callback is None
        progress_bar = None
        if use_tqdm:
            progress_bar = tqdm(
                total=total_size,
                unit='iB',
                unit_scale=True,
                desc=f"Downloading {local_path.name}"
            )

        if is_zip:
            # Download zip file and extract the target file
            zip_bytes = bytearray()
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    zip_bytes.extend(chunk)
                    downloaded += len(chunk)
                    if use_tqdm and progress_bar:
                        progress_bar.update(len(chunk))
                    elif progress_callback and total_size > 0:
                        progress = downloaded / total_size
                        progress_callback(progress, f"Downloading {local_path.name}")

            # Extract the file from zip
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
                for name in z.namelist():
                    if name.endswith(local_path.name):
                        with z.open(name) as src, open(local_path, "wb") as dst:
                            dst.write(src.read())
                        break
                else:
                    # If exact name not found, extract the first .sqlite file
                    for name in z.namelist():
                        if name.endswith('.sqlite'):
                            with z.open(name) as src, open(local_path, "wb") as dst:
                                dst.write(src.read())
                            break
        else:
            # Download file directly
            with open(local_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if use_tqdm and progress_bar:
                            progress_bar.update(len(chunk))
                        elif progress_callback and total_size > 0:
                            progress = downloaded / total_size
                            progress_callback(progress, f"Downloading {local_path.name}")

        if progress_bar:
            progress_bar.close()

        print(f"[mtgjson_sync] Downloaded {local_path} successfully")

    except Exception as e:
        print(f"[mtgjson_sync] Failed to download {url}: {e}")
        raise DownloadError(f"Failed to download {url}") from e

def build_summary_cards_from_mtgjson(mtgjson_db_path: Path) -> None:
    """
    Build summary cards from the MTGJSON database and add them to the same database.
    
    This function reads the raw MTGJSON card data and creates summary cards that
    aggregate information across all printings of each card. The summary cards
    are stored in the same database for efficient querying.
    
    Args:
        mtgjson_db_path: Path to the MTGJSON SQLite database (contains raw data and will contain summary cards)
    """
    try:
        from mtg_deck_builder.db.setup import build_summary_cards_from_mtgjson as build_summary
        build_summary(mtgjson_db_path)
    except ImportError:
        print("[mtgjson_sync] Warning: Could not import build_summary_cards_from_mtgjson function.")
        print("[mtgjson_sync] Summary cards will not be built. The database may not be fully functional.")
        print("[mtgjson_sync] Make sure the mtg_deck_builder package is properly installed.")

def mtgjson_sync(
    progress_callback: Optional[Callable[[float, str], None]] = None,
    force_update: bool = False,
    inventory_file: Optional[str] = None,
) -> Dict[str, Any]:
    """Check and sync MTGJSON data if outdated or missing.

    Args:
        progress_callback: Optional callback for progress updates.
        force_update: Whether to force update the database schema.
    Returns:
        Dict containing sync results and status.
    """
    print("\n[mtgjson_sync] Starting MTGJSON synchronization...")
    
    # Convert paths to Path objects
    paths = {key: Path(path) for key, path in DEFAULT_PATHS.items()}
    urls = DEFAULT_URLS

    # Initialize result dict
    result = {
        "status": "success",
        "updates": {
            "meta": False,
            "sqlite": False,
            "keywords": False,
            "cardtypes": False,
            "database": False,
            "inventory": False,
        },
        "versions": {
            "local": {"version": "", "date": ""},
            "remote": {"version": "", "date": ""},
        },
        "errors": [],
    }

    try:
        # Check local meta data
        local_version = local_date = ""
        if paths["meta"].exists():
            try:
                with open(paths["meta"], "r", encoding="utf-8") as f:
                    local_meta = json.load(f)
                local_version = local_meta.get("meta", {}).get("version", "")
                local_date = local_meta.get("meta", {}).get("date", "")
                result["versions"]["local"] = {
                    "version": local_version,
                    "date": local_date,
                }
                print(
                    f"[mtgjson_sync] Local meta: version={local_version}, date={local_date}"
                )
            except Exception as e:
                logger.error(
                    "Failed to read local meta: %s\n%s", e, traceback.format_exc()
                )
                result["errors"].append(
                    f"Failed to read local meta: {type(e).__name__}: {e}\n{traceback.format_exc()}"
                )

        # Get remote meta data
        try:
            print(f"[mtgjson_sync] Fetching remote meta from {urls['meta']}")
            remote_meta = requests.get(urls["meta"], timeout=10).json()
            remote_version = remote_meta.get("meta", {}).get("version", "")
            remote_date = remote_meta.get("meta", {}).get("date", "")
            result["versions"]["remote"] = {
                "version": remote_version,
                "date": remote_date,
            }
            print(
                f"[mtgjson_sync] Remote meta: version={remote_version}, date={remote_date}"
            )
        except Exception as e:
            logger.error(
                "Failed to fetch remote meta: %s\n%s", e, traceback.format_exc()
            )
            result["errors"].append(
                f"Failed to fetch remote meta: {type(e).__name__}: {e}\n{traceback.format_exc()}"
            )
            return result

        # Check if DB needs update
        db_needs_update = False
        if paths["allprintings_sqlite"].exists():
            try:
                # Use mtg_deck_builder utilities to check if reload is needed
                from mtg_deck_builder.db.loader import is_reload_needed
                
                # Check if the database file is empty or very small (indicating it needs data)
                db_size = paths["allprintings_sqlite"].stat().st_size
                if db_size < 1024:  # Less than 1KB, likely empty
                    db_needs_update = True
                    print(f"[mtgjson_sync] Database file is small ({db_size} bytes), needs update.")
                else:
                    # Use the existing utility to check if reload is needed based on meta files
                    # We'll create a temporary remote meta file for comparison
                    temp_remote_meta = paths["meta"].parent / "temp_remote_meta.json"
                    try:
                        with open(temp_remote_meta, "w", encoding="utf-8") as f:
                            json.dump(remote_meta, f, indent=4)
                        
                        if is_reload_needed(paths["meta"], temp_remote_meta):
                            db_needs_update = True
                            print("[mtgjson_sync] Database reload needed based on meta comparison.")
                    finally:
                        # Clean up temporary file
                        if temp_remote_meta.exists():
                            temp_remote_meta.unlink()
                            
            except Exception as e:
                logger.error(
                    "Failed to check database: %s\n%s", e, traceback.format_exc()
                )
                result["errors"].append(
                    f"Failed to check database: {type(e).__name__}: {e}\n{traceback.format_exc()}"
                )
                return result

        # Sync AllPrintings.sqlite
        if not paths["allprintings_sqlite"].exists() or remote_date > local_date or force_update:
            print("[mtgjson_sync] AllPrintings.sqlite is outdated or missing.")
            result["updates"]["sqlite"] = True
            db_needs_update = True  # If we're downloading new SQLite, we need to update DB
            backup_old_sqlite(
                paths["allprintings_sqlite"],
                meta_date=datetime.strptime(remote_date, "%Y-%m-%d"),
            )
            download_file(
                urls["sqlite"],
                paths["allprintings_sqlite"],
                is_zip=True,  # SQLite file is zipped
                progress_callback=progress_callback,
            )
        else:
            print("[mtgjson_sync] AllPrintings.sqlite is up to date.")

        # Sync Keywords.json
        if not paths["keywords"].exists() or remote_date > local_date:
            print("[mtgjson_sync] Keywords.json is outdated or missing.")
            result["updates"]["keywords"] = True
            download_file(urls["keywords"], paths["keywords"])
        else:
            print("[mtgjson_sync] Keywords.json is up to date.")

        # Sync CardTypes.json
        if not paths["cardtypes"].exists() or remote_date > local_date:
            print("[mtgjson_sync] CardTypes.json is outdated or missing.")
            result["updates"]["cardtypes"] = True
            download_file(urls["cardtypes"], paths["cardtypes"])
        else:
            print("[mtgjson_sync] CardTypes.json is up to date.")

        # Update Meta.json after successful downloads
        if any(result["updates"].values()):
            print("[mtgjson_sync] Updating local meta file.")
            result["updates"]["meta"] = True
            with open(paths["meta"], "w", encoding="utf-8") as f:
                json.dump(remote_meta, f, indent=4)

        # Update database if needed (build summary cards)
        if db_needs_update or result["updates"]["sqlite"]:
            print("[mtgjson_sync] Database update required.")
            result["updates"]["database"] = True
            try:
                # Use mtg_deck_builder utilities for database setup
                from mtg_deck_builder.db.setup import setup_database
                from mtg_deck_builder.db.mtgjson_models.base import MTGJSONBase
                
                # Ensure database is properly set up
                db_url = f"sqlite:///{paths['allprintings_sqlite']}"
                setup_database(db_url, base=MTGJSONBase)
                
                # Build summary cards in the MTGJSON database
                build_summary_cards_from_mtgjson(mtgjson_db_path=paths['allprintings_sqlite'])
                if progress_callback:
                    progress_callback(1.0, "Summary cards built successfully.")
                print("[mtgjson_sync] Summary cards built successfully.")
                    
            except Exception as e:
                logger.error(
                    "Failed to build summary cards: %s\n%s", e, traceback.format_exc()
                )
                result["errors"].append(
                    f"Failed to build summary cards: {type(e).__name__}: {e}\n{traceback.format_exc()}"
                )
        else:
            print("[mtgjson_sync] Database is up to date, no update needed.")

        # Import inventory file if provided
        if inventory_file:
            print(f"[mtgjson_sync] Importing inventory from {inventory_file}...")
            result["updates"]["inventory"] = True
            try:
                # Use mtg_deck_builder utilities for database operations
                from mtg_deck_builder.db import get_session
                from mtg_deck_builder.db.setup import setup_database
                from mtg_deck_builder.db.mtgjson_models.base import MTGJSONBase
                from mtg_deck_builder.db.inventory import InventoryItem
                from import_inventory import load_inventory_items
                
                # Ensure database is set up
                db_url = f"sqlite:///{paths['allprintings_sqlite']}"
                setup_database(db_url, base=MTGJSONBase)
                
                # Import inventory using the standalone function
                load_inventory_items(inventory_file, str(paths['allprintings_sqlite']))
                print("[mtgjson_sync] Inventory imported successfully.")
                if progress_callback:
                    progress_callback(1.0, "Inventory imported successfully.")
            except Exception as e:
                logger.error(
                    "Failed to import inventory: %s\n%s", e, traceback.format_exc()
                )
                result["errors"].append(
                    f"Failed to import inventory: {type(e).__name__}: {e}\n{traceback.format_exc()}"
                )

        # Set final status
        if result["errors"]:
            result["status"] = "error"
        elif any(result["updates"].values()):
            result["status"] = "updated"
        else:
            result["status"] = "no_update_needed"

        return result

    except Exception as e:
        logger.error("Synchronization failed: %s\n%s", e, traceback.format_exc())
        result["status"] = "error"
        result["errors"].append(
            f"Synchronization failed: {type(e).__name__}: {e}\n{traceback.format_exc()}"
        )
        return result

def main():
    parser = argparse.ArgumentParser(description="Sync MTGJSON data and update the local database.")
    parser.add_argument("--force", action="store_true", help="Force update even if data is up to date.")
    parser.add_argument("--quiet", action="store_true", help="Suppress progress output.")
    parser.add_argument("--inventory", help="Path to inventory file to import after sync")
    args = parser.parse_args()

    try:
        print("Starting MTGJSON synchronization...")
        
        # Use the standalone mtgjson_sync function
        result = mtgjson_sync(force_update=args.force, inventory_file=args.inventory)
        
        # Display results
        if result["status"] == "error":
            print(f"❌ Synchronization failed with errors:")
            for error in result["errors"]:
                print(f"   {error}")
            sys.exit(1)
        elif result["status"] == "updated":
            print("✅ Synchronization completed successfully!")
            if result["updates"]:
                print("Updates performed:")
                for key, value in result["updates"].items():
                    if value:
                        print(f"   - {key}")
        else:
            print("ℹ️  No updates needed - data is already current.")
            
    except Exception as e:
        logger.error(f"Synchronization failed: {e}")
        print(f"❌ Synchronization failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 