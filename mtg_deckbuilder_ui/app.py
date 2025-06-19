import threading
import argparse
import gradio as gr
import uvicorn
from pathlib import Path
from mtg_deckbuilder_ui.utils.file_utils import (
    list_files_by_extension,
    import_inventory_file
)

from mtg_deckbuilder_ui.app_config import app_config
from mtg_deckbuilder_ui.utils.logging_config import setup_logging
from mtg_deckbuilder_ui.startup import startup_init
from mtg_deckbuilder_ui.tabs import (
    create_deckbuilder_tab,
    create_config_manager_tab,
    create_deck_viewer_tab,
    create_inventory_manager_tab,
    create_library_viewer_tab,
    # create_collection_viewer_tab,
    # create_settings_tab,
)
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, Request
import sys
import logging
from mtg_deckbuilder_ui.utils.formatting import format_sync_result

# Silence uvicorn, fastapi, gradio, matplotlib, and other noisy libraries
# logging.getLogger("uvicorn").setLevel(logging.WARNING)
# logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
# logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
# logging.getLogger("fastapi").setLevel(logging.WARNING)
# logging.getLogger("gradio").setLevel(logging.WARNING)
logging.getLogger("matplotlib").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)

# --- Unicode fix for Windows console ---

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


# Initialize logging first
logger = setup_logging(app_config)
logger.info("MTG Deckbuilder UI starting up...")

parser = argparse.ArgumentParser(description="MTG Deckbuilder UI")
parser.add_argument(
    "--ignore-json-updates",
    action="store_true",
    help="Ignore updates to the JSON data files",
)
parser.add_argument(
    "--debug",
    action="store_true",
    help="Enable debug logging")
args, _ = parser.parse_known_args()
ignore_json_updates = args.ignore_json_updates

# Set debug log level if requested
if args.debug:
    logger.info("Debug logging enabled")
else:
    logging.getLogger().setLevel(logging.WARNING)


def sync_progress_callback(progress: float, message: str) -> None:
    """Callback for sync progress updates."""
    logger.debug(f"Sync progress: {progress:.1%} - {message}")


logger.info("Starting startup initialization...")
sync_result = startup_init(ignore_json_updates=ignore_json_updates)
sync_status = format_sync_result(
    sync_result) if sync_result else "No sync performed"

# --- Bootstrap DB with current inventory file on startup ---
if not app_config.get_path("inventory_dir"):
    logger.error(
        "No inventory_files path set in config. "
        "Skipping inventory DB bootstrap."
    )
    inventory_files = []
else:
    inventory_files = list_files_by_extension(app_config.get_path("inventory_dir"), [".txt"])

last_inventory = app_config.get_last_loaded_inventory()
selected_inventory = None
if last_inventory and last_inventory in inventory_files:
    selected_inventory = last_inventory
    logger.info(
        f"Bootstrapping DB with last loaded inventory: {selected_inventory}")
elif inventory_files:
    selected_inventory = inventory_files[0]
    logger.info(
        "Bootstrapping DB with first available inventory: {}".format(
            selected_inventory
        )
    )
else:
    logger.warning("No inventory files found to bootstrap DB.")

# if selected_inventory and app_config.get_path("inventory_dir"):
#     inventory_path = str(Path(app_config.get_path("inventory_dir")) / selected_inventory)
#     logger.info(f"Importing inventory file at startup: {inventory_path}")
#     # Synchronously import inventory to ensure DB is ready before UI loads
#     thread = import_inventory_file(inventory_path)
#     # Wait for import to finish (optional, can be removed for async)
#     thread.join()
#     logger.info("Inventory import at startup complete.")

# FastAPI static file serving (optional, for downloading)
app = FastAPI()
app.mount(
    "/static",
    StaticFiles(directory=str(Path(__file__).parent / "static")),
    name="static",
)


@app.post("/reload")
def reload_app(request: Request):
    logger.info(
        "[RELOAD] /reload endpoint called. Exiting process to trigger reload.")

    def delayed_exit():
        import time

        time.sleep(0.5)
        import os

        os._exit(3)

    threading.Thread(target=delayed_exit, daemon=True).start()
    return JSONResponse({"status": "reloading"})


def load_css(css_path: str = None) -> str:
    if css_path is None:
        css_path = str(Path(__file__).parent / "static" / "styles.css")
    try:
        return "<style>" + \
            Path(css_path).read_text(encoding="utf-8") + "</style>"
    except Exception as e:
        logger.error(f"Failed to load {css_path}: {e}")
        return ""


def create_app():
    """Create and configure the Gradio application."""
    with gr.Blocks(theme=gr.themes.Default(), css=load_css()) as app:
        gr.Markdown("# MTG Deckbuilder")
        with gr.Tabs():
            with gr.TabItem("Deck Builder"):
                deckbuilder_tab = create_deckbuilder_tab()
                deckbuilder_tab.render()
            with gr.TabItem("Config Manager"):
                config_manager_tab = create_config_manager_tab()
                config_manager_tab.render()
            with gr.TabItem("Inventory Manager"):
                inventory_manager_tab = create_inventory_manager_tab()
                inventory_manager_tab.render()
            with gr.TabItem("Deck Viewer"):
                deck_viewer_tab = create_deck_viewer_tab()
                deck_viewer_tab.render()
            with gr.TabItem("Library Viewer"):
                library_viewer_tab = create_library_viewer_tab()
                library_viewer_tab.render()
            # with gr.TabItem("Settings"):
            #     settings_tab = create_settings_tab()
            #     settings_tab.render()
    return app



if __name__ == "__main__":
    # Create and launch the app
    app = create_app()
    app.launch(
        server_name=app_config.SERVER_HOST,
        server_port=app_config.SERVER_PORT,
        share=app_config.SHARE_APP
    )
