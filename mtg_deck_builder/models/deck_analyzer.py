from collections import defaultdict
from typing import List, Dict, Optional, Set, Tuple, Any, TYPE_CHECKING
from pathlib import Path
from mtg_deck_builder.db import get_card_types, get_keywords    
from mtg_deck_builder.models.card_meta import TypeEntry
from mtg_deckbuilder_ui.app_config import app_config

if TYPE_CHECKING:
    from mtg_deck_builder.models.deck import Deck

KEYWORDS_PATH = Path("data/mtgjson/keywords.json")
CARDTYPES_PATH = Path("data/mtgjson/CardTypes.json")
CARD_TYPES = get_card_types()
KEYWORDS = get_keywords()

class DeckAnalyzer:
    """
    Handles analysis of a Deck object.
    """
    _ALL_KEYWORDS: Optional[Set[str]] = None
    _ALL_CREATURE_TYPES: Optional[Set[str]] = None

    def __init__(self, deck: 'Deck'):
        self.deck = deck
        self._load_keyword_and_type_sets()

    @classmethod
    def _load_keyword_and_type_sets(cls):
        if cls._ALL_KEYWORDS is None or cls._ALL_CREATURE_TYPES is None:
            all_keywords = set()
            for key in ("keywordAbilities", "keywordActions", "abilityWords"):
                method_name = f"get_{key.lower()}"
                method = getattr(KEYWORDS, method_name, None)
                if callable(method):
                    all_keywords.update([k.lower() for k in method()])
            cls._ALL_KEYWORDS = all_keywords
            
            # Get creature subtypes from the data structure
            creature_data = CARD_TYPES.data.get("creature", TypeEntry())
            cls._ALL_CREATURE_TYPES = set(creature_data.subTypes)

    def average_mana_value(self) -> float:
        total_mv = sum((getattr(card, "converted_mana_cost", 0) or 0) * getattr(card, "owned_qty", 1) for card in self.deck.cards.values())
        total_cards = sum(getattr(card, "owned_qty", 1) for card in self.deck.cards.values())
        return total_mv / total_cards if total_cards else 0.0

    def average_power_toughness(self) -> Tuple[float, float]:
        def parse_stat(value) -> float:
            try:
                return float(value)
            except (ValueError, TypeError):
                return 1.0
        total_power = 0.0
        total_toughness = 0.0
        creature_count = 0
        for card in self.deck.cards.values():
            if card.matches_type("creature"):
                qty = getattr(card, "owned_qty", 1)
                total_power += parse_stat(getattr(card, "power", None)) * qty
                total_toughness += parse_stat(getattr(card, "toughness", None)) * qty
                creature_count += qty
        if creature_count == 0:
            return (0.0, 0.0)
        return (total_power / creature_count, total_toughness / creature_count)

    def deck_color_identity(self) -> Set[str]:
        color_set = set()
        for card in self.deck.cards.values():
            if getattr(card, "colors", None):
                color_set.update(card.colors)
            else:
                color_set.add("C")
        if len(color_set) > 1 and "C" in color_set:
            color_set.remove("C")
        return color_set

    def color_balance(self) -> Dict[str, int]:
        color_counts: Dict[str, int] = {}
        for card in self.deck.cards.values():
            qty = getattr(card, "owned_qty", 1)
            if getattr(card, "colors", None):
                for col in card.colors:
                    color_counts[col] = color_counts.get(col, 0) + qty
            else:
                color_counts["C"] = color_counts.get("C", 0) + qty
        return color_counts

    def count_mana_ramp(self) -> int:
        ramp_count = 0
        for card in self.deck.cards.values():
            text = (getattr(card, "text", "") or "").lower()
            qty = getattr(card, "owned_qty", 1)
            if any(phrase in text for phrase in [
                "search your library for a land", "add {", "add one mana", "add two mana",
                "add three mana", "create a treasure", "create a powerstone", "create one mana",
                "add mana of any color", "add one mana of any type", "add one mana of any color"
            ]):
                ramp_count += qty
        return ramp_count

    def count_lands(self) -> int:
        return sum(self.deck.get_quantity(card.name) for card in self.deck.cards.values() if card.matches_type("land"))

    def land_breakdown(self) -> Dict[str, int]:
        return {card.name: self.deck.get_quantity(card.name) for card in self.deck.cards.values() if card.matches_type("land")}

    def count_card_types(self) -> Dict[str, int]:
        type_counts: Dict[str, int] = defaultdict(int)
        for card in self.deck.cards.values():
            # Ensure card.types is iterable and contains only strings
            card_types = getattr(card, "types", [])
            if not isinstance(card_types, (list, tuple)):
                continue
            for t in card_types:
                # Only count if t is a string
                if isinstance(t, str):
                    type_counts[t] += self.deck.get_quantity(t)
        return type_counts

    def synergy_score(self) -> float:
        if not self.deck.cards:
            return 0.0
        creature_types = set()
        for card in self.deck.cards.values():
            if card.matches_type("creature"):
                type_line = getattr(card, "type", "").lower()
                if " - " in type_line:
                    subtypes = type_line.split(" - ")[1].split()
                    for t in subtypes:
                        if t in self._ALL_CREATURE_TYPES:
                            creature_types.add(t)
        type_synergy_count = 0
        for card in self.deck.cards.values():
            text = (getattr(card, "text", "") or "").lower()
            for creature_type in creature_types:
                if creature_type in text:
                    type_synergy_count += getattr(card, "owned_qty", 1)
        keywords = {}
        for card in self.deck.cards.values():
            text = (getattr(card, "text", "") or "").lower()
            for keyword in self._ALL_KEYWORDS:
                if keyword in text:
                    keywords[keyword] = keywords.get(keyword, 0) + getattr(card, "owned_qty", 1)
        keyword_synergy_count = 0
        for card in self.deck.cards.values():
            text = (getattr(card, "text", "") or "").lower()
            for keyword, count in keywords.items():
                if count > 1 and keyword in text and f"with {keyword}" in text:
                    keyword_synergy_count += getattr(card, "owned_qty", 1)
        total_cards = self.deck.size()
        synergy_percentage = (type_synergy_count + keyword_synergy_count) / total_cards if total_cards else 0.0
        return min(10.0, synergy_percentage * 10)

    def render_mana_curve_ascii(self) -> str:
        cmc_counts = self.mana_curve()
        if not cmc_counts:
            return "No spells in deck."
        max_count = max(cmc_counts.values())
        max_bar_length = 20
        result = ["Mana Curve:"]
        for cmc in range(0, 8):
            count = cmc_counts.get(cmc, 0)
            cmc_label = "7+" if cmc == 7 else str(cmc)
            bar_length = int((count / max_count) * max_bar_length) if max_count > 0 else 0
            bar = "█" * bar_length
            result.append(f"{cmc_label:>3}: {bar} {count}")
        return "\n".join(result)

    def mana_curve(self) -> dict:
        cmc_counts = {}
        for card in self.deck.cards.values():
            if card.matches_type("land"):
                continue
            cmc = getattr(card, "converted_mana_cost", 0) or 0
            cmc = 7 if cmc >= 7 else cmc
            cmc_counts[cmc] = cmc_counts.get(cmc, 0) + getattr(card, "owned_qty", 1)
        return cmc_counts

    def power_toughness_curve(self) -> dict:
        pt_counts = {}
        for card in self.deck.cards.values():
            if card.matches_type("creature"):
                try:
                    power = float(getattr(card, "power", 0) or 0)
                    toughness = float(getattr(card, "toughness", 0) or 0)
                    key = (power, toughness)
                    pt_counts[key] = pt_counts.get(key, 0) + getattr(card, "owned_qty", 1)
                except Exception:
                    continue
        return pt_counts

    def keyword_summary(self) -> Dict[str, int]:
        keywords = self._ALL_KEYWORDS
        summary = {k: 0 for k in keywords}
        for card in self.deck.cards.values():
            text = (getattr(card, "text", "") or "").lower()
            for k in keywords:
                if k in text:
                    summary[k] += getattr(card, "owned_qty", 1)
        return {k: v for k, v in summary.items() if v > 0}

    def count_keywords(self, keyword: str) -> int:
        keyword = keyword.lower()
        count = 0
        for card in self.deck.cards.values():
            text = (getattr(card, "text", "") or "").lower()
            if keyword in text:
                count += getattr(card, "owned_qty", 1)
        return count

    def _stringify_keys(self, d: Dict[Any, Any]) -> Dict[str, Any]:
        if not isinstance(d, dict):
            return d
        return {str(k): self._stringify_keys(v) for k, v in d.items()}

    def summary_dict(self) -> Dict[str, Any]:
        avg_power, avg_toughness = self.average_power_toughness()
        expensive_cards = []
        max_cmc = 0
        for card in self.deck.cards.values():
            cmc = getattr(card, "converted_mana_cost", 0) or 0
            if cmc > max_cmc:
                max_cmc = cmc
                expensive_cards = [card.name]
            elif cmc == max_cmc:
                expensive_cards.append(card.name)
        rarity_breakdown = {}
        for card in self.deck.cards.values():
            rarity = getattr(card, "rarity", "Common")
            rarity_breakdown[rarity] = rarity_breakdown.get(rarity, 0) + getattr(card, "owned_qty", 1)
        keyword_counts = self.keyword_summary()
        frequent_keywords = []
        if keyword_counts:
            max_count = max(keyword_counts.values())
            frequent_keywords = [k for k, v in keyword_counts.items() if v == max_count]
        summary = {
            "name": self.deck.name,
            "total_cards": self.deck.size(),
            "land_count": self.count_lands(),
            "spell_count": self.deck.size() - self.count_lands(),
            "avg_mana_value": round(self.average_mana_value(), 2),
            "color_balance": self.color_balance(),
            "color_identity": list(self.deck_color_identity()),
            "type_counts": self.count_card_types(),
            "ramp_count": self.count_mana_ramp(),
            "lands": self.count_lands(),
            "avg_power": round(avg_power, 2),
            "avg_toughness": round(avg_toughness, 2),
            "synergy": round(self.synergy_score(), 2),
            "mana_curve": self.mana_curve(),
            "power_toughness_curve": self.power_toughness_curve(),
            "keyword_summary": self.keyword_summary(),
            "land_breakdown": self.land_breakdown(),
            "rarity_breakdown": rarity_breakdown,
            "max_cmc": max_cmc,
            "expensive_cards": expensive_cards,
            "sample_hand": [card.name for card in self.deck.sample_hand(7)],
            "frequent_keywords": frequent_keywords
        }
        return self._stringify_keys(summary) 