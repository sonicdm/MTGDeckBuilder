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
import logging
from tqdm import tqdm
from pathlib import Path
from typing import Optional, Dict, Any, Callable, TextIO
import traceback

from mtg_deckbuilder_ui.app_config import app_config

# Configure logging
logger = logging.getLogger(__name__)


class MTGJSONSyncError(Exception):
    """Base exception for MTGJSON synchronization errors."""

    pass


class DownloadError(MTGJSONSyncError):
    """Error during file download."""

    pass


class DatabaseUpdateError(MTGJSONSyncError):
    """Error during database update."""

    pass


def get_app_config_paths() -> Dict[str, Path]:
    """Helper to get all relevant paths from the app_config singleton."""
    return {
        "meta": app_config.get_path("meta"),
        "allprintings_sqlite": app_config.get_path("allprintings_sqlite"),
        "keywords": app_config.get_path("keywords"),
        "cardtypes": app_config.get_path("cardtypes"),
    }


def get_app_config_urls() -> Dict[str, str]:
    """Helper to get all relevant URLs from the app_config singleton."""
    return {
        "meta": app_config.get("MTGJSON", "meta_url") or "",
        "sqlite": app_config.get("MTGJSON", "allprintings_sqlite_url") or "",
        "keywords": app_config.get("MTGJSON", "keywords_url") or "",
        "cardtypes": app_config.get("MTGJSON", "cardtypes_url") or "",
    }


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


def mtgjson_sync(
    progress_callback: Optional[Callable[[float, str], None]] = None,
    force_update: bool = False,
) -> Dict[str, Any]:
    """Check and sync MTGJSON data if outdated or missing.

    Args:
        progress_callback: Optional callback for progress updates.
        force_update: Whether to force update the database schema.
    Returns:
        Dict containing sync results and status.
    """
    print("\n[mtgjson_sync] Starting MTGJSON synchronization...")
    paths = get_app_config_paths()
    urls = get_app_config_urls()

    # Initialize result dict
    result = {
        "status": "success",
        "updates": {
            "meta": False,
            "sqlite": False,
            "keywords": False,
            "cardtypes": False,
            "database": False,
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
                # Check if the database file is empty or very small (indicating it needs data)
                db_size = paths["allprintings_sqlite"].stat().st_size
                if db_size < 1024:  # Less than 1KB, likely empty
                    db_needs_update = True
                    print(f"[mtgjson_sync] Database file is small ({db_size} bytes), needs update.")
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
                from mtg_deck_builder.db.setup import build_summary_cards_from_mtgjson
                
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
