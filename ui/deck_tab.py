\
import gradio as gr

def deck_tab(session_state):
    with gr.Tab("Deck"):
        gr.Markdown("## Build or Analyze a Deck (Placeholder)")

        color_identity = gr.Textbox(label="Color Identity (comma-separated, e.g. R,G)")
        max_mana = gr.Slider(label="Max Mana Value", minimum=0, maximum=10, step=1, value=5)
        deck_size = gr.Slider(label="Deck Size", minimum=1, maximum=100, step=1, value=60)
        build_button = gr.Button("Build Deck")

        deck_output = gr.Dataframe(
            headers=["Card Name", "Quantity", "Mana Value", "Type"],
            datatype=["str", "number", "number", "str"],
            label="Deck"
        )

        def build_deck_fn(ci_text, max_mv, dsize):
            if "collection" not in session_state:
                return [["No data", 0, 0, ""]]

            coll = session_state["collection"]

            if ci_text.strip():
                desired_colors = [c.strip() for c in ci_text.split(",")]
            else:
                desired_colors = []

            filtered_cards = []
            for card_name, card_obj in coll.cards.items():
                # color check
                if desired_colors:
                    cident = card_obj.colorIdentity or []
                    if not set(desired_colors).issubset(set(cident)):
                        continue
                # mana check
                mv = card_obj.manaValue if card_obj.manaValue else 0
                if mv > max_mv:
                    continue
                # ownership
                owned = coll.get_owned_quantity(card_name)
                if owned > 0:
                    filtered_cards.append((card_name, owned, mv, card_obj.type))

            filtered_cards.sort(key=lambda x: x[2])  # sort by mana value

            deck_list = []
            current_count = 0
            for (cname, cowned, cmv, ctype) in filtered_cards:
                needed = dsize - current_count
                if needed <= 0:
                    break
                copies = min(cowned, needed)
                if copies > 0:
                    deck_list.append([cname, copies, cmv, ctype])
                    current_count += copies

            return deck_list

        build_button.click(
            fn=build_deck_fn,
            inputs=[color_identity, max_mana, deck_size],
            outputs=[deck_output]
        )
