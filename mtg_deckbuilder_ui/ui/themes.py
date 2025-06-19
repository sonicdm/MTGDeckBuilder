# mtg_deckbuilder_ui/ui/themes.py

import gradio as gr
import os


def create_custom_theme(css_path="static/styles.css", enable_dark_mode=True):
    """
    Creates a Gradio theme with injected custom CSS and optional dark mode.
    """
    base_theme = gr.themes.Default(
        font=[fonts.GoogleFont("Source Sans Pro"), "sans-serif"]
    ).set(
        body_background_fill="white",
        body_text_color="#111",
        body_background_fill_dark="#0f0f11" if enable_dark_mode else "white",
        body_text_color_dark="#f4f4f5" if enable_dark_mode else "#111",
    )

    # Inject global CSS
    if os.path.exists(css_path):
        try:
            with open(css_path, "r") as f:
                base_theme.styles += "\n" + f.read()
            print(f"[theme] Injected custom CSS from {css_path}")
        except Exception as e:
            print(f"[theme] Failed to load CSS from {css_path}: {e}")
    else:
        print(f"[theme] CSS file not found at: {css_path}")

    return base_theme
