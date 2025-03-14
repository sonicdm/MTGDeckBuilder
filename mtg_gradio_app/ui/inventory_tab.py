\
import gradio as gr

def filter_inventory(session_state, name_query, only_owned):
    if "collection" not in session_state:
        return [["No data", 0, ""]]

    coll = session_state["collection"]
    rows = []
    for card_name, card_obj in coll.cards.items():
        owned = coll.get_owned_quantity(card_name)
        if only_owned and owned <= 0:
            continue
        if name_query and name_query.lower() not in card_name.lower():
            continue
        rows.append([card_name, owned, card_obj.type or ""])

    rows.sort(key=lambda x: x[0])
    return rows

def inventory_tab(session_state):
    with gr.Tab("Inventory"):
        gr.Markdown("## Filter Inventory")
        name_query = gr.Textbox(label="Name contains:")
        only_owned = gr.Checkbox(label="Only Owned", value=True)

        run_btn = gr.Button("Filter")
        output = gr.Dataframe(
            headers=["Card Name", "Owned", "Type"],
            datatype=["str", "number", "str"],
            label="Filtered Results"
        )

        def on_run(nq, ow):
            return filter_inventory(session_state, nq, ow)

        run_btn.click(fn=on_run, inputs=[name_query, only_owned], outputs=[output])
