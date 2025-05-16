import json
import math
import re
from typing import Optional, List, Dict, Union

from pydantic import BaseModel
from pydantic import field_validator


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


class AtomicCard(BaseModel):
    name: str
    layout: Optional[str] = None
    manaCost: Optional[str] = None
    text: Optional[str] = None
    type: Optional[str] = None
    supertypes: Optional[List[str]] = None
    types: Optional[List[str]] = None
    subtypes: Optional[List[str]] = None
    colorIdentity: List[str] = [""]  # Always defaults to [""] if colorless

    # Older naming; still used by some data
    convertedManaCost: Optional[float] = None

    legalities: Optional[Dict[str, str]] = None
    keywords: Optional[List[str]] = None

    # We'll store these as floats or None
    power: Optional[float] = None
    toughness: Optional[float] = None
    # The new official name for converted mana cost
    manaValue: Optional[float] = None

    # ownership data
    owned: Optional[bool] = False
    quantity: Optional[int] = 0

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

    @field_validator("colorIdentity", mode="before")
    def set_default_color_identity(cls, v):
        """Ensures colorless cards always have colorIdentity set to [""]"""
        if v is None or v == []:
            return [""]
        return v
    @field_validator("keywords", mode="before")
    def parse_keywords(cls, v):
        """
        Ensure keywords are stored as a list of strings.
        """
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return v
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
        """
        Return the color identity as a comma-separated. If no color identity, return an empty string.
        No color identity is for artifacts etc. Things that use generic mana.
        """
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
    def matches_name(self, queries: List[str], mode: str = "or") -> bool:
        """Check if card name matches any/all queries based on mode."""
        if not queries:
            return True
        if mode == "or":
            return any(q.lower() in self.name.lower() for q in queries)
        elif mode == "and":
            return all(q.lower() in self.name.lower() for q in queries)
        return False

    def matches_text(self, queries: List[str], mode: str = "or") -> bool:
        """Check if card text matches any/all queries based on mode."""
        if not queries:
            return True
        if mode == "or":
            return any(q.lower() in (self.text or "").lower() for q in queries)
        elif mode == "and":
            return all(q.lower() in (self.text or "").lower() for q in queries)
        return False

    def matches_type(self, queries: List[str], mode: str = "or") -> bool:
        """Check if card type matches any/all queries based on mode."""
        if not queries:
            return True
        if type(queries) == str:
            queries = [queries]
        if not len([str(t) for t in queries]) > 0:
            return False

        card_type_str = (self.type or "").lower()
        if mode == "or":
            return any(q.lower() in card_type_str for q in queries)
        elif mode == "and":
            return all(q.lower() in card_type_str for q in queries)
        return False

    def matches_keyword(self, queries: List[str], mode: str = "or") -> bool:
        """Check if card has any/all keywords based on mode."""
        if not queries or not self.keywords:
            return True
        if mode == "or":
            return any(q.lower() in [kw.lower() for kw in self.keywords] for q in queries)
        elif mode == "and":
            return all(q.lower() in [kw.lower() for kw in self.keywords] for q in queries)
        return False

    def matches_color_identity(self, query_colors: List[str], mode: str = "exact") -> bool:
        """Matches color identity based on different modes.

        Modes:
        - "exact": Card must match query_colors exactly (but "" is ignored for colored cards).
        - "contains": Card must contain all colors in query_colors.
        - "only": Card must have only colors from query_colors (or be colorless).
        - [""] as query_colors: Returns only colorless cards.

        Raises:
            ValueError: If an unknown mode is used.
        """

        valid_modes = {"exact", "contains", "only"}
        if mode not in valid_modes:
            raise ValueError(f"Invalid mode '{mode}'. Expected one of: {valid_modes}")

        card_ci = set(self.colorIdentity)
        query_set = set(query_colors)

        if query_colors == [""]:
            return card_ci == {""}

        if mode == "exact":
            if "" in query_set:
                query_set.remove("")
            return card_ci == query_set or (card_ci == {""} and "" in query_colors)

        elif mode == "contains":
            return query_set.issubset(card_ci)

        elif mode == "only":
            return card_ci.issubset(query_set)

    # Numeric comparisons
    def matches_power(self, value: float, op: str) -> bool:
        return compare_values(self.power, value, op)

    def matches_toughness(self, value: float, op: str) -> bool:
        return compare_values(self.toughness, value, op)

    def matches_mana_value(self, value: float, op: str) -> bool:
        actual_mv = self.manaValue if self.manaValue is not None else self.convertedManaCost
        return compare_values(actual_mv, value, op)

    def __hash__(self):
        """Use a sorted JSON string of the model for a stable hash."""
        json_repr = json.dumps(self.model_dump(), sort_keys=True)
        return hash(json_repr)

    def __eq__(self, other):
        """Compare two AtomicCard instances using their full JSON representation."""
        if not isinstance(other, AtomicCard):
            return False
        return json.dumps(self.model_dump(), sort_keys=True) == json.dumps(other.model_dump(), sort_keys=True)

    def __repr__(self):
        # format as manacost - name - type - color identity - mana value - power/toughness
        # only include the parts that are not None
        parts = [self.name]
        if self.manaCost:
            parts.insert(0, self.manaCost)
        if self.type:
            parts.append(self.type)
        if self.colorIdentity:
            parts.append(self.color_identity_str())
        if self.manaValue:
            parts.append(f"{self.manaValue} CMC")
        if self.power is not None and self.toughness is not None:
            parts.append(f"{int(self.power)}/{int(self.toughness)}")
        return " - ".join(parts)


