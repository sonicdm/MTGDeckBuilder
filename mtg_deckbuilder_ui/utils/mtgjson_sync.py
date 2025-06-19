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
from mtg_deckbuilder_ui.db.models import ImportLog
from mtg_deckbuilder_ui.db.bootstrap import bootstrap

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
        "allprintings": app_config.get_path("allprintings"),
        "database": app_config.get_path("database"),
        "keywords": app_config.get_path("keywords"),
        "cardtypes": app_config.get_path("cardtypes"),
    }


def get_app_config_urls() -> Dict[str, str]:
    """Helper to get all relevant URLs from the app_config singleton."""
    return {
        "meta": app_config.get("MTGJSON", "meta_url"),
        "allprintings": app_config.get("MTGJSON", "allprintings_url"),
        "keywords": app_config.get("MTGJSON", "keywords_url"),
        "cardtypes": app_config.get("MTGJSON", "cardtypes_url"),
    }


def backup_old_json(json_path: Path, meta_date: Optional[datetime] = None) -> None:
    """Backup an existing JSON file.

    Args:
        json_path: Path to the JSON file to backup.
        meta_date: Optional meta date to include in backup filename.
    """
    json_path = Path(json_path)
    if not json_path.exists():
        return

    try:
        if meta_date:
            safe_meta_date = meta_date.strftime("%Y%m%d")
            backup_zip = json_path.with_name(json_path.stem + f"_{safe_meta_date}.zip")
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_zip = json_path.with_name(json_path.stem + f"_{timestamp}.zip")

        with zipfile.ZipFile(str(backup_zip), "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(str(json_path), arcname=json_path.name)

        print(f"[mtgjson_sync] Backed up {json_path} to {backup_zip}")

    except Exception as e:
        print(f"[mtgjson_sync] Failed to backup {json_path}: {e}")
        raise DownloadError(f"Failed to backup {json_path}") from e


def download_file(
    url: str,
    local_path: Path,
    is_zip: bool = False,
    progress_callback: Optional[Callable[[float, str], None]] = None,
) -> None:
    """Download a file from URL and save to local path.

    Args:
        url: URL to download from.
        local_path: Local path to save to.
        is_zip: Whether the file is a zip archive.
        progress_callback: Optional callback for progress updates.
    """
    local_path = Path(local_path)
    try:
        print(f"[mtgjson_sync] Downloading {url} to {local_path}")

        if is_zip:
            r = requests.get(url, stream=True, timeout=60)
            r.raise_for_status()
            total_size = int(r.headers.get("content-length", 0))

            print(
                f"[mtgjson_sync] Downloading {local_path.name} ({total_size/1024/1024:.1f} MB)"
            )
            zip_bytes = bytearray()
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    zip_bytes.extend(chunk)
                    if progress_callback:
                        progress = len(zip_bytes) / total_size
                        progress_callback(progress, f"Downloading {local_path.name}")

            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
                for name in z.namelist():
                    if name.endswith(local_path.name):
                        with z.open(name) as src, open(str(local_path), "wb") as dst:
                            dst.write(src.read())
                        break
        else:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            with open(str(local_path), "wb") as f:
                f.write(r.content)

        print(f"[mtgjson_sync] Successfully downloaded {local_path}")

    except requests.RequestException as e:
        print(f"[mtgjson_sync] Failed to download {url}: {e}")
        raise DownloadError(f"Failed to download {url}") from e
    except Exception as e:
        print(f"[mtgjson_sync] Failed to save {local_path}: {e}")
        raise DownloadError(f"Failed to save {local_path}") from e


def update_database_with_json(
    json_path: str,
    db_path: str,
    meta_date: Optional[datetime],
    progress_callback: Optional[Callable[[float, str], None]] = None,
) -> None:
    """Update the database with new MTGJSON data.

    Args:
        json_path: Path to AllPrintings.json.
        db_path: Path to SQLite database.
        meta_date: Meta date of the new data.
        progress_callback: Optional callback for progress updates.
    """
    try:
        print("[mtgjson_sync] Updating database with new MTGJSON data...")

        bootstrap(
            json_path=json_path,
            db_url=f"sqlite:///{db_path}",
            use_tqdm=True,
            progress_callback=progress_callback,
        )

        print("[mtgjson_sync] Database update complete")

    except Exception as e:
        print(f"[mtgjson_sync] Failed to update database: {e}")
        raise DatabaseUpdateError("Failed to update database") from e


def mtgjson_sync(
    progress_callback: Optional[Callable[[float, str], None]] = None,
) -> Dict[str, Any]:
    """Check and sync MTGJSON data if outdated or missing.

    Args:
        progress_callback: Optional callback for progress updates.

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
            "allprintings": False,
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
        if paths["database"].exists():
            try:
                from sqlalchemy import create_engine
                from sqlalchemy.orm import sessionmaker

                engine = create_engine(f"sqlite:///{paths['database']}")
                Session = sessionmaker(bind=engine)
                session = Session()
                # Check if the database is empty
                if session.query(ImportLog).count() == 0:
                    db_needs_update = True
            except Exception as e:
                logger.error(
                    "Failed to check database: %s\n%s", e, traceback.format_exc()
                )
                result["errors"].append(
                    f"Failed to check database: {type(e).__name__}: {e}\n{traceback.format_exc()}"
                )
                return result

        # Sync AllPrintings.json
        if not paths["allprintings"].exists() or remote_date > local_date:
            print("[mtgjson_sync] AllPrintings.json is outdated or missing.")
            result["updates"]["allprintings"] = True
            backup_old_json(
                paths["allprintings"],
                meta_date=datetime.strptime(remote_date, "%Y-%m-%d"),
            )
            download_file(
                urls["allprintings"],
                paths["allprintings"],
                is_zip=True,
                progress_callback=progress_callback,
            )
        else:
            print("[mtgjson_sync] AllPrintings.json is up to date.")

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

        # Update database if needed
        if db_needs_update and result["updates"]["allprintings"]:
            print("[mtgjson_sync] Database update required.")
            result["updates"]["database"] = True
            update_database_with_json(
                paths["allprintings"],
                paths["database"],
                datetime.strptime(remote_date, "%Y-%m-%d"),
                progress_callback,
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
