
import gradio as gr
from ui.data_tab import data_tab
from ui.inventory_tab import inventory_tab
from ui.deck_tab import deck_tab

def build_app():
    session_state = {}
    with gr.Blocks() as demo:
        gr.Markdown("# MTG Deck Builder - Multi-File Gradio App")

        with gr.Tabs():
            data_tab(session_state)
            inventory_tab(session_state)
            deck_tab(session_state)

    return demo

if __name__ == "__main__":
    app = build_app()
    app.launch(server_name="127.0.0.1", server_port=7666)
