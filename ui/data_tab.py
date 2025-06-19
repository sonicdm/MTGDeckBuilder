# ui/data_tab.py

import gradio as gr
import mtg_deckbuilder_ui.logic.data_logic as logic

# Updated CSS to make refresh buttons even smaller
SMALL_BUTTON_CSS = """
#small-refresh-btn, #small-refresh-btn-inv {
    width: 24px !important;
    min-width: 24px !important;
    height: 24px !important;
    min-height: 24px !important;
    padding: 0 !important;
    margin-left: 4px !important;  /* small gap from the dropdown */
    text-align: center;
    font-size: 14px !important;
    line-height: 1 !important;
}
"""

def data_tab(session_state):
    with gr.Tab("Data Loading"):
        # Provide custom CSS for small refresh buttons
        gr.Markdown("## Select or Upload Atomic Data & Inventory")

        with gr.Row():
            with gr.Column():
                gr.Markdown("### Atomic Data")

                # Local atomic JSON + refresh in a row
                with gr.Row():
                    local_atomic_files = ["None"] + logic.list_local_json_files()
                    local_atomic_choice = gr.Dropdown(
                        choices=local_atomic_files,
                        label="Local Atomic JSON",
                        value="None"
                    )
                    refresh_atomic_btn = gr.Button("🔃", elem_id="small-refresh-btn")

                def refresh_atomic():
                    new_files = ["None"] + logic.list_local_json_files()
                    return gr.update(choices=new_files)

                refresh_atomic_btn.click(
                    fn=refresh_atomic,
                    inputs=[],
                    outputs=[local_atomic_choice]
                )

                # Move file upload above the URL
                atomic_upload = gr.File(
                    label="Upload AtomicCards.json",
                    file_types=[".json"]
                )

                atomic_url = gr.Textbox(
                    label="Atomic URL (optional)",
                    placeholder="https://example.com/AtomicCards.json"
                )

            with gr.Column():
                gr.Markdown("### Inventory (Multi)")

                # local inventory + refresh in a row
                with gr.Row():
                    local_inv = logic.list_local_inventory_files()
                    inv_dropdown = gr.Dropdown(
                        choices=local_inv,
                        label="Local Inventories",
                        multiselect=True,
                        value=[]
                    )
                    refresh_inv_btn = gr.Button("🔃", elem_id="small-refresh-btn-inv")

                def refresh_inv():
                    new_invs = logic.list_local_inventory_files()
                    return gr.update(choices=new_invs)

                refresh_inv_btn.click(
                    fn=refresh_inv,
                    inputs=[],
                    outputs=[inv_dropdown]
                )

                inv_upload = gr.File(
                    label="Upload Inventory .txt",
                    file_types=[".txt"]
                )

        load_btn = gr.Button("Load Data")
        load_output = gr.Textbox(label="Result", lines=5)

        def on_load(local_atomic, at_up, at_url, local_invs, inv_up):
            return logic.process_data(
                local_atomic, at_up, at_url,
                local_invs, inv_up,
                session_state=session_state
            )

        load_btn.click(
            fn=on_load,
            inputs=[local_atomic_choice, atomic_upload, atomic_url, inv_dropdown, inv_upload],
            outputs=[load_output]
        )

def build_data_tab_blocks(session_state):
    """
    If you want to return a Blocks object with custom CSS,
    you can do so here, or just embed the CSS in the main app.
    """
    with gr.Blocks(css=SMALL_BUTTON_CSS) as data_tab_blocks:
        data_tab(session_state)
    return data_tab_blocks
