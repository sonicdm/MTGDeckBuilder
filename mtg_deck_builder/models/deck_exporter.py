from typing import Dict, Any, TYPE_CHECKING
import pandas as pd

from mtg_deck_builder.models.deck_analyzer import DeckAnalyzer

if TYPE_CHECKING:
    from mtg_deck_builder.models.deck import Deck


class DeckExporter:
    """
    Handles exporting a Deck object to various formats.
    """

    def __init__(self, deck: 'Deck'):
        self.deck = deck

    def _safe_convert_power_toughness(self, value):
        """
        Safely convert power/toughness value to float, handling special cases.
        
        Args:
            value: Power or toughness value to convert
            
        Returns:
            float or None: Converted value, or None if invalid
        """
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def to_dataframe(self) -> pd.DataFrame:
        """
        Convert deck to pandas DataFrame.
        
        Returns:
            DataFrame with deck data
        """
        rows = []
        for card in self.deck.cards.values():
            rows.append({
                "Name": getattr(card, "name", ""),
                "Quantity": getattr(card, "owned_qty", 1),
                "Mana Cost": getattr(card, "mana_cost", ""),
                "Converted Mana Cost": getattr(card, "converted_mana_cost", 0),
                "Card Type": getattr(card, "type", ""),
                "Power": self._safe_convert_power_toughness(getattr(card, "power", None)) if card.matches_type("creature") else None,
                "Toughness": self._safe_convert_power_toughness(getattr(card, "toughness", None)) if card.matches_type("creature") else None,
                "Text": getattr(card, "text", ""),
                "Rarity": getattr(card, "rarity", ""),
                "Colors": ", ".join(getattr(card, "colors", []) or [])
            })
        return pd.DataFrame(rows)

    def as_json(self) -> Dict[str, Any]:
        """
        Convert deck to JSON-serializable dict, including analysis stats.
        
        Returns:
            Dict containing deck data
        """
        card_list = []
        for card in self.deck.cards.values():
            card_list.append({
                "name": getattr(card, "name", ""),
                "quantity": getattr(card, "owned_qty", 1),
                "mana_cost": getattr(card, "mana_cost", ""),
                "converted_mana_cost": getattr(card, "converted_mana_cost", 0),
                "type": getattr(card, "type", ""),
                "power": self._safe_convert_power_toughness(getattr(card, "power", None)) if card.matches_type("creature") else None,
                "toughness": self._safe_convert_power_toughness(getattr(card, "toughness", None)) if card.matches_type("creature") else None,
                "text": getattr(card, "text", ""),
                "rarity": getattr(card, "rarity", ""),
                "colors": getattr(card, "colors", []) or []
            })
            
        deck_config_json = None
        if hasattr(self.deck, "config") and self.deck.config is not None:
            cfg = self.deck.config
            if hasattr(cfg, "model_dump"):
                deck_config_json = cfg.model_dump()
            elif hasattr(cfg, "to_dict"):
                deck_config_json = cfg.to_dict()
            elif hasattr(cfg, "as_dict"):
                deck_config_json = cfg.as_dict()
            elif hasattr(cfg, "__dict__"):
                deck_config_json = dict(cfg.__dict__)

        analyzer = DeckAnalyzer(self.deck)
        
        return {
            "name": self.deck.name,
            "cards": card_list,
            "stats": analyzer.summary_dict(),
            "arena_export": self.mtg_arena_import(),
            "deck_config": deck_config_json
        }

    def mtg_arena_import(self):
        """
        Returns a string formatted for MTG Arena import.

        Returns:
            str: Decklist formatted for MTG Arena import.
        """
        output = []
        # Add Arena About header with deck name
        output.append("About")
        output.append(f"Name {self.deck.name if self.deck.name else 'Unnamed Deck'}")
        output.append("\nDeck")  # Blank line before decklist
        for card in self.deck.cards.values():
            qty = self.deck.get_quantity(str(card.name))
            output.append(f"{qty} {card.name}")
        return "\n".join(output) 