import os
import requests
import json
import zipfile
import io
from datetime import datetime
from tqdm import tqdm
from mtg_deck_builder.db.models import ImportLog
from mtg_deck_builder.db.bootstrap import bootstrap
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def backup_old_json(json_path, meta_date=None):
    if os.path.exists(json_path):
        # Use meta_date in backup filename if provided, else fallback to timestamp
        if meta_date:
            safe_meta_date = str(meta_date).replace(":", "-").replace(" ", "_")
            backup_zip = json_path.replace(".json", f"_{safe_meta_date}.zip")
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_zip = json_path.replace(".json", f"_{timestamp}.zip")
        with zipfile.ZipFile(backup_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(json_path, arcname=os.path.basename(json_path))

def get_db_last_import_meta_date(db_path):
    if not os.path.exists(db_path):
        return None
    try:
        engine = create_engine(f"sqlite:///{db_path}")
        Session = sessionmaker(bind=engine)
        session = Session()
        latest = session.query(ImportLog).order_by(ImportLog.meta_date.desc()).first()
        session.close()
        if latest:
            return latest.meta_date
    except Exception as e:
        print(f"Could not query ImportLog: {e}")
    return None

def download_keywords_json(keywords_url, keywords_json):
    try:
        print(f"[mtgjson_sync] Downloading Keywords.json from {keywords_url} ...")
        r = requests.get(keywords_url, timeout=30)
        r.raise_for_status()
        with open(keywords_json, "wb") as f:
            f.write(r.content)
        print(f"[mtgjson_sync] Saved Keywords.json to {keywords_json}")
    except Exception as e:
        print(f"[mtgjson_sync] Failed to download Keywords.json: {e}")

def download_cardtypes_json(cardtypes_url, local_cardtypes_path):
    try:
        print(f"[mtgjson_sync] Downloading CardTypes.json from {cardtypes_url} ...")
        r = requests.get(cardtypes_url, timeout=30)
        r.raise_for_status()
        with open(local_cardtypes_path, "wb") as f:
            f.write(r.content)
        print(f"[mtgjson_sync] Saved CardTypes.json to {local_cardtypes_path}")
    except Exception as e:
        print(f"[mtgjson_sync] Failed to download CardTypes.json: {e}")

def update_database_with_json(json_path, db_path, meta_date, progress_callback=None):
    print("[mtgjson_sync] Updating database with AllPrintings.json using backend bootstrap...")
    bootstrap(json_path=json_path, db_url=f"sqlite:///{db_path}", use_tqdm=True)
    if progress_callback:
        progress_callback(1.0, "Import complete.")
    print("[mtgjson_sync] Import complete.")

def mtgjson_sync(
    meta_url,
    allprintings_url,
    local_meta_path,
    local_allprintings_path,
    db_path,
    keywords_json,
    keywords_url,
    local_cardtypes_path,
    cardtypes_url,
    progress_callback=None
):
    print("[mtgjson_sync] Checking MTGJSON data sync status...")
    print(f"[mtgjson_sync] Local AllPrintings path: {local_allprintings_path}")
    print(f"[mtgjson_sync] Local Meta path: {local_meta_path}")
    print(f"[mtgjson_sync] Database path: {db_path}")

    # Always check meta/version/date, regardless of db existence
    local_version = local_date = ""
    if os.path.exists(local_meta_path):
        try:
            with open(local_meta_path, "r", encoding="utf-8") as f:
                local_meta = json.load(f)
            local_version = local_meta.get("meta", {}).get("version", "")
            local_date = local_meta.get("meta", {}).get("date", "")
            print(f"[mtgjson_sync] Local meta: version={local_version}, date={local_date}")
        except Exception:
            print("[mtgjson_sync] Failed to read local meta.")

    # Check DB ImportLog meta_date (convert to string for comparison)
    db_meta_date = get_db_last_import_meta_date(db_path)
    db_meta_date_str = db_meta_date.strftime("%Y-%m-%d") if db_meta_date else None

    # Download remote meta
    try:
        print(f"[mtgjson_sync] Fetching remote meta from {meta_url} ...")
        remote_meta = requests.get(meta_url, timeout=10).json()
        remote_version = remote_meta.get("meta", {}).get("version", "")
        remote_date = remote_meta.get("meta", {}).get("date", "")
        print(f"[mtgjson_sync] Remote meta: version={remote_version}, date={remote_date}")
    except Exception as e:
        print(f"[mtgjson_sync] Could not fetch remote MTGJSON meta: {e}")
        return

    # Determine if AllPrintings/Meta need update
    need_main_json_update = (
        not os.path.exists(local_allprintings_path)
        or not os.path.exists(local_meta_path)
        or remote_version != local_version
        or remote_date != local_date
    )
    # Determine if DB needs update
    need_db_update = (
        db_meta_date_str != str(remote_date)
        or not os.path.exists(db_path)
    )

    # Download AllPrintings/Meta if needed
    if need_main_json_update:
        print("[mtgjson_sync] Update required. Downloading and updating data...")
        try:
            backup_old_json(local_allprintings_path, meta_date=local_date if local_date else None)
            # --- Progress bar for AllPrintings.json.zip ---
            r = requests.get(allprintings_url, stream=True, timeout=60)
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))
            zip_bytes = bytearray()
            with tqdm(total=total_size, unit='B', unit_scale=True, desc='Downloading AllPrintings.json.zip') as pbar:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        zip_bytes.extend(chunk)
                        pbar.update(len(chunk))
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
                for name in z.namelist():
                    if name.endswith("AllPrintings.json"):
                        with z.open(name) as src, open(local_allprintings_path, "wb") as dst:
                            dst.write(src.read())
                        break
            with open(local_meta_path, "w", encoding="utf-8") as f:
                json.dump(remote_meta, f, indent=2)
            print("[mtgjson_sync] Downloaded new AllPrintings.json and updated Meta.json.")
            # Always re-download Keywords and CardTypes if main JSON was updated
            download_keywords_json(keywords_url, keywords_json)
            download_cardtypes_json(cardtypes_url, local_cardtypes_path)
            need_db_update = True  # Always update DB if new main JSON
        except Exception as e:
            print(f"[mtgjson_sync] Failed to update MTGJSON data: {e}")
            return
    else:
        print("[mtgjson_sync] MTGJSON data is up to date.")
        # Download Keywords/CardTypes only if missing
        if not os.path.exists(keywords_json):
            download_keywords_json(keywords_url, keywords_json)
        if not os.path.exists(local_cardtypes_path):
            download_cardtypes_json(cardtypes_url, local_cardtypes_path)

    # Only update DB if needed
    if need_db_update:
        print("[mtgjson_sync] Database is missing or out of date. Rebuilding from local AllPrintings.json...")
        update_database_with_json(local_allprintings_path, db_path, remote_date, progress_callback=progress_callback)
        print("[mtgjson_sync] Database update complete.")
    else:
        print("[mtgjson_sync] Skipping download and DB update.")
    return
