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
        
        # Check if this is a commander deck
        is_commander_deck = False
        commander_name = None
        
        # Check if deck has a commander field in config
        if hasattr(self.deck, 'config') and self.deck.config:
            if hasattr(self.deck.config, 'commander') and self.deck.config.commander:
                commander_name = self.deck.config.commander
                is_commander_deck = True
            elif hasattr(self.deck.config, 'deck') and hasattr(self.deck.config.deck, 'commander') and self.deck.config.deck.commander:
                commander_name = self.deck.config.deck.commander
                is_commander_deck = True
            elif hasattr(self.deck.config, 'deck') and hasattr(self.deck.config.deck, 'legalities'):
                legalities = self.deck.config.deck.legalities
                if any(format_name in ['commander', 'brawl', 'historicbrawl', 'standardbrawl'] for format_name in legalities):
                    is_commander_deck = True
        
        # Also check if deck has exactly 100 cards and singleton rule (common commander indicators)
        if not is_commander_deck:
            total_cards = sum(self.deck.inventory.values())
            max_copies = max(self.deck.inventory.values()) if self.deck.inventory else 0
            if total_cards == 100 and max_copies == 1:
                is_commander_deck = True
        
        if is_commander_deck:
            # Commander format - separate commander and deck sections
            output.append("\nCommander")
            
            # Find and add commander card
            if commander_name:
                # Look for the commander card in the deck
                commander_found = False
                for card in self.deck.cards.values():
                    if card.name == commander_name:
                        qty = self.deck.get_quantity(str(card.name))
                        output.append(f"{qty} {card.name}")
                        commander_found = True
                        break
                
                if not commander_found:
                    # Commander not found in deck, add it anyway
                    output.append(f"1 {commander_name}")
            
            output.append("\nDeck")
            
            # Add all other cards (excluding commander if it was already added)
            for card in self.deck.cards.values():
                if commander_name and card.name == commander_name:
                    continue  # Skip commander as it was already added
                qty = self.deck.get_quantity(str(card.name))
                output.append(f"{qty} {card.name}")
        else:
            # Standard format - all cards in Deck section
            output.append("\nDeck")
            for card in self.deck.cards.values():
                qty = self.deck.get_quantity(str(card.name))
                output.append(f"{qty} {card.name}")
        
        return "\n".join(output) 