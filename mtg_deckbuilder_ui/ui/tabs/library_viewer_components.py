"""Library viewer components module."""

# Standard library imports
import logging

# Third-party imports
import gradio as gr

# Local application imports
from mtg_deckbuilder_ui.ui.ui_objects import UISection, UIElement, UIContainer
# from mtg_deckbuilder_ui.logic.library_viewer_callbacks import filter_library
from mtg_deck_builder.db import get_session
from mtg_deck_builder.db.repository import CardRepository

# Set up logger
logger = logging.getLogger(__name__)


def create_library_viewer_section() -> UISection:
    """Create the library viewer section."""
    with UISection("library_viewer", "Library Viewer") as section:
        owned_only = UIElement(
            "owned_only",
            lambda: gr.Checkbox(label="Show only owned cards", value=False),
        )
        library_output = UIElement(
            "library_output", lambda: gr.Textbox(label="Library", lines=10)
        )

        layout = UIContainer("group", children=[owned_only, library_output])
        section.set_layout(layout)
    return section


def create_library_viewer_tab() -> UISection:
    """Create the library viewer tab."""
    tab = UISection("library_viewer_tab", "Library Viewer")

    # Create main section
    main_section = create_library_viewer_section()
    tab.add_section(main_section)

    # Get components for wiring
    components = tab.get_component_map()

    # Wire up callbacks
    components["owned_only"].change(
        filter_library,
        inputs=[components["owned_only"]],
        outputs=[components["library_output"]],
    )

    # Initial load
    components["library_output"].value = filter_library(False)

    return tab


def load_library():
    """Load all cards from the library."""
    with get_session() as session:
        card_repo = CardRepository(session=session)
        return card_repo.get_all_cards()


def filter_library(owned_only: bool) -> str:
    """Filter library cards based on ownership.

    Args:
        owned_only: Whether to show only owned cards

    Returns:
        String containing filtered card names
    """
    cards = load_library()
    if owned_only:
        cards = [card for card in cards if getattr(card, "owned_qty", 0) > 0]
    return "\n".join([card.name for card in cards])
