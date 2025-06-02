"""
ui_helpers.py

Provides common UI utility functions for the MTG Deckbuilder application.
These functions help standardize operations like:
- Listing files with specific extensions
- Refreshing dropdowns
- File loading/saving operations with proper path handling
- Common UI feedback patterns
"""
import os
import gradio as gr
import logging

# Set up logging
logger = logging.getLogger(__name__)

def list_files_by_extension(directory, extensions):
    """
    List all files in a directory with specified extensions.

    Args:
        directory (str): The directory to search
        extensions (list): List of file extensions to include (e.g. ['.txt', '.yaml'])

    Returns:
        list: List of filenames that match the extensions
    """
    if not os.path.exists(directory):
        logger.warning(f"Directory does not exist: {directory}")
        return []

    try:
        return [
            f for f in os.listdir(directory)
            if any(f.lower().endswith(ext.lower()) for ext in extensions)
        ]
    except Exception as e:
        logger.error(f"Error listing files in {directory}: {e}")
        return []

def refresh_dropdown(dropdown_component, directory, extensions):
    """
    Refresh a dropdown component with files from the specified directory.

    Args:
        dropdown_component (gr.Dropdown): The Gradio dropdown component to update
        directory (str): Directory to scan for files
        extensions (list): List of file extensions to include

    Returns:
        gr.update: Gradio update object for the dropdown
    """
    files = list_files_by_extension(directory, extensions)
    return gr.update(choices=files)

def get_full_path(directory, filename):
    """
    Get the full path to a file, ensuring it exists in the specified directory.

    Args:
        directory (str): Base directory
        filename (str): Filename or relative path

    Returns:
        str: Full path to the file
    """
    if not filename:
        return None

    return os.path.join(directory, filename)

def ensure_extension(filename, default_extension):
    """
    Ensure a filename has the specified extension.

    Args:
        filename (str): The filename to check
        default_extension (str): Extension to add if missing (include the dot, e.g. '.txt')

    Returns:
        str: Filename with extension
    """
    if not filename.lower().endswith(default_extension.lower()):
        return f"{filename}{default_extension}"
    return filename

def _to_int(val, default=0):
    try:
        if val is None:
            return default
        # Gradio Number or numpy types
        if hasattr(val, 'item'):
            return int(val.item())
        return int(val)
    except Exception:
        return default

def _to_float(val, default=0.0):
    try:
        if val is None:
            return default
        if hasattr(val, 'item'):
            return float(val.item())
        return float(val)
    except Exception:
        return default

def _get_value(val, default=None):
    # If val is a Gradio component, get its .value, else return val
    if hasattr(val, 'value'):
        return val.value if val.value is not None else default
    return val if val is not None else default

def gradio_log_and_return(status_message, deck_obj=None):
    import gradio as gr
    # This helper can be reused for any Gradio callback that needs to log and return a status and deck object
    return gr.update(value=status_message), deck_obj

def validate_tab_names(tab_names):
    """
    Validate that all tab names are unique and non-empty strings.
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
    """
    Robust tab switching mechanism for Gradio apps.
    Usage:
        switcher = TabSwitcher(["Tab1", "Tab2", ...])
        switcher.render()
    """
    def __init__(self, tab_names, default=None):
        validate_tab_names(tab_names)
        self.tab_names = tab_names
        self.default = default if default in tab_names else tab_names[0]
        self._tab_state = gr.State(self.default)
        self._tab_buttons = []
        self._tab_callbacks = {}

    def on_tab(self, tab_name, callback):
        if tab_name not in self.tab_names:
            raise ValueError(f"Tab '{tab_name}' not in tab_names")
        self._tab_callbacks[tab_name] = callback

    def switch_to(self, tab_name):
        """
        Returns a function suitable for use as a Gradio event handler to switch to the given tab.
        Usage: my_button.click(tab_switcher.switch_to("Tab2"), outputs=..., inputs=[...])
        """
        if tab_name not in self.tab_names:
            raise ValueError(f"Tab '{tab_name}' not in tab_names")
        def _switch(*args, **kwargs):
            self._tab_state.value = tab_name
            if tab_name in self._tab_callbacks:
                return self._tab_callbacks[tab_name]()
            return None
        return _switch

    def render(self):
        with gr.Row():
            for name in self.tab_names:
                btn = gr.Button(name, elem_id=f"tab-btn-{name}", variant="secondary" if name != self.default else "primary")
                self._tab_buttons.append(btn)
        tab_content = gr.Column(visible=True)

        def switch_tab(tab_name, _):
            self._tab_state.value = tab_name
            # Only render the callback for the active tab
            if tab_name in self._tab_callbacks:
                return self._tab_callbacks[tab_name]()
            return None

        # Wire up each button to update the state and content
        for btn, name in zip(self._tab_buttons, self.tab_names):
            btn.click(lambda n=name: (n, self._tab_state), outputs=tab_content, inputs=[self._tab_state], fn=lambda n, _: switch_tab(n, _))
        return tab_content, self._tab_state
