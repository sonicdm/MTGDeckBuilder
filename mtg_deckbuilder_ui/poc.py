# poc.py

import gradio as gr
import yaml
from pathlib import Path
from typing import Optional, Dict, Any
from mtg_deck_builder.db.repository import CardRepository, InventoryRepository
from mtg_deck_builder.models.deck import Deck
from mtg_deck_builder.models.deck_analyzer import DeckAnalyzer
from mtg_deck_builder.models.deck_exporter import DeckExporter
from mtg_deck_builder.yaml_builder.yaml_deckbuilder import (
    build_deck_from_yaml,
    load_yaml_config,
)
from mtg_deck_builder.models.deck_config import DeckConfig
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from mtg_deckbuilder_ui.utils.plot_utils import (
    plot_power_toughness_curve,
    plot_mana_curve,
    plot_color_balance,
    plot_type_counts,
    plot_rarity_breakdown,
)
import os
import matplotlib.pyplot as plt
import pandas as pd
from mtg_deckbuilder_ui.utils.mtgjson_sync import mtgjson_sync
import threading
import traceback
from mtg_deckbuilder_ui.utils.formatting import format_sync_result
from mtg_deckbuilder_ui.app_config import app_config

print(app_config.config_file)

# Constants
DEFAULT_CONFIG = """deck:
  name: "My Deck"
  colors: ["R", "G"]
  color_match_mode: "subset"
  size: 60
  max_card_copies: 4
  allow_colorless: true
  legalities: ["standard"]
  owned_cards_only: true
  mana_curve:
    min: 1
    max: 5
    curve_shape: "bell"
    curve_slope: "down"

categories:
  creatures:
    target: 24
    preferred_keywords: ["haste", "menace", "first strike"]
    priority_text: ["when this attacks", "sacrifice a creature"]
    preferred_basic_type_priority: ["creature"]

  removal:
    target: 6
    priority_text: ["destroy target", "exile target"]
    preferred_basic_type_priority: ["instant", "sorcery"]

  card_draw:
    target: 3
    priority_text: ["draw a card", "loot"]
    preferred_basic_type_priority: ["instant", "sorcery"]

mana_base:
  land_count: 24
  special_lands:
    count: 6
    prefer: ["add {r}", "add {g}"]
    avoid: ["enters tapped unless"]

card_constraints:
  rarity_boost:
    common: 1
    uncommon: 2
    rare: 2
    mythic: 1
  exclude_keywords: ["defender", "lifelink", "hexproof"]

fallback_strategy:
  fill_with_any: true
  fill_priority: ["creatures", "removal", "buffs"]
  allow_less_than_target: false"""


def ensure_config_dir():
    """Ensure the deck configs directory exists."""
    os.makedirs(app_config.get_path("deck_configs_dir"), exist_ok=True)


def list_yaml_files():
    """List all YAML files in the config directory."""
    ensure_config_dir()
    return [
        f
        for f in os.listdir(app_config.get_path("deck_configs_dir"))
        if f.endswith((".yaml", ".yml"))
    ]


def save_yaml_config(yaml_file: str, content: str) -> str:
    """Save YAML configuration to a file."""
    try:
        ensure_config_dir()
        if not (
            yaml_file.lower().endswith(".yaml") or yaml_file.lower().endswith(".yml")
        ):
            yaml_file += ".yaml"

        file_path = Path(app_config.get_path("deck_configs_dir")) / yaml_file
        file_path.write_text(content, encoding="utf-8")
        return f"✅ Config saved to {yaml_file}"
    except Exception as e:
        return f"❌ Error: {str(e)}"


def load_yaml_config_file(filename: str) -> str:
    """Load YAML configuration from a file."""
    try:
        file_path = Path(app_config.get_path("deck_configs_dir")) / filename
        return file_path.read_text(encoding="utf-8")
    except Exception as e:
        return f"❌ Error loading config: {str(e)}"


