from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field
from uuid import UUID
import json


# Define a model for foreign language data
class ForeignData(BaseModel):
    language: str
    multiverse_id: Optional[int] = None
    name: str
    text: Optional[str] = None
    type: Optional[str] = None
    flavor_text: Optional[str] = None


# Define a model for legalities
class Legalities(BaseModel):
    formats: Dict[str, str]

    def is_legal_in(self, format_name: str) -> bool:
        return self.formats.get(format_name, "").lower() == "legal"


# Define a model for rulings
class Ruling(BaseModel):
    date: str
    text: str


# Define a model for individual cards
class Card(BaseModel):
    uid: UUID = Field(..., description="Unique identifier for the card")
    name: str
    type: str
    rarity: Optional[str] = None
    mana_cost: Optional[str] = None
    power: Optional[Union[int, str]] = None  # Some values are "*"
    toughness: Optional[Union[int, str]] = None
    abilities: Optional[List[str]] = []
    flavor_text: Optional[str] = None
    text: Optional[str] = None
    artist: Optional[str] = None
    number: Optional[str] = None
    set_code: Optional[str] = None
    colors: Optional[List[str]] = []
    legalities: Legalities = Legalities(formats={})
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


# Define a model for sets that maps cards by UID
class CardSet(BaseModel):
    set_name: str
    set_code: str
    release_date: Optional[str] = None
    block: Optional[str] = None
    cards: Dict[UUID, int]  # Mapping from Card UID to some integer value (e.g., count or identifier)


# Define the overall schema structure
class CardDatabase(BaseModel):
    cards: Dict[UUID, Card]  # Centralized card storage
    sets: Dict[str, CardSet]  # Set storage by set code

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
                    (not criteria.get("power_value") or card.matches_power(criteria["power_value"],
                                                                           criteria.get("power_op", "=="))) and
                    (not criteria.get("toughness_value") or card.matches_toughness(criteria["toughness_value"],
                                                                                   criteria.get("toughness_op",
                                                                                                "=="))) and
                    (not criteria.get("mana_value") or card.matches_mana_value(criteria["mana_value"],
                                                                               criteria.get("mana_op", "==")))
            ):
                result.append(card)
        return result


# Function to load JSON and populate models
def load_card_database(json_file: str) -> CardDatabase:
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # data structure db -> 'data' -> 'setname' -> set data including cards.
    # all cards need to be combined into a single dictionary, with the sets being stored separately.
    all_cards = {}
    all_sets = {}
    for set_code, setdata in data['data'].items():
        # get cards from setdata
        for card in setdata['cards']:
            card_uid = UUID(card['uuid'])
            card_data = Card(
                uid=card_uid,
                name=card['name'],
                type=card['type'],
                rarity=card.get('rarity'),
                mana_cost=card.get('manaCost'),
                power=card.get('power'),
                toughness=card.get('toughness'),
                abilities=card.get('abilities', []),
                flavor_text=card.get('flavorText'),
                text=card.get('text'),
                artist=card.get('artist'),
                number=card.get('number'),
                set_code=set_code,
                colors=card.get('colors', []),
                legalities=Legalities(formats=card.get('legalities', {})),
                rulings=[Ruling(**ruling) for ruling in card.get('rulings', [])],
                foreign_data=[ForeignData(**foreign) for foreign in card.get('foreignData', [])]
            )
            all_cards[card_uid] = card_data
            # the rest goes into the set metadata
            set_metadata = setdata.copy()
            set_metadata.pop('cards')
            all_sets[set_code] = set_metadata

    return CardDatabase(cards=all_cards, sets=all_sets)


model_json = r"Z:\Scripts\MTGDecks\reference\10E.json"
model = load_card_database(model_json)

pass
