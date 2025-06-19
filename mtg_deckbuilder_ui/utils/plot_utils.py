"""Utility functions for plotting deck data."""

import base64
import io
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.patches import Patch

# Set a Unicode/emoji-capable font if available
emoji_fonts = [
    "Noto Color Emoji",  # Linux
    "Segoe UI Emoji",  # Windows
    "Apple Color Emoji",  # Mac
]
available_fonts = set(f.name for f in fm.fontManager.ttflist)
for font in emoji_fonts:
    if font in available_fonts:
        plt.rcParams["font.family"] = font
        break
else:
    plt.rcParams["font.family"] = "DejaVu Sans"

MTG_MANA_COLORS = {
    "W": "#FFFFFF",
    "U": "#1E90FF",
    "B": "#000000",
    "R": "#FF3131",
    "G": "#22C55E",
    "C": "#BEBEBE",
}
COLOR_DISPLAY_MAP = {
    "W": "⚪ Plains (W)",
    "U": "🔵 Island (U)",
    "B": "⚫ Swamp (B)",
    "R": "🔴 Mountain (R)",
    "G": "🟢 Forest (G)",
    "C": "🚫 Colorless (C)",
}

MTG_MANA_NAMES = {
    "W": "⚪ Plains (W)",
    "U": "🔵 Island (U)",
    "B": "⚫ Swamp (B)",
    "R": "🔴 Mountain (R)",
    "G": "🟢 Forest (G)",
    "C": "🚫 Colorless (C)",
}


def get_text_color(bg_hex):
    bg_hex = bg_hex.lstrip("#")
    r, g, b = int(bg_hex[0:2], 16), int(bg_hex[2:4], 16), int(bg_hex[4:6], 16)
    luminance = 0.299 * r + 0.587 * g + 0.114 * b
    return "#FFFFFF" if luminance < 128 else "#000000"


def plot_mana_curve(mana_curve):
    """
    Generate a mana curve plot from a dictionary of mana values and counts.
    Returns a matplotlib Figure object.
    """
    import matplotlib.pyplot as plt

    if not mana_curve:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        ax.axis("off")
        return fig
    # Sort keys numerically
    sorted_items = sorted(mana_curve.items(), key=lambda x: int(x[0]))
    x = [str(k) for k, v in sorted_items]
    y = [v for k, v in sorted_items]
    fig, ax = plt.subplots()
    ax.bar(x, y, color="#4a90e2")
    ax.set_xlabel("Mana Value")
    ax.set_ylabel("Card Count")
    ax.set_title("Mana Curve")
    plt.tight_layout()
    return fig


def plot_power_toughness_curve(pt_counts):
    """
    Generate a power/toughness scatter plot from a deck object.
    Returns a matplotlib Figure object or None.
    """
    import matplotlib.pyplot as plt

    if not pt_counts:
        return None

    fig, ax = plt.subplots()
    x = [k[0] for k in pt_counts.keys()]
    y = [k[1] for k in pt_counts.keys()]
    sizes = [v * 40 for v in pt_counts.values()]

    ax.scatter(x, y, s=sizes, alpha=0.7, color="#e67e22")
    ax.set_xlabel("Power")
    ax.set_ylabel("Toughness")
    ax.set_title("Power/Toughness Curve")
    ax.grid(True, linestyle="--", alpha=0.5)

    plt.tight_layout()
    return fig


def plot_color_balance(color_balance):
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    if not color_balance:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        ax.axis("off")
        return fig

    # Prepare data
    keys = list(color_balance.keys())
    labels = [MTG_MANA_NAMES.get(k, k) for k in keys]
    sizes = list(color_balance.values())
    colors = [MTG_MANA_COLORS.get(k, "#888888") for k in keys]
    symbols = [COLOR_DISPLAY_MAP.get(k, k) for k in keys]

    fig, ax = plt.subplots(figsize=(6, 6), facecolor="white")
    ax.set_facecolor("white")  # Ensures axes bg is white
    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, autopct="%1.1f%%", startangle=90, colors=colors
    )
    for i, (wedge, text, autotext) in enumerate(zip(wedges, texts, autotexts)):
        color = colors[i]
        text.set_color(get_text_color(color))
        autotext.set_color(get_text_color(color))
    ax.set_title("Color Balance")

    # Custom legend: one entry per color
    legend_elements = [
        Patch(
            facecolor=colors[i],
            edgecolor="none",
            label=f"{symbols[i]} {labels[i]} ({keys[i]})",
        )
        for i in range(len(keys))
    ]
    # Remove duplicate labels
    seen = set()
    unique_legend_elements = []
    for elem in legend_elements:
        if elem.get_label() not in seen:
            unique_legend_elements.append(elem)
            seen.add(elem.get_label())

    ax.legend(
        handles=unique_legend_elements,
        title="Mana Symbols",
        loc="lower center",
        bbox_to_anchor=(0.5, -0.15),
        ncol=len(unique_legend_elements),
        frameon=False,
        fontsize=10,
        title_fontsize=12,
    )

    legend = ax.legend()
    legend.get_frame().set_facecolor("white")
    legend.get_frame().set_edgecolor("black")  # Optional: for a border

    plt.tight_layout()
    return fig


def plot_type_counts(type_counts):
    import matplotlib.pyplot as plt

    if not type_counts:
        return None
    fig, ax = plt.subplots()
    x = list(type_counts.keys())
    y = list(type_counts.values())
    ax.bar(x, y, color="#e67e22")
    ax.set_xlabel("Card Type")
    ax.set_ylabel("Count")
    ax.set_title("Type Counts")
    plt.tight_layout()
    return fig


def plot_rarity_breakdown(rarity_breakdown):
    import matplotlib.pyplot as plt

    if not rarity_breakdown:
        return None
    fig, ax = plt.subplots()
    x = list(rarity_breakdown.keys())
    y = list(rarity_breakdown.values())
    ax.bar(x, y, color="#9b59b6")
    ax.set_xlabel("Rarity")
    ax.set_ylabel("Count")
    ax.set_title("Rarity Breakdown")
    plt.tight_layout()
    return fig
