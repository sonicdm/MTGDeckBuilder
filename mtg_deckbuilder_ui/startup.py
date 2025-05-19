import os
from utils.mtgjson_sync import mtgjson_sync
from app_config import CONFIG_PRESETS_DIR, MTGJSON_DIR, USER_UPLOADS_DIR, LOGIC_DIR, UI_DIR, UTILS_DIR, LOCAL_ALLPRINTINGS_PATH

def ensure_folders():
    print("[startup] Ensuring required folders exist...")
    os.makedirs(CONFIG_PRESETS_DIR, exist_ok=True)
    os.makedirs(MTGJSON_DIR, exist_ok=True)
    os.makedirs(USER_UPLOADS_DIR, exist_ok=True)
    os.makedirs(LOGIC_DIR, exist_ok=True)
    os.makedirs(UI_DIR, exist_ok=True)
    os.makedirs(UTILS_DIR, exist_ok=True)
    print("[startup] Folder check complete.")

def get_db_path():
    # Database at module root
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "profile_cards.db"))

def initialize_database():
    from mtg_deck_builder.db.bootstrap import bootstrap

    db_path = get_db_path()
    json_path = LOCAL_ALLPRINTINGS_PATH

    # Ensure AllPrintings.json exists before bootstrapping
    if not os.path.exists(json_path):
        print("[startup] AllPrintings.json not found, running mtgjson_sync()...")
        mtgjson_sync()

    if not os.path.exists(db_path):
        print("[startup] Database not found, bootstrapping database...")
        inventory_files = os.listdir(USER_UPLOADS_DIR)
        inventory_path = os.path.join(USER_UPLOADS_DIR, inventory_files[0]) if inventory_files else None
        bootstrap(
            json_path=json_path,
            inventory_path=inventory_path,
            db_url=f"sqlite:///{db_path}",
            use_tqdm=False
        )
        print("[startup] Database bootstrapped.")
    else:
        print("[startup] Database already exists.")

def startup_init(ignore_json_updates=False):
    print("[startup] Running startup_init...")
    ensure_folders()
    if not ignore_json_updates:
        print("[startup] Running mtgjson_sync()...")
        mtgjson_sync()
    else:
        print("[startup] Skipping mtgjson_sync() due to --ignore-json-updates flag.")
    print("[startup] Running initialize_database()...")
    initialize_database()
    print("[startup] Startup complete.")

