import random
from typing import List, Dict, Optional, Set, Tuple

from sqlalchemy.orm import Session

from mtg_deck_builder.db import CardDB
from mtg_deck_builder.db.repository import CardRepository


class Deck(CardRepository):
    """
    A deck is a specialized CardRepository with additional deck analysis methods.
    The 'cards' field is a dict of cardName -> CardDB, each with an 'owned_qty' attribute
    indicating how many copies are in this deck.
    """
    session: Optional[Session] = None
    name: str = ""

    def __init__(self, cards: Optional[Dict[str, CardDB]] = None, session: Optional[Session] = None, name: str = ""):
        self.session = session
        self.name = name
        self._cards: Dict[str, CardDB] = cards if cards is not None else {}

    @classmethod
    def from_repo(cls, repo: CardRepository, limit: int = 60, random_cards: bool = True) -> 'Deck':
        all_cards = repo.get_all_cards()
        if not all_cards:
            raise ValueError("No cards found in the repository.")
        if random_cards:
            random.shuffle(all_cards)
        selected = all_cards[:limit] if limit else all_cards
        cards_dict = {}
        for card in selected:
            card.owned_qty = 1
            cards_dict[card.name] = card
        return cls(cards=cards_dict, session=repo.session)

    def insert_card(self, card: CardDB) -> None:
        """
        Inserts a card into the deck, incrementing owned_qty if already present.
        """
        if card.name in self._cards:
            self._cards[card.name].owned_qty += 1
        else:
            card.owned_qty = 1
            self._cards[card.name] = card

    def sample_hand(self, hand_size: int = 7) -> List[CardDB]:
        """
        Draws a random selection of `hand_size` cards from the deck.
        Returns a list of CardDB objects.
        """
        deck_list = [card for card in self.cards.values() for _ in range(getattr(card, "owned_qty", 1))]
        if hand_size > len(deck_list):
            raise ValueError("Hand size exceeds the number of cards in the deck.")
        return random.sample(deck_list, hand_size)

    def average_mana_value(self) -> float:
        """
        Average mana value across all cards in the deck, weighted by owned_qty.
        """
        total_mv = sum((getattr(card, "converted_mana_cost", 0) or 0) * getattr(card, "owned_qty", 1) for card in
                       self.cards.values())
        total_cards = sum(getattr(card, "owned_qty", 1) for card in self.cards.values())
        return total_mv / total_cards if total_cards else 0.0

    def average_power_toughness(self) -> Tuple[float, float]:
        """
        Average power/toughness among creatures only, weighted by owned_qty.
        """

        def parse_stat(value) -> float:
            try:
                return float(value)
            except (ValueError, TypeError):
                return 1.0

        total_power = 0.0
        total_toughness = 0.0
        creature_count = 0

        for card in self.cards.values():
            if card.matches_type("creature"):
                qty = getattr(card, "owned_qty", 1)
                total_power += parse_stat(getattr(card, "power", None)) * qty
                total_toughness += parse_stat(getattr(card, "toughness", None)) * qty
                creature_count += qty

        if creature_count == 0:
            return (0.0, 0.0)
        return (total_power / creature_count, total_toughness / creature_count)

    def deck_color_identity(self) -> Set[str]:
        """
        Returns the overall color identity of the deck as a set of color codes.
        """
        color_set = set()
        for card in self.cards.values():
            if getattr(card, "colors", None):
                color_set.update(card.colors)
            else:
                color_set.add("C")
        if len(color_set) > 1 and "C" in color_set:
            color_set.remove("C")
        return color_set

    def color_balance(self) -> Dict[str, int]:
        """
        Returns a dict of color -> count, how many cards in that color for the deck.
        For multi-color cards, increments multiple colors if present.
        Weighted by owned_qty.
        """
        color_counts: Dict[str, int] = {}
        for card in self.cards.values():
            qty = getattr(card, "owned_qty", 1)
            if getattr(card, "colors", None):
                for col in card.colors:
                    color_counts[col] = color_counts.get(col, 0) + qty
            else:
                color_counts["C"] = color_counts.get("C", 0) + qty
        return color_counts

    def count_mana_ramp(self) -> int:
        """
        Count how many 'ramp' cards exist in the deck, referencing the deck's color identity.
        Checks card text for 'Add {X}' or 'search your library for a land'.
        """
        ramp_count = 0
        deck_ci = self.deck_color_identity()
        for card in self.cards.values():
            text_lower = (getattr(card, "text", "") or "").lower()
            qty = getattr(card, "owned_qty", 1)
            if "search your library for a land" in text_lower:
                ramp_count += qty
                continue
            for color in deck_ci:
                pattern = f"add {{{color.lower()}}}"
                if pattern in text_lower:
                    ramp_count += qty
                    break
        return ramp_count

    def count_lands(self) -> int:
        """
        Count the number of land cards in the deck (weighted by owned_qty).
        """
        return sum(getattr(card, "owned_qty", 1) for card in self.cards.values() if card.matches_type("land"))

    def land_breakdown(self) -> Dict[str, int]:
        """
        Returns a dict of land card name -> quantity in the deck.
        """
        return {card.name: getattr(card, "owned_qty", 1) for card in self.cards.values() if card.matches_type("land")}

    @property
    def cards(self) -> Dict[str, CardDB]:
        """
        Returns the cards in the deck as a dictionary of card name -> CardDB.
        """
        return self._cards

    def count_card_types(self) -> Dict[str, int]:
        """
        Returns a count of cards for each basic card type in the deck (weighted by owned_qty).
        Types counted: Land, Instant, Sorcery, Enchantment, Creature, Artifact, Planeswalker
        """
        type_keywords = ["Land", "Instant", "Sorcery", "Enchantment", "Creature", "Artifact", "Planeswalker"]
        type_counts: Dict[str, int] = {}
        for card in self.cards.values():
            card_type = getattr(card, "type", "") or ""
            qty = getattr(card, "owned_qty", 1)
            for type_kw in type_keywords:
                if type_kw.lower() in card_type.lower():
                    type_counts[type_kw] = type_counts.get(type_kw, 0) + qty
        return type_counts

    def mtg_arena_import(self):
        """
        Returns a string formatted for MTG Arena import.
        """
        output = []
        for card in self.cards.values():
            qty = getattr(card, "owned_qty", 1)
            output.append(f"{qty} {card.name}")
        return "\n".join(output)
