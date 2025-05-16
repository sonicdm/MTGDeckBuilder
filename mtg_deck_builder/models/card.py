from typing import List, Optional, Union, Dict
from pydantic import BaseModel, Field
from uuid import UUID
from mtg_deck_builder.models.card_metadata import Legalities, ForeignData, Ruling

class Card(BaseModel):
    uid: UUID = Field(..., description="Unique identifier for the card")
    name: str
    type: str
    rarity: Optional[str] = None
    mana_cost: Optional[str] = None
    power: Optional[Union[int, str]] = None
    toughness: Optional[Union[int, str]] = None
    abilities: Optional[List[str]] = []
    flavor_text: Optional[str] = None
    text: Optional[str] = None
    artist: Optional[str] = None
    number: Optional[str] = None
    set_code: Optional[str] = None
    colors: Optional[List[str]] = []
    legalities: Optional[List[Legalities]] = []
    rulings: Optional[List[Ruling]] = []
    foreign_data: Optional[List[ForeignData]] = []

    def is_color_identity(self, colors: List[str], mode: str = "exact") -> bool:
        card_colors = set(self.colors or [])
        query_colors = set(colors)
        if mode == "exact":
            return card_colors == query_colors
        elif mode == "subset":
            return query_colors.issubset(card_colors)
        elif mode == "superset":
            return card_colors.issubset(query_colors)
        elif mode == "any":
            return bool(card_colors & query_colors)
        return False

    def matches_rarity(self, rarity: str) -> bool:
        return self.rarity and self.rarity.lower() == rarity.lower()

    def matches_set_code(self, set_code: str) -> bool:
        return self.set_code and self.set_code.lower() == set_code.lower()

    def matches_text_query(self, query: str) -> bool:
        return query.lower() in (self.text or "").lower()

    def matches_name(self, name: str) -> bool:
        return name.lower() in self.name.lower()

    def matches_power(self, value: float, op: str) -> bool:
        if isinstance(self.power, (int, float)):
            return eval(f"{float(self.power)} {op} {value}")
        return False

    def matches_toughness(self, value: float, op: str) -> bool:
        if isinstance(self.toughness, (int, float)):
            return eval(f"{float(self.toughness)} {op} {value}")
        return False

    def matches_mana_value(self, value: float, op: str) -> bool:
        try:
            mana_cost_value = sum(map(int, filter(str.isdigit, self.mana_cost or "0")))
        except ValueError:
            mana_cost_value = 0
        return eval(f"{mana_cost_value} {op} {value}")


