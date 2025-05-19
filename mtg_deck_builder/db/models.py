"""
Database models for Magic: The Gathering deck builder application.

Defines SQLAlchemy ORM models for cards, printings, sets, import logs, and inventory items.
"""

import re
from typing import Dict, List, Optional, TYPE_CHECKING, ClassVar, Any
from datetime import date, datetime

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

    Attributes:
        uid (str): Unique identifier for this card printing.
        card_name (str): Name of the card (foreign key to CardDB).
        artist (str, optional): Artist of the card.
        number (str, optional): Collector number in the set.
        set_code (str): Set code (foreign key to CardSetDB).
        card_type (str, optional): Type line of the card.
        rarity (str, optional): Rarity of the card.
        mana_cost (str, optional): Mana cost string.
        power (str, optional): Power value (for creatures).
        toughness (str, optional): Toughness value (for creatures).
        abilities (list, optional): List of keyword abilities.
        flavor_text (str, optional): Flavor text.
        text (str, optional): Rules text.
        colors (list, optional): Printed colors.
        color_identity (list, optional): Color identity for deck-building.
        legalities (dict, optional): Format legality info.
        rulings (list, optional): List of rulings.
        foreign_data (dict, optional): Foreign language data.
        card (CardDB): Relationship to CardDB.
        set (CardSetDB): Relationship to CardSetDB.
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

    Attributes:
        name (str): Name of the card (primary key).
        printings (list): List of CardPrintingDB objects for this card.
        newest_printing_uid (str, optional): UID of the newest printing.
        newest_printing_rel (CardPrintingDB, optional): Relationship to newest printing.
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
        if self.newest_printing_rel is not None:  # Check relationship first (populated by bootstrap)
            return self.newest_printing_rel

        if self._newest_printing_cache is not None:  # Then manual instance cache
            return self._newest_printing_cache

        if not self.printings:
            self._newest_printing_cache = None  # Ensure cache is None if no printings
            return None

        def get_safe_release_date(printing_obj: CardPrintingDB) -> date:
            set_obj = getattr(printing_obj, "set", None)
            if set_obj:
                release_date_val = getattr(set_obj, "release_date", None)
                if isinstance(release_date_val, date):
                    return release_date_val
                # Handle cases where release_date might be a string in data, though DB should store as Date
                if isinstance(release_date_val, str):
                    try:
                        return datetime.strptime(release_date_val, "%Y-%m-%d").date()
                    except ValueError:
                        pass  # Fall through to date.min if parsing fails
            # Fallback for comparison if no valid date found for this printing's set
            return date.min

        try:
            # Find the printing with the maximum (latest) release date.
            determined_newest_printing = max(self.printings, key=get_safe_release_date)
        except ValueError:
            # Should ideally not be reached if `if not self.printings:` is effective and list is not empty.
            # If self.printings is not empty but max still fails (e.g. all dates are date.min and max has issues with that),
            # this is a fallback. A more sophisticated tie-breaker might be needed if all dates are date.min.
            determined_newest_printing = self.printings[0] if self.printings else None

        self._newest_printing_cache = determined_newest_printing
        return determined_newest_printing

    @newest_printing.setter
    def newest_printing(self, value: Optional["CardPrintingDB"]):
        self._newest_printing_cache = value

    @property
    def type(self) -> Optional[str]:
        """
        Returns the card type from the newest printing.
        """
        np = self.newest_printing
        return getattr(np, "card_type", None) if np else None

    @property
    def rarity(self) -> Optional[str]:
        """
        Returns the rarity from the newest printing.
        """
        np = self.newest_printing
        return getattr(np, "rarity", None) if np else None

    @property
    def mana_cost(self) -> Optional[str]:
        """
        Returns the mana cost from the newest printing.
        """
        np = self.newest_printing
        return getattr(np, "mana_cost", None) if np else None

    @property
    def power(self) -> Optional[str]:
        """
        Returns the power from the newest printing.
        """
        np = self.newest_printing
        return getattr(np, "power", None) if np else None

    @property
    def toughness(self) -> Optional[str]:
        """
        Returns the toughness from the newest printing.
        """
        np = self.newest_printing
        return getattr(np, "toughness", None) if np else None

    @property
    def abilities(self) -> Optional[List[str]]:
        """
        Returns the list of abilities from the newest printing.
        """
        np = self.newest_printing
        abilities = getattr(np, "abilities", None) if np else None
        if abilities is None:
            return []
        if isinstance(abilities, list):
            return abilities
        return [str(abilities)]

    @property
    def flavor_text(self) -> Optional[str]:
        """
        Returns the flavor text from the newest printing.
        """
        np = self.newest_printing
        return getattr(np, "flavor_text", None) if np else None

    @property
    def text(self) -> Optional[str]:
        """
        Returns the rules text from the newest printing.
        """
        np = self.newest_printing
        return getattr(np, "text", None) if np else None

    @property
    def colors(self) -> Optional[List[str]]:
        """
        Returns the color identity (preferred) or printed colors from the newest printing.
        """
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
        """
        Returns the legality dictionary from the newest printing.
        """
        np = self.newest_printing
        legalities = getattr(np, "legalities", None) if np else None
        if legalities is None:
            return {}
        if isinstance(legalities, dict):
            return legalities
        return {}

    @property
    def rulings(self) -> Optional[List[str]]:
        """
        Returns the list of rulings from the newest printing.
        """
        np = self.newest_printing
        rulings = getattr(np, "rulings", None) if np else None
        if rulings is None:
            return []
        if isinstance(rulings, list):
            return rulings
        return [str(rulings)]

    @property
    def foreign_data(self) -> Optional[Dict]:
        """
        Returns the foreign language data from the newest printing.
        """
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

        Args:
            type_string (str): Type string to match (e.g., 'creature').
        Returns:
            bool: True if the card's type matches, False otherwise.
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

        Args:
            colors (List[str]): List of color codes to match (e.g., ['W', 'U']).
            match_mode (str): 'any', 'subset', or 'exact'.
        Returns:
            bool: True if the card matches the color identity criteria.
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

    Attributes:
        set_code (str): Set code (primary key).
        set_name (str): Name of the set.
        release_date (date, optional): Release date of the set.
        block (str, optional): Block name.
        set_metadata (dict): Additional metadata for the set.
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

    Attributes:
        json_path (str): Path to the imported JSON file (primary key).
        meta_date (datetime): Date from the file's meta section.
        mtime (float): File modification time.
    """
    __tablename__ = 'import_log'
    json_path: Mapped[str] = mapped_column(String, primary_key=True)
    meta_date: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    mtime: Mapped[Float] = mapped_column(Float, nullable=False)


class InventoryItemDB(Base):
    """
    Represents an inventory item for a card, tracking quantity and infinite status.

    Attributes:
        card_name (str): Name of the card (primary key).
        quantity (int): Number of copies owned.
        is_infinite (bool): If True, treat as infinite copies owned.
    """
    __tablename__ = "inventory_items"
    card_name: Mapped[str] = mapped_column(String, primary_key=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    is_infinite: Mapped[bool] = mapped_column(Boolean, default=False)

