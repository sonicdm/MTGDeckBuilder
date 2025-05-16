"""
Database models for Magic: The Gathering deck builder application.

Defines SQLAlchemy ORM models for cards, printings, sets, import logs, and inventory items.
"""

import re
from typing import Dict, List, Optional, TYPE_CHECKING, ClassVar, Any

from sqlalchemy import Column, String, Integer, Date, Text, JSON, Boolean, DateTime, Float, ForeignKey, event
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column

# Import CardPrintingDB for use in bootstrap and type hints
# (This is a forward declaration for type hints, actual class is defined below)

if TYPE_CHECKING:
    from mtg_deck_builder.db.repository import InventoryRepository

Base = declarative_base()


class CardPrintingDB(Base):
    """
    Represents a specific printing of a Magic: The Gathering card in a particular set.
    Stores detailed card data as it appears in that printing.
    """
    __tablename__ = "card_printings"
    uid: Mapped[str] = mapped_column(String, primary_key=True)
    card_name: Mapped[str] = mapped_column(String, ForeignKey("cards.name"))
    artist: Mapped[Optional[str]] = mapped_column(String)
    number: Mapped[Optional[str]] = mapped_column(String)
    set_code: Mapped[str] = mapped_column(String, ForeignKey("sets.set_code"))

    # Primary printing data
    card_type: Mapped[Optional[str]] = mapped_column(String)
    rarity: Mapped[Optional[str]] = mapped_column(String)
    mana_cost: Mapped[Optional[str]] = mapped_column(String)
    power: Mapped[Optional[str]] = mapped_column(String)
    toughness: Mapped[Optional[str]] = mapped_column(String)
    abilities: Mapped[Optional[List[str]]] = mapped_column(JSON)
    flavor_text: Mapped[Optional[str]] = mapped_column(Text)
    text: Mapped[Optional[str]] = mapped_column(Text)
    colors: Mapped[Optional[List[str]]] = mapped_column(JSON)
    color_identity: Mapped[Optional[List[str]]] = mapped_column(JSON)
    legalities: Mapped[Optional[Dict]] = mapped_column(JSON)
    rulings: Mapped[Optional[List[str]]] = mapped_column(JSON)
    foreign_data: Mapped[Optional[Dict]] = mapped_column(JSON)

    # Relationships
    card: Mapped["CardDB"] = relationship(
        "CardDB",
        back_populates="printings",
        foreign_keys=[card_name]
    )
    set: Mapped["CardSetDB"] = relationship("CardSetDB")

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<CardPrintingDB(name='{self.card_name}', set='{self.set_code}', uid='{self.uid}')>"

    def __str__(self) -> str:
        """Returns a human-readable string for the printing."""
        return f"{self.card_name} [{self.set_code}]"


