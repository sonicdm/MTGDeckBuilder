from typing import Dict, List, Optional
from pydantic import BaseModel
from uuid import UUID
from .card import Card
from .card_set import CardSet

class CardDatabase(BaseModel):
    cards: Dict[UUID, Card]
    sets: Dict[str, CardSet]

    def get_card_by_name(self, name: str) -> Optional[Card]:
        return next((card for card in self.cards.values() if card.matches_name(name)), None)

    def get_cards_in_set(self, set_code: str) -> Optional[CardSet]:
        return self.sets.get(set_code, None)

    def get_all_cards(self) -> List[Card]:
        return list(self.cards.values())

    def find_cards_by_criteria(self, **criteria) -> List[Card]:
        result = []
        for card in self.cards.values():
            if (
                (not criteria.get("name_query") or card.matches_name(criteria["name_query"])) and
                (not criteria.get("text_query") or card.matches_text_query(criteria["text_query"])) and
                (not criteria.get("rarity") or card.matches_rarity(criteria["rarity"])) and
                (not criteria.get("set_code") or card.matches_set_code(criteria["set_code"])) and
                (not criteria.get("power_value") or card.matches_power(criteria["power_value"], criteria.get("power_op", "=="))) and
                (not criteria.get("toughness_value") or card.matches_toughness(criteria["toughness_value"], criteria.get("toughness_op", "=="))) and
                (not criteria.get("mana_value") or card.matches_mana_value(criteria["mana_value"], criteria.get("mana_op", "==")))
            ):
                result.append(card)
        return result