from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class AtomicCards(BaseModel):
    cards: Dict[str, AtomicCard] = Field(..., alias="data")

    class Config:
        populate_by_name = True

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
            mana_op: str = "==",
            legal_in: Optional[list] = None
    ) -> "AtomicCards":
        """
        Filter cards based on multiple criteria, including numeric comparisons for power, toughness, and mana value.

        Returns:
            AtomicCards: The filtered collection of cards.
        """
        filtered_cards = self._filter_logic(
            name_query, text_query, type_query, color_identity, color_mode,
            keyword_query, power_value, power_op, toughness_value, toughness_op,
            mana_value, mana_op, legal_in
        )
        # return an AtomicCards object with exact copies of the filtered cards
        return filtered_cards

    def filter_cards_set(
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
            mana_op: str = "==",
            legal_in: Optional[list] = None
    ) -> set[AtomicCard]:
        """
        Filter cards based on multiple criteria, returning a list of AtomicCard objects.

        Returns:
            List[AtomicCard]: The filtered collection of cards.
        """
        return self._filter_logic(
            name_query, text_query, type_query, color_identity, color_mode,
            keyword_query, power_value, power_op, toughness_value, toughness_op,
            mana_value, mana_op, legal_in
        )

    def _filter_logic(
            self,
            name_query: Optional[Union[str, List[str]]] = None,
            text_query: Optional[Union[str, List[str]]] = None,
            type_query: Optional[Union[str, List[str]]] = None,
            color_identity: Optional[List[str]] = None,
            color_mode: str = "exact",
            keyword_query: Optional[Union[str, List[str]]] = None,
            power_value: Optional[float] = None,
            power_op: str = "==",
            toughness_value: Optional[float] = None,
            toughness_op: str = "==",
            mana_value: Optional[float] = None,
            mana_op: str = "==",
            legal_in: Optional[Union[str, List[str]]] = None,
            text_match_mode: str = "or"  # "or" means match any, "and" means match all
    ) -> Union["AtomicCards", set[AtomicCard]]:
        """
        Filter cards based on multiple criteria, supporting list queries and text-based match modes.

        Returns:
            AtomicCards: The filtered collection of cards.
        """

        valid_modes = {"or", "and"}
        if text_match_mode not in valid_modes:
            raise ValueError(f"Invalid text_match_mode '{text_match_mode}'. Expected one of: {valid_modes}")

        # Ensure all text-based queries are converted to lists
        if isinstance(name_query, str):
            name_query = [name_query]
        if isinstance(text_query, str):
            text_query = [text_query]
        if isinstance(type_query, str):
            type_query = [type_query]
        if isinstance(keyword_query, str):
            keyword_query = [keyword_query]
        if isinstance(legal_in, str):
            legal_in = [legal_in]

        all_cards = list(self.cards.values())
        filtered_cards = []

        for card in all_cards:
            # ✅ **Apply legality filtering FIRST to prevent unnecessary processing**
            if legal_in is not None and not all(card.is_legal_in(fmt) for fmt in legal_in):
                # print(f"⚠️ Skipping {card.name} - Not legal in {legal_in}")
                continue  # Skip immediately if not Standard-legal

            # ✅ Apply text-based filtering (with match mode)
            if not card.matches_name(name_query, text_match_mode):
                continue
            if not card.matches_text(text_query, text_match_mode):
                continue
            if not card.matches_type(type_query, text_match_mode):
                continue
            if not card.matches_keyword(keyword_query, text_match_mode):
                continue

            # ✅ Apply strict filters (color, power, toughness, mana)
            if color_identity is not None and not card.matches_color_identity(color_identity, color_mode):
                continue
            if power_value is not None and not card.matches_power(power_value, power_op):
                continue
            if toughness_value is not None and not card.matches_toughness(toughness_value, toughness_op):
                continue
            if mana_value is not None and not card.matches_mana_value(mana_value, mana_op):
                continue

            # ✅ **Now that it passed all filters, add to the result**
            filtered_cards.append(card)

        return AtomicCards(data={c.name: c for c in filtered_cards})

    def get_card(
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
            mana_op: str = "==",
            legal_in: Optional[list] = None
    ) -> Optional["AtomicCard"]:
        """
        Retrieve a single card based on filtering criteria.

        Returns:
            AtomicCard: The first matching card.
            None: If no matching card is found.
        """
        filtered_cards = self.filter_cards_set(
            name_query, text_query, type_query, color_identity, color_mode,
            keyword_query, power_value, power_op, toughness_value, toughness_op,
            mana_value, mana_op, legal_in
        )

        if not filtered_cards:
            return None  # No match found
        cards = list(filtered_cards.cards.values())
        if len(filtered_cards) > 1:
            # pick the card that has the exact name if it exists
            for c in cards:
                if c.name == name_query:
                    return c

            # account for cards that have the same name twice (double faced or otherwise)

            shortest_card = min(cards, key=lambda c: len(c.name))
            # check if all the card names are similar to the shortest card name
            if all(shortest_card.name in c.name for c in cards):
                return shortest_card
            # # print the search terms and the cards that were found
            # print(f"Search terms: {name_query}")
            # print(f"Cards found: {[c.name for c in cards]}")
            # # throw a warning and dont return any cards if multiple cards are found and none of the above conditions are met
            # # print warning message in warning text color
            # # print("\033[93mWarning: Multiple cards found, and no exact match, returning None.\033[0m")
        # get the first card from the AtomicCards object dict of cards
        return filtered_cards.cards.popitem()[1]

    @property
    def total_cards(self):
        """
        Returns the total number of cards in the collection
        :return:
        """
        return len(self.cards)

    def get_card_by_name(self, name: str) -> Optional[AtomicCard]:
        """
        Get a card by its name.
        """
        return self.cards.get(name)

    def __getitem__(self, item) -> Optional[AtomicCard]:
        return self.cards.get(item,None)

    def __hash__(self):
        """Use a sorted JSON string of the model for a stable hash."""
        json_repr = json.dumps(self.model_dump(), sort_keys=True)
        return hash(json_repr)

    def __eq__(self, other):
        """Compare two AtomicCard instances using their full JSON representation."""
        if not isinstance(other, AtomicCard):
            return False
        return json.dumps(self.model_dump(), sort_keys=True) == json.dumps(other.model_dump(), sort_keys=True)

    def __len__(self):
        return len(self.cards)

    def __iter__(self) -> List[AtomicCard]:
        return iter(self.cards.values())