class CardDB(Base):
    """
    Represents a unique Magic: The Gathering card (by name).
    Aggregates all printings of the card and provides properties to access the latest printing's data.
    """
    __tablename__ = "cards"
    __allow_unmapped__ = True  # Allow runtime-only attributes

    name: Mapped[str] = mapped_column(String, primary_key=True)
    # Track how many copies are owned (not persisted in DB, for runtime/deck use)
    owned_qty: ClassVar[int] = 0

    # Relationship to all printings of this card
    printings: Mapped[List["CardPrintingDB"]] = relationship(
        "CardPrintingDB",
        back_populates="card",
        foreign_keys="[CardPrintingDB.card_name]"
    )

    # Add newest_printing_uid and relationship
    newest_printing_uid: Mapped[Optional[str]] = mapped_column(String, ForeignKey("card_printings.uid"), nullable=True)
    newest_printing_rel: Mapped[Optional["CardPrintingDB"]] = relationship(
        "CardPrintingDB", foreign_keys=[newest_printing_uid], post_update=True, uselist=False
    )

    _newest_printing_cache: Optional["CardPrintingDB"] = None

    @property
    def newest_printing(self) -> Optional["CardPrintingDB"]:
        """
        Returns the most recent printing of the card, or None if no printings exist.
        Uses the cached DB relationship if available, otherwise falls back to calculation.
        """
        if self.newest_printing_rel is not None:
            return self.newest_printing_rel
        # fallback for legacy/uncached cards
        if self._newest_printing_cache is not None:
            return self._newest_printing_cache
        if not self.printings:
            return None
        try:
            np = max(
                self.printings,
                key=lambda p: getattr(getattr(p, "set", None), "release_date", None) or getattr(p, "release_date", None) or "",
                default=None
            )
        except Exception:
            np = self.printings[0] if self.printings else None
        self._newest_printing_cache = np
        return np

    @newest_printing.setter
    def newest_printing(self, value: Optional["CardPrintingDB"]):
        self._newest_printing_cache = value

    @property
    def type(self) -> Optional[str]:
        """Returns the card type from the newest printing."""
        np = self.newest_printing
        return getattr(np, "card_type", None) if np else None

    @property
    def rarity(self) -> Optional[str]:
        np = self.newest_printing
        return getattr(np, "rarity", None) if np else None

    @property
    def mana_cost(self) -> Optional[str]:
        np = self.newest_printing
        return getattr(np, "mana_cost", None) if np else None

    @property
    def power(self) -> Optional[str]:
        np = self.newest_printing
        return getattr(np, "power", None) if np else None

    @property
    def toughness(self) -> Optional[str]:
        np = self.newest_printing
        return getattr(np, "toughness", None) if np else None

    @property
    def abilities(self) -> Optional[List[str]]:
        np = self.newest_printing
        abilities = getattr(np, "abilities", None) if np else None
        if abilities is None:
            return []
        if isinstance(abilities, list):
            return abilities
        return [str(abilities)]

    @property
    def flavor_text(self) -> Optional[str]:
        np = self.newest_printing
        return getattr(np, "flavor_text", None) if np else None

    @property
    def text(self) -> Optional[str]:
        np = self.newest_printing
        return getattr(np, "text", None) if np else None

    @property
    def colors(self) -> Optional[List[str]]:
        np = self.newest_printing
        # Use color_identity for deck-building color filtering
        color_identity = getattr(np, "color_identity", None) if np else None
        if color_identity is not None:
            if isinstance(color_identity, list):
                return color_identity
            return [str(color_identity)]
        # Fallback to colors if color_identity is missing
        colors = getattr(np, "colors", None) if np else None
        if colors is None:
            return []
        if isinstance(colors, list):
            return colors
        return [str(colors)]

    @property
    def legalities(self) -> Optional[dict]:
        np = self.newest_printing
        legalities = getattr(np, "legalities", None) if np else None
        if legalities is None:
            return {}
        if isinstance(legalities, dict):
            return legalities
        return {}

    @property
    def rulings(self) -> Optional[List[str]]:
        np = self.newest_printing
        rulings = getattr(np, "rulings", None) if np else None
        if rulings is None:
            return []
        if isinstance(rulings, list):
            return rulings
        return [str(rulings)]

    @property
    def foreign_data(self) -> Optional[Dict]:
        np = self.newest_printing
        foreign_data = getattr(np, "foreign_data", None) if np else None
        if foreign_data is None:
            return {}
        if isinstance(foreign_data, dict):
            return foreign_data
        return {}

    @property
    def converted_mana_cost(self) -> int:
        """
        Calculates the converted mana cost (CMC) from the mana cost string.
        """
        mana_cost = self.mana_cost
        if not mana_cost:
            return 0
        import re
        converted_cost = 0
        for symbol in re.findall(r'\{[^\}]+\}', mana_cost):
            symbol = symbol[1:-1]
            try:
                if symbol.isdigit():
                    converted_cost += int(symbol)
                else:
                    converted_cost += 1
            except Exception:
                continue
        return converted_cost

    def matches_type(self, type_string: str) -> bool:
        """
        Checks if the card's type matches the given type string (case-insensitive).
        """
        t = self.type
        if not t or not type_string:
            return False
        return type_string.lower() in t.lower()

    def __repr__(self) -> str:
        return f"<CardDB(name='{self.name}')>"

    def __str__(self) -> str:
        return self.name

    def matches_color_identity(self, colors: List[str], match_mode: str = "subset") -> bool:
        """
        Checks if the card's color identity matches the given colors.
        match_mode can be 'any', 'subset', or 'exact'.

        - 'any': Card shares at least one color with the requested colors.
        - 'subset': All of the card's colors are in the requested colors (but not vice versa).
        - 'exact': Card's colors exactly match the requested colors.
        """
        if not colors:
            return True

        requested = set(colors)
        card_colors = set(self.colors or [])

        # Debug: log the card and its color identity for troubleshooting
        # import logging
        # logging.getLogger(__name__).debug(
        #     f"[ColorMatch] Card: {self.name}, Card Colors: {card_colors}, Requested: {requested}, Mode: {match_mode}"
        # )

        # Special handling for truly colorless cards (no colors, no mana cost)
        if not card_colors and not (self.mana_cost and any(c in self.mana_cost for c in "WUBRG")):
            return "C" in requested and (match_mode in ("subset", "exact"))

        # If the card is colorless but has a mana cost (e.g., Eldrazi with {10}), treat as colorless
        if not card_colors and self.mana_cost:
            return "C" in requested and (match_mode in ("subset", "exact"))

        requested.discard("C")

        if match_mode == "any":
            return bool(card_colors & requested)
        elif match_mode == "subset":
            # All card colors must be in requested, and card must have at least one color
            return bool(card_colors) and card_colors.issubset(requested)
        elif match_mode == "exact":
            return card_colors == requested

        raise ValueError(f"Invalid match_mode '{match_mode}'")

    def is_basic_land(self) -> bool:
        """
        Returns True if the card is a basic land.
        """
        t = self.type
        return t is not None and "basic" in t.lower()

    def get_preferred_printing(self) -> Optional[CardPrintingDB]:
        """
        Returns the preferred printing for this card (currently the newest printing).
        """
        return self.newest_printing


# Invalidate newest_printing cache when printings relationship changes
@event.listens_for(CardDB.printings, "append")
@event.listens_for(CardDB.printings, "remove")
@event.listens_for(CardDB.printings, "set")
def _invalidate_newest_printing_cache(card, *args, **kwargs):
    card._newest_printing_cache = None


class CardSetDB(Base):
    """
    Represents a Magic: The Gathering set (expansion, core set, etc.).
    """
    __tablename__ = "sets"
    set_code: Mapped[str] = mapped_column(String, primary_key=True)
    set_name: Mapped[str] = mapped_column(String)
    release_date: Mapped[Optional[Date]] = mapped_column(Date)
    block: Mapped[Optional[str]] = mapped_column(String)
    set_metadata: Mapped[Dict] = mapped_column("metadata", JSON)


class ImportLog(Base):
    """
    Tracks import operations for card data files.
    Stores file path, import date, and modification time.
    """
    __tablename__ = 'import_log'
    json_path: Mapped[str] = mapped_column(String, primary_key=True)
    meta_date: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    mtime: Mapped[float] = mapped_column(Float, nullable=False)


class InventoryItemDB(Base):
    """
    Represents an inventory item for a card, tracking quantity and infinite status.
    """
    __tablename__ = "inventory_items"
    card_name: Mapped[str] = mapped_column(String, primary_key=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    is_infinite: Mapped[bool] = mapped_column(Boolean, default=False)

