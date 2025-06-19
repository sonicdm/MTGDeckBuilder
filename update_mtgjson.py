#!/usr/bin/env python3
"""
MTGJSON Synchronization Script

This script synchronizes local MTGJSON data with the remote MTGJSON API.
It handles downloading and updating card data, keywords, and card types,
and manages the local database accordingly.

Usage:
    python update_mtgjson.py [--force]

Options:
    --force    Force update even if data appears to be current
"""

import os
import sys
import json
import zipfile
import io
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, Callable, TextIO
import requests
from tqdm import tqdm
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import contextlib
import threading
from queue import Queue
import time
import shutil
import argparse

from mtg_deck_builder.db.models import ImportLog
from mtg_deck_builder.db.bootstrap import bootstrap, DatabaseError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MTGJSONError(Exception):
    """Base exception for MTGJSON synchronization errors."""
    pass

class DownloadError(MTGJSONError):
    """Raised when downloading MTGJSON data fails."""
    pass

class DatabaseUpdateError(MTGJSONError):
    """Raised when updating the database fails."""
    pass

class ProgressManager:
    """Manages progress reporting and output buffering."""
    
    def __init__(self, file: TextIO = sys.stdout):
        self.file = file
        self.queue = Queue()
        self.thread = None
        self._stop = False
        self.terminal_width = shutil.get_terminal_size().columns
        
    def start(self):
        """Start the progress manager thread."""
        self.thread = threading.Thread(target=self._process_queue)
        self.thread.daemon = True
        self.thread.start()
        
    def stop(self):
        """Stop the progress manager thread."""
        self._stop = True
        if self.thread:
            self.thread.join()
            
    def _process_queue(self):
        """Process messages from the queue."""
        while not self._stop:
            try:
                msg = self.queue.get(timeout=0.1)
                if msg is None:
                    continue
                self.file.write(msg)
                self.file.flush()
            except Exception:
                pass
                
    def write(self, msg: str):
        """Write a message to the output."""
        self.queue.put(msg)
        
    def flush(self):
        """Flush the output buffer."""
        self.file.flush()

@contextlib.contextmanager
def buffered_output(file: TextIO = sys.stdout):
    """Context manager for buffered output."""
    manager = ProgressManager(file)
    manager.start()
    try:
        yield manager
    finally:
        manager.stop()

