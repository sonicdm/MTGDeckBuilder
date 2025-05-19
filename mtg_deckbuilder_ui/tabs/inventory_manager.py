import gradio as gr
from mtg_deckbuilder_ui.logic.inventory_manager_func import list_txt_files, parse_inventory_txt, save_inventory_txt, import_from_clipboard

def inventory_manager_tab(config_context, session, db_path, inventory_path):
    gr.Markdown("## Inventory: Load / Save")
    txt_files = gr.Dropdown(choices=list_txt_files(), label="Select Inventory TXT", interactive=True)
    with gr.Column():
        load_btn = gr.Button("📂 Load", variant="secondary", size="sm")
        save_btn = gr.Button("💾 Save", variant="primary", size="sm")
        refresh_btn = gr.Button(
            value="🔄 Refresh Inventories",
            elem_id="refresh_inventory_list",
            elem_classes="refresh-btn",
            size="sm",
            scale=1
        )
    filename_box = gr.Textbox(label="Save As Filename", value="card inventory.txt", interactive=True)
    inventory_table = gr.Dataframe(headers=["Quantity", "Card Name"], datatype=["number", "str"], row_count=(10, "dynamic"), col_count=(2, "fixed"), interactive=True, label="Inventory Table")
    clipboard = gr.Textbox(label="Paste Inventory Here (qty cardname per line)")
    import_btn = gr.Button("Import from Clipboard")

    def on_refresh_inventories():
        return gr.update(choices=list_txt_files())

    def autofill_filename(selected_file):
        return selected_file or "card inventory.txt"

    txt_files.change(autofill_filename, inputs=txt_files, outputs=filename_box)
    load_btn.click(lambda f: parse_inventory_txt(f), inputs=txt_files, outputs=inventory_table)
    save_btn.click(lambda fname, t: save_inventory_txt(fname, t), inputs=[filename_box, inventory_table], outputs=clipboard)
    import_btn.click(lambda text: import_from_clipboard(text), inputs=clipboard, outputs=inventory_table)
    refresh_btn.click(on_refresh_inventories, outputs=txt_files)
