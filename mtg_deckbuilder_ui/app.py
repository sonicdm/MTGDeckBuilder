from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from mtg_deckbuilder_ui.ui.tabs import build_tabs
from mtg_deckbuilder_ui.startup import startup_init
from pathlib import Path
import uvicorn
import gradio as gr
import argparse

parser = argparse.ArgumentParser(description="MTG Deckbuilder UI")
parser.add_argument('--ignore-json-updates', action='store_true', help='Ignore updates to the JSON data files')
args, _ = parser.parse_known_args()
ignore_json_updates = args.ignore_json_updates

print("[MTGDeckbuilderUI] Starting up...")
startup_init(ignore_json_updates=ignore_json_updates)

# FastAPI static file serving (optional, for downloading)
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

def load_css(css_path: str = "static/styles.css") -> str:
    try:
        return "<style>" + Path(css_path).read_text() + "</style>"
    except Exception as e:
        print(f"[CSS] Failed to load {css_path}: {e}")
        return ""

# ✅ Inject CSS directly with css=Path(...) — THIS is the supported method
with gr.Blocks(css_paths=Path('./static/styles.css'), head=load_css()) as mtg_app:
    print(mtg_app.css)
    gr.Markdown("# MTG Deckbuilder UI")
    build_tabs()

# Mount Gradio onto FastAPI
app = gr.mount_gradio_app(app, mtg_app, path="/")

if __name__ == "__main__":
    print("[MTGDeckbuilderUI] Launching Gradio on port 42069...")
    uvicorn.run(app, host="0.0.0.0", port=42069)