class MTGJSONSync:
    """Handles synchronization of MTGJSON data."""
    
    def __init__(
        self,
        data_dir: str = "data",
        db_path: str = "cards.db",
        force_update: bool = False,
        output: Optional[TextIO] = None,
        inventory_dir: str = "inventory_files"
    ):
        """Initialize MTGJSON synchronization.
        
        Args:
            data_dir: Directory to store MTGJSON data files.
            db_path: Path to the SQLite database.
            force_update: Whether to force update even if data appears current.
            output: Optional output stream for progress reporting.
        """
        self.data_dir = Path(data_dir)
        self.inventory_dir = Path(inventory_dir)
        self.db_path = Path(db_path)
        self.force_update = force_update
        self.output = output or sys.stdout
        self.terminal_width = shutil.get_terminal_size().columns
        
        # Create data directory if it doesn't exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Define file paths
        self.allprintings_path = self.data_dir / "AllPrintings.json"
        self.meta_path = self.data_dir / "Meta.json"
        self.keywords_path = self.data_dir / "Keywords.json"
        self.cardtypes_path = self.data_dir / "CardTypes.json"
        self.inventory_path = self.inventory_dir / "card inventory.txt"
        
        # Define URLs
        self.meta_url = "https://mtgjson.com/api/v5/Meta.json"
        self.allprintings_url = "https://mtgjson.com/api/v5/AllPrintings.json.zip"
        self.keywords_url = "https://mtgjson.com/api/v5/Keywords.json"
        self.cardtypes_url = "https://mtgjson.com/api/v5/CardTypes.json"

    def backup_old_json(self, json_path: Path, meta_date: Optional[datetime] = None) -> None:
        """Backup an existing JSON file.
        
        Args:
            json_path: Path to the JSON file to backup.
            meta_date: Optional meta date to include in backup filename.
        """
        if not json_path.exists():
            return
            
        try:
            # Use meta_date in backup filename if provided, else fallback to timestamp
            if meta_date:
                # Format date in a way that's safe for filenames
                safe_meta_date = meta_date.strftime("%Y%m%d")
                backup_zip = json_path.parent / f"{json_path.stem}_{safe_meta_date}.zip"
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_zip = json_path.parent / f"{json_path.stem}_{timestamp}.zip"
                
            with zipfile.ZipFile(backup_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(json_path, arcname=json_path.name)
                
            logger.info(f"Backed up {json_path} to {backup_zip}")
            
        except Exception as e:
            logger.error(f"Failed to backup {json_path}: {e}")
            raise DownloadError(f"Failed to backup {json_path}") from e

    def get_db_last_import_meta_date(self) -> Optional[datetime]:
        """Get the meta date of the last successful database import.
        
        Returns:
            The meta date of the last import, or None if no import found.
        """
        if not self.db_path.exists():
            return None
            
        try:
            engine = create_engine(f"sqlite:///{self.db_path}")
            Session = sessionmaker(bind=engine)
            session = Session()
            
            try:
                latest = session.query(ImportLog).order_by(ImportLog.meta_date.desc()).first()
                return latest.meta_date if latest else None
            finally:
                session.close()
                
        except SQLAlchemyError as e:
            logger.error(f"Failed to query ImportLog: {e}")
            return None

    def download_file(
        self,
        url: str,
        local_path: Path,
        is_zip: bool = False,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> None:
        """Download a file from a URL.
        
        Args:
            url: URL to download from.
            local_path: Local path to save the file.
            is_zip: Whether the file is a zip archive.
            progress_callback: Optional callback for progress updates.
            
        Raises:
            DownloadError: If download fails.
        """
        try:
            logger.info(f"Downloading {url} to {local_path}")
            
            if is_zip:
                # Download zip file with progress bar
                r = requests.get(url, stream=True, timeout=60)
                r.raise_for_status()
                
                total_size = int(r.headers.get('content-length', 0))
                zip_bytes = bytearray()
                
                # Calculate width for progress bar
                desc_width = min(40, self.terminal_width - 50)  # Leave room for progress info
                
                with tqdm(
                    total=total_size,
                    unit='B',
                    unit_scale=True,
                    desc=f'Downloading {local_path.name}',
                    file=self.output,
                    miniters=1,
                    bar_format='{desc:<' + str(desc_width) + '} |{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]',
                    ncols=self.terminal_width
                ) as pbar:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            zip_bytes.extend(chunk)
                            pbar.update(len(chunk))
                            
                # Extract specific file from zip
                with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
                    for name in z.namelist():
                        if name.endswith(local_path.name):
                            with z.open(name) as src, open(local_path, "wb") as dst:
                                dst.write(src.read())
                            break
            else:
                # Download regular file
                r = requests.get(url, timeout=30)
                r.raise_for_status()
                local_path.write_bytes(r.content)
                
            logger.info(f"Successfully downloaded {local_path}")
            
        except requests.RequestException as e:
            logger.error(f"Failed to download {url}: {e}")
            raise DownloadError(f"Failed to download {url}") from e
        except Exception as e:
            logger.error(f"Failed to save {local_path}: {e}")
            raise DownloadError(f"Failed to save {local_path}") from e

    def update_database(
        self,
        meta_date: datetime,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> None:
        """Update the database with new MTGJSON data.
        
        Args:
            meta_date: Meta date of the new data.
            progress_callback: Optional callback for progress updates.
            
        Raises:
            DatabaseUpdateError: If database update fails.
        """
        try:
            logger.info("Updating database with new MTGJSON data...")
            
            def wrapped_callback(progress: float, message: str):
                if progress_callback:
                    progress_callback(progress, message)
                # Calculate width for progress message
                desc_width = min(40, self.terminal_width - 20)  # Leave room for percentage
                message = message[:desc_width].ljust(desc_width)
                self.output.write(f"\r{message} [{progress:.1%}]")
                self.output.flush()
            
            # Show initial status
            self.output.write("\nInitializing database update...\n")
            
            bootstrap(
                json_path=str(self.allprintings_path),
                inventory_path=str(self.inventory_path),
                db_url=f"sqlite:///{self.db_path}",
                use_tqdm=True,
                progress_callback=wrapped_callback
            )
            
            # Show completion status
            self.output.write("\nFinalizing database update...\n")
            self.output.write("Database update complete\n")
            logger.info("Database update complete")
            
        except DatabaseError as e:
            logger.error(f"Failed to update database: {e}")
            raise DatabaseUpdateError("Failed to update database") from e

    def sync(
        self,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> None:
        """Synchronize MTGJSON data.
        
        Args:
            progress_callback: Optional callback for progress updates.
            
        Raises:
            MTGJSONError: If synchronization fails.
        """
        try:
            with buffered_output(self.output) as output:
                output.write("Checking MTGJSON data sync status...\n")
                
                # Get local meta data
                local_version = local_date = ""
                if self.meta_path.exists():
                    try:
                        local_meta = json.loads(self.meta_path.read_text(encoding='utf-8'))
                        local_version = local_meta.get("meta", {}).get("version", "")
                        local_date = local_meta.get("meta", {}).get("date", "")
                        output.write(f"Local meta: version={local_version}, date={local_date}\n")
                    except Exception as e:
                        logger.error(f"Failed to read local meta: {e}")
                        local_meta = {}

                # Get database meta date
                db_meta_date = self.get_db_last_import_meta_date()
                db_meta_date_str = db_meta_date.strftime("%Y-%m-%d") if db_meta_date else None

                # Get remote meta data
                try:
                    remote_meta = requests.get(self.meta_url, timeout=10).json()
                    remote_version = remote_meta.get("meta", {}).get("version", "")
                    remote_date = remote_meta.get("meta", {}).get("date", "")
                    output.write(f"Remote meta: version={remote_version}, date={remote_date}\n")
                except Exception as e:
                    logger.error(f"Failed to fetch remote meta: {e}")
                    raise DownloadError("Failed to fetch remote meta") from e

                # Determine if updates are needed
                need_main_json_update = (
                    self.force_update
                    or not self.allprintings_path.exists()
                    or not self.meta_path.exists()
                    or remote_version != local_version
                    or remote_date != local_date
                )
                
                need_db_update = (
                    self.force_update
                    or db_meta_date_str != str(remote_date)
                    or not self.db_path.exists()
                )

                # Download and update files if needed
                if need_main_json_update:
                    output.write("Update required. Downloading and updating data...\n")
                    
                    # Backup existing files
                    if self.allprintings_path.exists():
                        self.backup_old_json(
                            self.allprintings_path,
                            meta_date=datetime.strptime(local_date, "%Y-%m-%d") if local_date else None
                        )

                    # Download new files
                    self.download_file(self.allprintings_url, self.allprintings_path, is_zip=True)
                    self.meta_path.write_text(json.dumps(remote_meta, indent=2), encoding='utf-8')
                    
                    # Always update keywords and card types when main JSON is updated
                    self.download_file(self.keywords_url, self.keywords_path)
                    self.download_file(self.cardtypes_url, self.cardtypes_path)
                    
                    need_db_update = True
                else:
                    output.write("MTGJSON data is up to date\n")
                    
                    # Download keywords and card types only if missing
                    if not self.keywords_path.exists():
                        self.download_file(self.keywords_url, self.keywords_path)
                    if not self.cardtypes_path.exists():
                        self.download_file(self.cardtypes_url, self.cardtypes_path)

                # Update database if needed
                if need_db_update:
                    output.write("Database needs update. Rebuilding from local AllPrintings.json...\n")
                    self.update_database(
                        meta_date=datetime.strptime(remote_date, "%Y-%m-%d"),
                        progress_callback=progress_callback
                    )
                else:
                    output.write("Database is up to date\n")

        except Exception as e:
            logger.error(f"Synchronization failed: {e}")
            raise MTGJSONError("Synchronization failed") from e

def main():
    parser = argparse.ArgumentParser(description="Sync MTGJSON data and update the local database.")
    parser.add_argument("--force", action="store_true", help="Force update even if data is up to date.")
    parser.add_argument("--data-dir", type=str, default="data", help="Directory for MTGJSON data files.")
    parser.add_argument("--db-path", type=str, default="cards.db", help="Path to the SQLite database.")
    parser.add_argument("--quiet", action="store_true", help="Suppress progress output.")
    parser.add_argument("--no-download", action="store_true", help="Skip downloading and only update the database using the existing file.")
    args = parser.parse_args()

    sync = MTGJSONSync(
        data_dir=args.data_dir,
        db_path=args.db_path,
        force_update=args.force,
        output=open(os.devnull, 'w') if args.quiet else sys.stdout
    )

    if args.no_download:
        if not sync.allprintings_path.exists():
            print(f"[ERROR] AllPrintings.json not found at {sync.allprintings_path}. Cannot update database without downloading.")
            exit(1)
        print("[INFO] --no-download flag set. Skipping download. Updating database using existing AllPrintings.json...")
        # If --force, always update; else, only update if needed
        if args.force:
            sync.update_database(meta_date=None)
            print("[INFO] Database update complete (forced).")
        else:
            # Check if database is up to date with the file
            db_meta_date = sync.get_db_last_import_meta_date()
            # You may want to compare file mtime or meta date here
            # For now, always update if unsure
            sync.update_database(meta_date=None)
            print("[INFO] Database update complete.")
        return

    # Default behavior: download/check for updates, then update database
    sync.sync()

if __name__ == "__main__":
    main() 