def build_deck_from_yaml_config(yaml_content: str) -> tuple[Optional[Deck], str]:
    """Build a deck from YAML configuration."""
    try:
        # Parse YAML content
        yaml_data = yaml.safe_load(yaml_content)
        if not isinstance(yaml_data, dict):
            print("YAML root is not a dictionary.")
            return None, "❌ Invalid YAML: root must be a dictionary"

        # Database setup
        engine = create_engine("sqlite:///cards.db")
        Session = sessionmaker(bind=engine)
        session = Session()

        # Create repositories
        card_repo = CardRepository(session)
        inventory_repo = InventoryRepository(session)

        # Build deck
        deck = build_deck_from_yaml(
            yaml_data,  # Pass the parsed YAML data directly
            card_repo=card_repo,
            inventory_repo=inventory_repo,
        )

        if deck is None:
            print("Deck build failed: No deck object returned.")
            return None, "❌ Failed to build deck"

        # Check for warnings/unmet conditions in the build context if available
        build_context = getattr(deck, "build_context", None)
        warnings = []
        unmet = []
        if build_context:
            warnings = getattr(build_context, "warnings", [])
            unmet = getattr(build_context, "unmet_conditions", [])
        # Also check for known deck attributes (if your build pipeline attaches them)
        if hasattr(deck, "warnings"):
            warnings += getattr(deck, "warnings", [])
        if hasattr(deck, "unmet_conditions"):
            unmet += getattr(deck, "unmet_conditions", [])
        if warnings or unmet:
            print("Deck build warnings:", warnings)
            print("Deck build unmet conditions:", unmet)
            msg = "⚠️ Deck built with warnings: "
            if warnings:
                msg += f"Warnings: {warnings}. "
            if unmet:
                msg += f"Unmet conditions: {unmet}."
            return deck, msg
        return deck, "✅ Deck built successfully"
    except yaml.YAMLError as e:
        print("YAML Error:", e)
        traceback.print_exc()
        return None, f"❌ Invalid YAML: {str(e)}"
    except Exception as e:
        print("Deck build error:", e)
        traceback.print_exc()
        return None, f"❌ Error building deck: {str(e)}"


def error_plot(message="Error"):
    fig, ax = plt.subplots()
    ax.text(0.5, 0.5, message, fontsize=16, ha="center", va="center")
    ax.axis("off")
    return fig


