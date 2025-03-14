import math
from typing import Optional, List, Dict
from pydantic import BaseModel, validator
from pydantic import Field, field_validator


class LeadershipSkills(BaseModel):
    brawl: Optional[bool] = None
    commander: Optional[bool] = None
    oathbreaker: Optional[bool] = None


class ForeignData(BaseModel):
    flavorText: Optional[str] = None
    language: Optional[str] = None
    multiverseId: Optional[int] = None
    name: Optional[str] = None
    text: Optional[str] = None
    type: Optional[str] = None



VALID_OPERATORS = {"<", "<=", "==", ">=", ">"}


def compare_values(card_value: float | None, target: float, op: str) -> bool:
    """
    Compare card_value to target using the given operator.
    If card_value is None, we return False (unless you choose otherwise).
    """
    if card_value is None:
        return False

    if op not in VALID_OPERATORS:
        # If invalid operator, treat as no match or raise an error
        return False

    if op == "<":
        return card_value < target
    elif op == "<=":
        return card_value <= target
    elif op == "==":
        return math.isclose(card_value, target, rel_tol=1e-9)
    elif op == ">=":
        return card_value >= target
    elif op == ">":
        return card_value > target
    return False


from typing import Optional, List, Dict
from pydantic import BaseModel, field_validator

class AtomicCard(BaseModel):
    name: str
    layout: Optional[str] = None
    manaCost: Optional[str] = None
    text: Optional[str] = None
    type: Optional[str] = None
    supertypes: Optional[List[str]] = None
    types: Optional[List[str]] = None
    subtypes: Optional[List[str]] = None
    colorIdentity: Optional[List[str]] = None

    # Older naming; still used by some data
    convertedManaCost: Optional[float] = None

    legalities: Optional[Dict[str, str]] = None
    keywords: Optional[List[str]] = None

    # We'll store these as floats or None
    power: Optional[float] = None
    toughness: Optional[float] = None
    # The new official name for converted mana cost
    manaValue: Optional[float] = None

    #
    # Pydantic v2 "field_validator" for numeric fields
    #
    @field_validator("power", "toughness", mode="before")
    def parse_power_toughness(cls, v):
        """
        Attempt to parse power/toughness as float. If it's non-numeric (like '*'), store None.
        """
        if v is None:
            return None
        v_str = str(v).strip()
        try:
            return float(v_str)
        except ValueError:
            return None

    @field_validator("manaValue", mode="before")
    def parse_mana_value(cls, v):
        """
        Attempt to parse manaValue as float. If invalid or missing, store None.
        """
        if v is None:
            return None
        try:
            return float(v)
        except ValueError:
            return None

    # -------------- Convenience Methods --------------
    def full_type_line(self) -> str:
        if self.type:
            return self.type
        supertypes_str = " ".join(self.supertypes or [])
        types_str = " ".join(self.types or [])
        subtypes_str = ""
        if self.subtypes:
            subtypes_str = " — " + " ".join(self.subtypes)
        line = f"{supertypes_str} {types_str}{subtypes_str}".strip()
        while "  " in line:
            line = line.replace("  ", " ")
        return line

    def color_identity_str(self) -> str:
        if not self.colorIdentity:
            return ""
        return ",".join(self.colorIdentity)

    def is_legal_in(self, fmt: str) -> bool:
        if not self.legalities or fmt.lower() not in self.legalities:
            return False
        return self.legalities[fmt.lower()] == "Legal"

    def short_summary(self) -> str:
        mv = self.manaValue if self.manaValue is not None else (self.convertedManaCost or 0)
        return f"{self.name} ({mv} CMC) - {self.full_type_line()}"

    # -------------- Matching Logic --------------
    def matches_name(self, name_query: str) -> bool:
        return name_query.lower() in self.name.lower()

    def matches_text(self, text_query: str) -> bool:
        return text_query.lower() in (self.text or "").lower()

    def matches_type(self, type_query: str) -> bool:
        tq = type_query.lower()
        card_type_str = (self.type or "").lower()
        if tq in card_type_str:
            return True
        if self.types and any(tq == t.lower() for t in self.types):
            return True
        if self.subtypes and any(tq == s.lower() for s in self.subtypes):
            return True
        return False

    def matches_color_identity(self, query_colors: List[str], mode: str = "exact") -> bool:
        card_ci = set(self.colorIdentity or [])
        query_set = set(c.upper() for c in query_colors)
        if mode == "exact":
            return card_ci == query_set
        elif mode == "contains":
            return query_set.issubset(card_ci)
        elif mode == "only":
            return card_ci.issubset(query_set)
        return False

    def matches_keyword(self, keyword_query: str) -> bool:
        if not self.keywords:
            return False
        return any(keyword_query.lower() == kw.lower() for kw in self.keywords)

    # Numeric comparisons
    def matches_power(self, value: float, op: str) -> bool:
        return compare_values(self.power, value, op)

    def matches_toughness(self, value: float, op: str) -> bool:
        return compare_values(self.toughness, value, op)

    def matches_mana_value(self, value: float, op: str) -> bool:
        # fallback to convertedManaCost if manaValue is None
        actual_mv = self.manaValue if self.manaValue is not None else self.convertedManaCost
        return compare_values(actual_mv, value, op)


from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class AtomicCards(BaseModel):
    cards: Dict[str, AtomicCard] = Field(..., alias="data")

    class Config:
        allow_population_by_field_name = True

    def filter_cards(
        self,
        name_query: Optional[str] = None,
        text_query: Optional[str] = None,
        type_query: Optional[str] = None,
        color_identity: Optional[List[str]] = None,
        color_mode: str = "exact",
        keyword_query: Optional[str] = None,
        power_value: Optional[float] = None,
        power_op: str = "==",
        toughness_value: Optional[float] = None,
        toughness_op: str = "==",
        mana_value: Optional[float] = None,
        mana_op: str = "=="
    ) -> List[AtomicCard]:
        """
        A flexible filter that combines multiple criteria, including numeric comparisons for
        power, toughness, and mana value.
        """
        results = list(self.cards.values())

        # Text / Name / Type / Keyword / Color Identity filters
        if name_query:
            results = [c for c in results if c.matches_name(name_query)]
        if text_query:
            results = [c for c in results if c.matches_text(text_query)]
        if type_query:
            results = [c for c in results if c.matches_type(type_query)]
        if color_identity:
            results = [c for c in results if c.matches_color_identity(color_identity, mode=color_mode)]
        if keyword_query:
            results = [c for c in results if c.matches_keyword(keyword_query)]

        # Numeric filters
        if power_value is not None:
            results = [c for c in results if c.matches_power(power_value, power_op)]
        if toughness_value is not None:
            results = [c for c in results if c.matches_toughness(toughness_value, toughness_op)]
        if mana_value is not None:
            results = [c for c in results if c.matches_mana_value(mana_value, mana_op)]

        return results
