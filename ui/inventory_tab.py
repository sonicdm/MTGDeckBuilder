# ui/inventory_tab.py

import gradio as gr
from logic.inventory_logic import build_inventory_list, add_card_to_deck

def inventory_tab(session_state):
    with gr.Tab("Inventory"):
        gr.Markdown("## Inventory Browser")

        only_owned_checkbox = gr.Checkbox(value=False, label="Show Only Owned")
        inventory_html = gr.HTML()
        deck_debug = gr.HTML()

        # We'll show the total non-land count in a separate HTML label
        non_land_label = gr.HTML()

        def refresh_inventory(only_owned: bool):
            """
            Build the HTML listing + the non-land count label.
            """
            if "collection" not in session_state:
                return "<p>No collection loaded.</p>", "<p>Non-land cards: 0</p>"

            coll = session_state["collection"]
            rows, non_land_count = build_inventory_list(coll, only_owned)

            # We'll start with a small summary about non-land count
            # Then build the row list
            html_content = []
            for row in rows:
                card_name = row["card_name"]
                owned_str = row["owned"]
                is_land = row["is_land"]
                # Convert \n to &#10; for the 'title' attribute
                safe_title = row["title_text"].replace("\n", "&#10;").replace('"', '&quot;')

                # We'll display them in a <div> with a tooltip in the title
                # and do a placeholder for the +, - button
                # (For fully functional +/-, you'd need custom JS or a separate approach.)
                line_html = f"""
                <div style="margin-bottom: 6px;">
                  <span style="cursor: help;" title="{safe_title}">
                    {card_name} (Owned: {owned_str})
                  </span>
                </div>
                """
                html_content.append(line_html)

            final_html = "<div>" + "".join(html_content) + "</div>"
            # Return the final HTML plus a label for the non-land count
            return final_html, f"<p>Non-land cards: {non_land_count}</p>"

        filter_button = gr.Button("Refresh Inventory")

        def on_filter(only_owned: bool):
            html_list, non_land_str = refresh_inventory(only_owned)
            return html_list, non_land_str

        filter_button.click(
            fn=on_filter,
            inputs=[only_owned_checkbox],
            outputs=[inventory_html, non_land_label]
        )

        # We'll define a "deck" approach similarly if you want
        # For now, we just show how to display the non-land count

        # Initialize
        init_button = gr.Button("Init (One-time)")

        init_button.click(
            fn=on_filter,
            inputs=[only_owned_checkbox],
            outputs=[inventory_html, non_land_label]
        )

        # The rest of your deck logic, etc. can go here
