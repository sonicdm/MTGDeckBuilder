import threading
import argparse
import gradio as gr
import gradio.themes as themes
import uvicorn
from pathlib import Path
from typing import Optional

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
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")  # type: ignore

# Initialize logging first
logger = setup_logging(app_config)
logger.info("MTG Deckbuilder UI starting up...")

parser = argparse.ArgumentParser(description="MTG Deckbuilder UI")
parser.add_argument(
    "--ignore-json-updates",
    action="store_true",
    help="Ignore updates to the databasefiles",
)
parser.add_argument(
    "--force-update",
    action="store_true",
    help="Force update the database schema",
)
parser.add_argument(
    "--debug",
    action="store_true",
    help="Enable debug logging")
args, _ = parser.parse_known_args()
ignore_json_updates = args.ignore_json_updates
force_update = args.force_update
force_update = True
# Set debug log level if requested
if args.debug:
    logger.info("Debug logging enabled")
else:
    logging.getLogger().setLevel(logging.WARNING)


def sync_progress_callback(progress: float, message: str) -> None:
    """Callback for sync progress updates."""
    logger.debug(f"Sync progress: {progress:.1%} - {message}")


logger.info("Starting startup initialization...")
sync_result = startup_init(ignore_database_updates=ignore_json_updates, force_update=force_update)
if sync_result:
    sync_status = format_sync_result(sync_result)
else:
    sync_status = "No sync performed (skipped or not needed)"

# Note: Database initialization is now handled by the sync process
# which downloads the SQLite file and builds summary cards
logger.info("Startup initialization complete.")

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


def load_css(css_path: Optional[str] = None) -> str:
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
    with gr.Blocks(theme=themes.Default(), css=load_css()) as app:
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
        server_name="127.0.0.1",
        server_port=7860,
        share=False
    )
