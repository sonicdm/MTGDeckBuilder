"""utils package for utility/helper modules.

This package intentionally avoids importing heavy optional dependencies at import time
so that modules like the FastAPI backend can import lightweight utilities (e.g.,
logging_config) without requiring optional libs such as matplotlib.

Plot utilities are imported lazily/optionally. If matplotlib is not installed, the
plot functions will not be available in this namespace, and callers should handle
their absence.
"""

# Optional plotting utilities (matplotlib). If unavailable, skip exporting them
try:
    from mtg_deckbuilder_ui.utils.plot_utils import (
        plot_mana_curve,
        plot_power_toughness_curve,
        plot_color_balance,
        plot_type_counts,
        plot_rarity_breakdown,
    )
    _PLOT_FUNCS_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    _PLOT_FUNCS_AVAILABLE = False
    plot_mana_curve = None  # type: ignore
    plot_power_toughness_curve = None  # type: ignore
    plot_color_balance = None  # type: ignore
    plot_type_counts = None  # type: ignore
    plot_rarity_breakdown = None  # type: ignore
from mtg_deckbuilder_ui.utils.mtgjson_loaders import (
    load_keywords_json,
    load_cardtypes_json,
    download_keywords_json,
    download_cardtypes_json,
)
from mtg_deckbuilder_ui.utils.ui_helpers import (
    get_full_path,
    ensure_extension,
    list_files_by_extension,
    refresh_dropdown,
    get_config_path,
    list_config_files,
    gradio_log_and_return,
    validate_tab_names,
    hide_component,
    show_component,
)
from mtg_deckbuilder_ui.utils.logging_config import setup_logging
from mtg_deckbuilder_ui.utils.file_utils import import_inventory_file

__all__ = [
    # plotting (optional)
    "plot_mana_curve",
    "plot_power_toughness_curve",
    "plot_color_balance",
    "plot_type_counts",
    "plot_rarity_breakdown",
    # loaders
    "load_keywords_json",
    "load_cardtypes_json",
    "download_keywords_json",
    "download_cardtypes_json",
    # helpers
    "get_full_path",
    "ensure_extension",
    "list_files_by_extension",
    "refresh_dropdown",
    "get_config_path",
    "list_config_files",
    "gradio_log_and_return",
    "validate_tab_names",
    "hide_component",
    "show_component",
    # logging
    "setup_logging",
    # file utils
    "import_inventory_file",
]
