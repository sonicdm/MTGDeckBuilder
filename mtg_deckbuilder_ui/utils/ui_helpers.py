# mtg_deckbuilder_ui/utils/ui_helpers.py

"""
ui_helpers.py

Provides common UI utility functions for the MTG Deckbuilder application.
These functions help standardize operations like:
- UI component visibility and state management
- Tab switching and navigation
- Common UI feedback patterns
- Value type conversion and validation
"""
import os
import gradio as gr
import logging
from pathlib import Path
from typing import List, Any, Optional
from mtg_deckbuilder_ui.app_config import app_config
from mtg_deckbuilder_ui.utils.file_utils import (
    get_full_path,
    ensure_extension,
    list_files_by_extension,
    refresh_dropdown,
    get_config_path,
    list_config_files,
)

# Set up logging
logger = logging.getLogger(__name__)


def _to_int(val: Any, default: int = 0) -> int:
    """Convert a value to integer, handling various input types.

    Args:
        val: Value to convert
        default: Default value if conversion fails

    Returns:
        Integer value
    """
    try:
        if val is None:
            return default
        # Gradio Number or numpy types
        if hasattr(val, "item"):
            return int(val.item())
        return int(val)
    except Exception:
        return default


def _to_float(val: Any, default: float = 0.0) -> float:
    """Convert a value to float, handling various input types.

    Args:
        val: Value to convert
        default: Default value if conversion fails

    Returns:
        Float value
    """
    try:
        if val is None:
            return default
        if hasattr(val, "item"):
            return float(val.item())
        return float(val)
    except Exception:
        return default


def _get_value(val: Any, default: Any = None) -> Any:
    """Get value from a Gradio component or return the value directly.

    Args:
        val: Value or Gradio component
        default: Default value if None

    Returns:
        The value
    """
    if hasattr(val, "value"):
        return val.value if val.value is not None else default
    return val if val is not None else default


def gradio_log_and_return(status_message: str, deck_obj: Any = None) -> tuple:
    """Helper for Gradio callbacks that need to log and return a status and deck object.

    Args:
        status_message: Message to display
        deck_obj: Optional deck object to return

    Returns:
        Tuple of (status update, deck object)
    """
    return gr.update(value=status_message), deck_obj


def validate_tab_names(tab_names: List[str]) -> bool:
    """Validate that all tab names are unique and non-empty strings.

    Args:
        tab_names: List of tab names to validate

    Returns:
        True if valid

    Raises:
        ValueError: If tab names are invalid
    """
    if not isinstance(tab_names, (list, tuple)):
        raise ValueError("Tab names must be a list or tuple.")
    seen = set()
    for name in tab_names:
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"Invalid tab name: '{name}' (must be non-empty string)")
        if name in seen:
            raise ValueError(f"Duplicate tab name: '{name}'")
        seen.add(name)
    return True


class TabSwitcher:
    """Robust tab switching mechanism for Gradio apps.

    Usage:
        switcher = TabSwitcher(["Tab1", "Tab2", ...])
        switcher.render()
    """

    def __init__(self, tab_names: List[str], default: Optional[str] = None):
        """Initialize the tab switcher.

        Args:
            tab_names: List of tab names
            default: Default tab name (uses first tab if not specified)
        """
        validate_tab_names(tab_names)
        self.tab_names = tab_names
        self.default = default if default in tab_names else tab_names[0]
        self._tab_state = gr.State(self.default)
        self._tab_buttons = []
        self._tab_callbacks = {}

    def on_tab(self, tab_name: str, callback: callable) -> None:
        """Register a callback for a specific tab.

        Args:
            tab_name: Name of the tab
            callback: Function to call when tab is selected
        """
        if tab_name not in self.tab_names:
            raise ValueError(f"Tab '{tab_name}' not in tab_names")
        self._tab_callbacks[tab_name] = callback

    def switch_to(self, tab_name: str) -> callable:
        """Returns a function suitable for use as a Gradio event handler.

        Args:
            tab_name: Name of the tab to switch to

        Returns:
            Function that can be used as a Gradio event handler
        """
        if tab_name not in self.tab_names:
            raise ValueError(f"Tab '{tab_name}' not in tab_names")

        def _switch(*args, **kwargs):
            self._tab_state.value = tab_name
            if tab_name in self._tab_callbacks:
                return self._tab_callbacks[tab_name]()
            return None

        return _switch

    def render(self) -> tuple:
        """Render the tab switcher UI components.

        Returns:
            Tuple of (tab content column, tab state)
        """
        with gr.Row():
            for name in self.tab_names:
                btn = gr.Button(
                    name,
                    elem_id=f"tab-btn-{name}",
                    variant="secondary" if name != self.default else "primary",
                )
                self._tab_buttons.append(btn)
        tab_content = gr.Column(visible=True)

        def switch_tab(tab_name: str, _: Any) -> Any:
            self._tab_state.value = tab_name
            if tab_name in self._tab_callbacks:
                return self._tab_callbacks[tab_name]()
            return None

        # Wire up each button to update the state and content
        for btn, name in zip(self._tab_buttons, self.tab_names):
            btn.click(
                lambda n=name: (n, self._tab_state),
                outputs=tab_content,
                inputs=[self._tab_state],
                fn=lambda n, _: switch_tab(n, _),
            )
        return tab_content, self._tab_state


def hide_component() -> gr.update:
    """Return a gr.update to hide a component.

    Returns:
        Gradio update object to hide component
    """
    return gr.update(visible=False)


def show_component() -> gr.update:
    """Return a gr.update to show a component.

    Returns:
        Gradio update object to show component
    """
    return gr.update(visible=True)
