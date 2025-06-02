"""Utility functions for plotting deck data."""

import base64
import io
import matplotlib.pyplot as plt

def plot_mana_curve(mana_curve):
    """
    Generate a mana curve plot from a dictionary of mana values and counts.
    Returns a data URL for the plot image.
    """
    if not mana_curve:
        return None
    fig, ax = plt.subplots()
    x = list(map(int, mana_curve.keys()))
    y = list(mana_curve.values())
    ax.bar(x, y, color='#4a90e2')
    ax.set_xlabel('Mana Value')
    ax.set_ylabel('Card Count')
    ax.set_title('Mana Curve')
    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format='png')
    plt.close(fig)
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode('utf-8')
    return f"data:image/png;base64,{img_str}"


def plot_power_toughness_curve(deck_obj):
    """
    Generate a power/toughness scatter plot from a deck object.
    Returns a data URL for the plot image.
    """
    if not deck_obj or not hasattr(deck_obj, 'cards'):
        return None
    pt_counts = {}
    for card in deck_obj.cards.values():
        if hasattr(card, 'matches_type') and card.matches_type("creature"):
            try:
                power = float(getattr(card, "power", 0) or 0)
                toughness = float(getattr(card, "toughness", 0) or 0)
                key = (power, toughness)
                pt_counts[key] = pt_counts.get(key, 0) + getattr(card, "owned_qty", 1)
            except Exception:
                continue
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
    ax.grid(True, linestyle='--', alpha=0.5)
    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format='png')
    plt.close(fig)
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode('utf-8')
    return f"data:image/png;base64,{img_str}"
