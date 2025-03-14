from typing import List, Dict
import random
from pydantic import BaseModel
from mtg_deck_builder.models.collection import Collection, CardInCollection
# or your actual import paths

class Deck(Collection):
    """
    A deck is effectively a specialized collection with additional deck analysis methods.
    The 'cards' field is a dict of cardName -> CardInCollection, each quantity
    is how many copies are in this deck.
    """

    def sample_hand(self, hand_size: int = 7) -> List[str]:
        """
        Draws a random selection of `hand_size` cards from the deck.
        Returns a list of card names.
        """
        deck_list = []
        for cic in self.cards.values():
            deck_list.extend([cic.card.name] * cic.quantity_owned)

        if hand_size >= len(deck_list):
            return deck_list

        return random.sample(deck_list, hand_size)

    def average_mana_value(self) -> float:
        """
        Average mana value across all cards in the deck.
        Weighted by the number of copies of each card.
        """
        total_mv = 0.0
        total_cards = 0
        for cic in self.cards.values():
            c = cic.card
            mv = c.manaValue if c.manaValue is not None else (c.convertedManaCost or 0)
            total_mv += mv * cic.quantity_owned
            total_cards += cic.quantity_owned

        if total_cards == 0:
            return 0.0
        return total_mv / total_cards

    def average_power_toughness(self) -> (float, float):
        """
        Average power/toughness among creatures only.
        """
        total_power = 0.0
        total_toughness = 0.0
        creature_count = 0

        for cic in self.cards.values():
            c = cic.card
            if c.matches_type("creature"):
                p = c.power if c.power is not None else 0
                t = c.toughness if c.toughness is not None else 0
                total_power += p * cic.quantity_owned
                total_toughness += t * cic.quantity_owned
                creature_count += cic.quantity_owned

        if creature_count == 0:
            return (0.0, 0.0)
        return (total_power / creature_count, total_toughness / creature_count)

    def deck_color_identity(self) -> set:
        """
        Returns the overall color identity of the deck as a set of color codes
        (e.g. {'R', 'G'} if it's Gruul).
        """
        color_set = set()
        for cic in self.cards.values():
            c = cic.card
            if c.colorIdentity:
                for col in c.colorIdentity:
                    color_set.add(col)
        return color_set

    def color_balance(self) -> Dict[str, int]:
        """
        Returns a dict of color -> count, how many cards in that color for the deck.
        For multi-color cards, we increment multiple colors if they have them.
        Weighted by quantity_owned.
        """
        color_counts = {}
        for cic in self.cards.values():
            c = cic.card
            cnt = cic.quantity_owned
            if c.colorIdentity:
                for col in c.colorIdentity:
                    color_counts[col] = color_counts.get(col, 0) + cnt
            else:
                color_counts["C"] = color_counts.get("C", 0) + cnt
        return color_counts

    def count_mana_ramp(self) -> int:
        """
        Count how many 'ramp' cards exist in the deck, referencing the deck's color identity.
        We check the card text for 'Add {X}' where X is in the deck's identity,
        or 'search your library for a land' or similar.
        """
        ramp_count = 0
        # gather deck's color identity
        deck_ci = self.deck_color_identity()  # e.g. {'R','G'}

        for cic in self.cards.values():
            c = cic.card
            text_lower = (c.text or "").lower()

            # Check for generic ramp phrases
            if "search your library for a land" in text_lower:
                ramp_count += cic.quantity_owned
                continue

            # Check for 'Add {X}' for each color in deck_ci
            # e.g. if deck_ci has 'R', we look for 'add {r}'
            # or if it has 'G', we look for 'add {g}', etc.
            for color in deck_ci:
                pattern = f"add {{{color.lower()}}}"
                if pattern in text_lower:
                    ramp_count += cic.quantity_owned
                    break  # no need to check other colors once matched

        return ramp_count