def main():
    """Create and launch the Gradio interface."""
    with gr.Blocks(title="MTG Deck Builder") as demo:
        gr.Markdown("# MTG Deck Builder")

        with gr.Tabs():
            with gr.Tab("Deck Builder"):
                with gr.Row():
                    with gr.Column(scale=1):
                        # Sync MTGJSON controls
                        sync_status = gr.Textbox(
                            label="MTGJSON Sync Status", interactive=False
                        )
                        sync_btn = gr.Button("Sync MTGJSON Data", variant="secondary")
                        sync_progress = gr.Progress(track_tqdm=True)

                        # Config selection
                        config_dropdown = gr.Dropdown(
                            choices=list_yaml_files(),
                            label="Select Configuration",
                            interactive=True,
                        )
                        with gr.Row():
                            load_config_btn = gr.Button("Load Config")
                            save_config_btn = gr.Button("Save Config")
                        config_status = gr.Textbox(label="Status", interactive=False)

                        # Build controls
                        build_btn = gr.Button("Build Deck", variant="primary")
                        build_status = gr.Textbox(
                            label="Build Status", interactive=False
                        )

                        # Deck stats
                        deck_stats = gr.JSON(label="Deck Statistics")

                    with gr.Column(scale=2):
                        # YAML editor
                        yaml_editor = gr.Code(
                            value=DEFAULT_CONFIG,
                            language="yaml",
                            label="Deck Configuration",
                            interactive=True,
                        )

                        # Deck list
                        deck_list = gr.Dataframe(
                            headers=[
                                "Name",
                                "Type",
                                "Colors",
                                "Mana Cost",
                                "Rarity",
                                "Quantity",
                            ],
                            label="Deck List",
                        )

                        # Power/Toughness distribution
                        pt_plot = gr.Plot(label="Power/Toughness Distribution")

            with gr.Tab("Deck Analysis"):
                analysis_md = gr.Markdown()
                mana_curve_plot = gr.Plot(label="Mana Curve")
                color_balance_plot = gr.Plot(label="Color Balance")
                type_counts_plot = gr.Plot(label="Type Counts")
                rarity_plot = gr.Plot(label="Rarity Breakdown")
                pt_plot_analysis = gr.Plot(label="Power/Toughness Distribution")

        # Event handlers
        def on_load_config(filename: str) -> tuple[str, str, gr.Dropdown]:
            # Ensure filename is a string
            if isinstance(filename, list):
                filename = filename[0] if filename else ""

            choices = list_yaml_files()
            if not filename or filename not in choices:
                return (
                    DEFAULT_CONFIG,
                    "❌ No configuration selected",
                    gr.update(choices=choices, value=None),
                )

            content = load_yaml_config_file(filename)
            if content.startswith("❌"):
                return DEFAULT_CONFIG, content, gr.update(choices=choices, value=None)

            return (
                content,
                f"✅ {filename} loaded",
                gr.update(choices=choices, value=filename),
            )

        def on_save_config(filename: str, content: str) -> tuple[str, gr.Dropdown]:
            if not filename:
                return "❌ Filename is required.", gr.update(choices=list_yaml_files())

            status = save_yaml_config(filename, content)

            # Refresh choices and set value to the saved file
            choices = list_yaml_files()
            return status, gr.update(
                choices=choices, value=filename if "✅" in status else None
            )

        def on_build_deck(yaml_content: str):
            try:
                deck, status = build_deck_from_yaml_config(yaml_content)
                if deck is None:
                    return (
                        pd.DataFrame([["Deck build failed"]], columns=["Error"]),
                        error_plot("Deck build failed"),
                        status,
                        {},
                        status,
                        error_plot("Deck build failed"),
                        error_plot("Deck build failed"),
                        error_plot("Deck build failed"),
                        error_plot("Deck build failed"),
                        error_plot("Deck build failed"),
                    )

                analyzer = DeckAnalyzer(deck)
                exporter = DeckExporter(deck)
                stats = analyzer.summary_dict()

                # Markdown summary
                md = f"""
### Deck: {stats['name']}
- **Total Cards:** {stats['total_cards']}
- **Lands:** {stats['land_count']}
- **Spells:** {stats['spell_count']}
- **Colors:** {', '.join(stats['color_identity'])}
- **Average Mana Value:** {stats['avg_mana_value']}
- **Synergy Score:** {stats['synergy']}
- **Most Expensive Cards:** {', '.join(stats['expensive_cards'])}
- **Frequent Keywords:** {', '.join(stats['frequent_keywords']) if stats['frequent_keywords'] else 'None'}
"""
                # Plots
                mana_curve_fig = plot_mana_curve(stats["mana_curve"])
                color_balance_fig = plot_color_balance(stats["color_balance"])
                type_counts_fig = plot_type_counts(stats["type_counts"])
                rarity_fig = plot_rarity_breakdown(stats["rarity_breakdown"])
                pt_fig = plot_power_toughness_curve(analyzer.power_toughness_curve())

                # Deck list
                deck_df = exporter.to_dataframe()

                # Ensure the DataFrame has the columns expected by the Gradio component
                expected_columns = [
                    "Name",
                    "Type",
                    "Colors",
                    "Mana Cost",
                    "Rarity",
                    "Quantity",
                ]
                # The exporter's dataframe has different column names, so we need to rename/select
                deck_df = deck_df.rename(columns={"Card Type": "Type"})
                deck_df = deck_df[expected_columns]

                print("Types returned by plot functions:")
                print("mana_curve_fig:", type(mana_curve_fig))
                print("color_balance_fig:", type(color_balance_fig))
                print("type_counts_fig:", type(type_counts_fig))
                print("rarity_fig:", type(rarity_fig))
                print("pt_fig:", type(pt_fig))

                print("stats['mana_curve']:", stats.get("mana_curve"))

                return (
                    deck_df,
                    pt_fig,
                    status,
                    stats,
                    md,
                    mana_curve_fig,
                    color_balance_fig,
                    type_counts_fig,
                    rarity_fig,
                    pt_fig,
                )
            except Exception as e:
                error_msg = f"❌ Error building deck: {e}\n{traceback.format_exc()}"
                return (
                    pd.DataFrame([[error_msg]], columns=["Error"]),
                    error_plot("Error"),
                    error_msg,
                    {},
                    error_msg,
                    error_plot("Error"),
                    error_plot("Error"),
                    error_plot("Error"),
                    error_plot("Error"),
                    error_plot("Error"),
                )

        def on_sync_mtgjson(progress=gr.Progress(track_tqdm=True)):
            def progress_callback(pct, msg):
                progress(pct, desc=msg)

            try:
                result = mtgjson_sync(progress_callback=progress_callback)
                # Use format_sync_result to show all errors and status
                status = format_sync_result(result)
            except Exception as e:
                status = f"❌ Sync failed: {e}\n{traceback.format_exc()}"
            return status

        # Connect event handlers
        load_config_btn.click(
            on_load_config,
            inputs=[config_dropdown],
            outputs=[yaml_editor, config_status, config_dropdown],
        )

        save_config_btn.click(
            on_save_config,
            inputs=[config_dropdown, yaml_editor],
            outputs=[config_status, config_dropdown],
        )

        build_btn.click(
            on_build_deck,
            inputs=[yaml_editor],
            outputs=[
                deck_list,
                pt_plot,
                build_status,
                deck_stats,
                analysis_md,
                mana_curve_plot,
                color_balance_plot,
                type_counts_plot,
                rarity_plot,
                pt_plot_analysis,
            ],
        )

        sync_btn.click(
            on_sync_mtgjson, inputs=[], outputs=[sync_status], api_name="sync_mtgjson"
        )

        # This is redundant if we update on every load/save, but good for completeness
        demo.load(list_yaml_files, None, config_dropdown)

    demo.launch()


if __name__ == "__main__":
    main()
