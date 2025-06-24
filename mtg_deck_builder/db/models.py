"""
Database models for Magic: The Gathering deck builder application.

Defines SQLAlchemy ORM models:
Cards, printings, sets, import logs, and inventory items.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, TYPE_CHECKING, Any, Union
from datetime import date
from sqlalchemy import (
    String,
    Integer,
    Date,
    Text,
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    event,
)
from sqlalchemy.orm import (
    declarative_base,
    relationship,
    Mapped,
    mapped_column
)
from sqlalchemy.exc import InvalidRequestError as DetachedInstanceError
from mtg_deck_builder.models.card_meta import CardTypesData, KeywordsData, load_card_types, load_keywords
# from mtg_deckbuilder_ui.app_config import app_config

if TYPE_CHECKING:
    # from mtg_deck_builder.db.repository import CardRepository, InventoryRepository
    pass

Base = declarative_base()

class CardPrintingDB(Base):
    """Database model for card printings."""

    __tablename__ = "card_printings"

    # Primary key and foreign keys
    id: Mapped[int] = mapped_column(primary_key=True)
    card_name: Mapped[str] = mapped_column(String, ForeignKey("cards.name"))
    set_code: Mapped[str] = mapped_column(String, ForeignKey("sets.code"))

    # Required fields from MTGJSON spec
    availability: Mapped[List[str]] = mapped_column(JSON)
    border_color: Mapped[str] = mapped_column(String)
    color_identity: Mapped[List[str]] = mapped_column(JSON)
    colors: Mapped[List[str]] = mapped_column(JSON)
    converted_mana_cost: Mapped[float] = mapped_column(Float)
    finishes: Mapped[List[str]] = mapped_column(JSON)
    frame_version: Mapped[str] = mapped_column(String)
    has_foil: Mapped[bool] = mapped_column(Boolean)
    has_non_foil: Mapped[bool] = mapped_column(Boolean)
    identifiers: Mapped[dict] = mapped_column(JSON)
    language: Mapped[str] = mapped_column(String)
    layout: Mapped[str] = mapped_column(String)
    legalities: Mapped[dict] = mapped_column(JSON)
    mana_value: Mapped[float] = mapped_column(Float)
    name: Mapped[str] = mapped_column(String)
    number: Mapped[str] = mapped_column(String)
    purchase_urls: Mapped[dict] = mapped_column(JSON)
    rarity: Mapped[str] = mapped_column(String)
    subtypes: Mapped[List[str]] = mapped_column(JSON)
    supertypes: Mapped[List[str]] = mapped_column(JSON)
    type: Mapped[str] = mapped_column(String)
    types: Mapped[List[str]] = mapped_column(JSON)
    uuid: Mapped[str] = mapped_column(String)

    # Optional fields from MTGJSON spec
    artist: Mapped[Optional[str]] = mapped_column(String)
    artist_ids: Mapped[Optional[List[str]]] = mapped_column(JSON)
    ascii_name: Mapped[Optional[str]] = mapped_column(String)
    attraction_lights: Mapped[Optional[List[int]]] = mapped_column(JSON)
    booster_types: Mapped[Optional[List[str]]] = mapped_column(JSON)
    card_parts: Mapped[Optional[List[str]]] = mapped_column(JSON)
    color_indicator: Mapped[Optional[List[str]]] = mapped_column(JSON)
    defense: Mapped[Optional[str]] = mapped_column(String)
    duel_deck: Mapped[Optional[str]] = mapped_column(String)
    edhrec_rank: Mapped[Optional[float]] = mapped_column(Float)
    edhrec_saltiness: Mapped[Optional[float]] = mapped_column(Float)
    face_converted_mana_cost: Mapped[Optional[float]] = mapped_column(Float)
    face_flavor_name: Mapped[Optional[str]] = mapped_column(String)
    face_mana_value: Mapped[Optional[float]] = mapped_column(Float)
    face_name: Mapped[Optional[str]] = mapped_column(String)
    flavor_name: Mapped[Optional[str]] = mapped_column(String)
    flavor_text: Mapped[Optional[str]] = mapped_column(Text)
    foreign_data: Mapped[Optional[List[dict]]] = mapped_column(JSON)
    frame_effects: Mapped[Optional[List[str]]] = mapped_column(JSON)
    hand: Mapped[Optional[str]] = mapped_column(String)
    has_alternative_deck_limit: Mapped[Optional[bool]] = mapped_column(Boolean)
    has_content_warning: Mapped[Optional[bool]] = mapped_column(Boolean)
    is_alternative: Mapped[Optional[bool]] = mapped_column(Boolean)
    is_full_art: Mapped[Optional[bool]] = mapped_column(Boolean)
    is_funny: Mapped[Optional[bool]] = mapped_column(Boolean)
    is_online_only: Mapped[Optional[bool]] = mapped_column(Boolean)
    is_oversized: Mapped[Optional[bool]] = mapped_column(Boolean)
    is_promo: Mapped[Optional[bool]] = mapped_column(Boolean)
    is_rebalanced: Mapped[Optional[bool]] = mapped_column(Boolean)
    is_reprint: Mapped[Optional[bool]] = mapped_column(Boolean)
    is_reserved: Mapped[Optional[bool]] = mapped_column(Boolean)
    is_starter: Mapped[Optional[bool]] = mapped_column(Boolean)
    is_story_spotlight: Mapped[Optional[bool]] = mapped_column(Boolean)
    is_textless: Mapped[Optional[bool]] = mapped_column(Boolean)
    is_timeshifted: Mapped[Optional[bool]] = mapped_column(Boolean)
    keywords: Mapped[Optional[List[str]]] = mapped_column(JSON)
    leadership_skills: Mapped[Optional[dict]] = mapped_column(JSON)
    life: Mapped[Optional[str]] = mapped_column(String)
    loyalty: Mapped[Optional[str]] = mapped_column(String)
    mana_cost: Mapped[Optional[str]] = mapped_column(String)
    original_printings: Mapped[Optional[List[str]]] = mapped_column(JSON)
    original_release_date: Mapped[Optional[str]] = mapped_column(String)
    original_text: Mapped[Optional[str]] = mapped_column(Text)
    original_type: Mapped[Optional[str]] = mapped_column(String)
    other_face_ids: Mapped[Optional[List[str]]] = mapped_column(JSON)
    power: Mapped[Optional[str]] = mapped_column(String)
    printings: Mapped[Optional[List[str]]] = mapped_column(JSON)
    promo_types: Mapped[Optional[List[str]]] = mapped_column(JSON)
    related_cards: Mapped[Optional[dict]] = mapped_column(JSON)
    rebalanced_printings: Mapped[Optional[List[str]]] = mapped_column(JSON)
    rulings: Mapped[Optional[List[dict]]] = mapped_column(JSON)
    security_stamp: Mapped[Optional[str]] = mapped_column(String)
    side: Mapped[Optional[str]] = mapped_column(String)
    signature: Mapped[Optional[str]] = mapped_column(String)
    source_products: Mapped[Optional[dict]] = mapped_column(JSON)
    subsets: Mapped[Optional[List[str]]] = mapped_column(JSON)
    text: Mapped[Optional[str]] = mapped_column(Text)
    toughness: Mapped[Optional[str]] = mapped_column(String)
    variations: Mapped[Optional[List[str]]] = mapped_column(JSON)
    watermark: Mapped[Optional[str]] = mapped_column(String)

    # Relationships
    card: Mapped["CardDB"] = relationship(
        "CardDB",
        back_populates="printings",
        foreign_keys=[card_name]
    )
    set: Mapped["CardSetDB"] = relationship(
        "CardSetDB",
        back_populates="printings",
        foreign_keys=[set_code]
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<CardPrintingDB(id='{self.id}', "
            f"name='{self.name}', set='{self.set_code}')>"
        )

    def __str__(self) -> str:
        """Returns a human-readable string for the printing."""
        return f"{self.name} [{self.set_code}]"

    def to_dict(self) -> Dict[str, Any]:
        """Convert printing to dictionary representation."""
        return {
            'id': self.id,
            'card_name': self.card_name,
            'set_code': self.set_code,
            'name': self.name,
            'number': self.number,
            'availability': self.availability,
            'border_color': self.border_color,
            'color_identity': self.color_identity,
            'colors': self.colors,
            'converted_mana_cost': self.converted_mana_cost,
            'finishes': self.finishes,
            'frame_version': self.frame_version,
            'has_foil': self.has_foil,
            'has_non_foil': self.has_non_foil,
            'identifiers': self.identifiers,
            'language': self.language,
            'layout': self.layout,
            'legalities': self.legalities,
            'mana_value': self.mana_value,
            'purchase_urls': self.purchase_urls,
            'rarity': self.rarity,
            'subtypes': self.subtypes,
            'supertypes': self.supertypes,
            'type': self.type,
            'types': self.types,
            'uuid': self.uuid,
            'artist': self.artist,
            'artist_ids': self.artist_ids,
            'ascii_name': self.ascii_name,
            'attraction_lights': self.attraction_lights,
            'booster_types': self.booster_types,
            'card_parts': self.card_parts,
            'color_indicator': self.color_indicator,
            'defense': self.defense,
            'duel_deck': self.duel_deck,
            'edhrec_rank': self.edhrec_rank,
            'edhrec_saltiness': self.edhrec_saltiness,
            'face_converted_mana_cost': self.face_converted_mana_cost,
            'face_flavor_name': self.face_flavor_name,
            'face_mana_value': self.face_mana_value,
            'face_name': self.face_name,
            'flavor_name': self.flavor_name,
            'flavor_text': self.flavor_text,
            'foreign_data': self.foreign_data,
            'frame_effects': self.frame_effects,
            'hand': self.hand,
            'has_alternative_deck_limit': self.has_alternative_deck_limit,
            'has_content_warning': self.has_content_warning,
            'is_alternative': self.is_alternative,
            'is_full_art': self.is_full_art,
            'is_funny': self.is_funny,
            'is_online_only': self.is_online_only,
            'is_oversized': self.is_oversized,
            'is_promo': self.is_promo,
            'is_rebalanced': self.is_rebalanced,
            'is_reprint': self.is_reprint,
            'is_reserved': self.is_reserved,
            'is_starter': self.is_starter,
            'is_story_spotlight': self.is_story_spotlight,
            'is_textless': self.is_textless,
            'is_timeshifted': self.is_timeshifted,
            'keywords': self.keywords,
            'leadership_skills': self.leadership_skills,
            'life': self.life,
            'loyalty': self.loyalty,
            'mana_cost': self.mana_cost,
            'original_printings': self.original_printings,
            'original_release_date': self.original_release_date,
            'original_text': self.original_text,
            'original_type': self.original_type,
            'other_face_ids': self.other_face_ids,
            'power': self.power,
            'printings': self.printings,
            'promo_types': self.promo_types,
            'related_cards': self.related_cards,
            'rebalanced_printings': self.rebalanced_printings,
            'rulings': self.rulings,
            'security_stamp': self.security_stamp,
            'side': self.side,
            'signature': self.signature,
            'source_products': self.source_products,
            'subsets': self.subsets,
            'text': self.text,
            'toughness': self.toughness,
            'variations': self.variations,
            'watermark': self.watermark
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], session) -> 'CardPrintingDB':
        """Create a CardPrintingDB instance from a dictionary."""
        printing = cls()
        for key, value in data.items():
            if hasattr(printing, key):
                setattr(printing, key, value)
        return printing

    @property
    def types(self) -> Optional[list[str]]:
        """
        Returns a list of types parsed from the card_type string.
        E.g., 'Creature — Human Wizard' -> ['Creature']
        """
        if self.type:
            # Split on em dash or hyphen, take the left part, split by space
            return [t.strip() for t in self.type.split('—')[0].split('-')[0].split()]
        return []

    @property
    def subtypes(self) -> Optional[list[str]]:
        """
        Returns a list of subtypes parsed from the card_type string.
        E.g., 'Creature — Human Wizard' -> ['Human', 'Wizard']
        """
        if self.type and '—' in self.type:
            return [s.strip() for s in self.type.split('—')[1].split()]
        return []

    @property
    def supertypes(self) -> Optional[list[str]]:
        """
        Returns a list of supertypes parsed from the card_type string.
        E.g., 'Basic Land — Forest' -> ['Basic']
        """
        if self.type:
            known_supertypes = {"Basic", "Legendary", "Snow", "World", "Ongoing"}
            return [t for t in self.type.split() if t in known_supertypes]
        return []

class CardDB(Base):
    """
    Represents a unique Magic: The Gathering card (by name).
    Aggregates all printings of the card and provides properties to access the latest printing's data.
    """
    __tablename__ = "cards"
    __allow_unmapped__ = True  # Allow runtime-only attributes

    card_name: Mapped[str] = mapped_column("name", primary_key=True)
    
    # Ensure these attributes always exist
    _card_types: Optional[CardTypesData] = None
    _keywords: Optional[KeywordsData] = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._owned_qty: int = 0
        self._card_types: Optional[CardTypesData] = None
        self._keywords: Optional[KeywordsData] = None

    # Relationships
    printings: Mapped[List["CardPrintingDB"]] = relationship(
        "CardPrintingDB",
        back_populates="card",
        foreign_keys="[CardPrintingDB.card_name]"
    )

    newest_printing_uid: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("card_printings.uuid"), nullable=True
    )
    newest_printing_rel: Mapped[Optional["CardPrintingDB"]] = relationship(
        "CardPrintingDB",
        foreign_keys=[newest_printing_uid],
        post_update=True,
        uselist=False,
        lazy="joined",
        innerjoin=True,
    )

    _newest_printing_cache: Optional["CardPrintingDB"] = None

    @property
    def card_types(self) -> CardTypesData:
        """Lazily load card types data."""
        if self._card_types is None:
            self._card_types = load_card_types(app_config.get_path("cardtypes"))
        return self._card_types

    @property
    def keywords(self) -> KeywordsData:
        """Lazily load keywords data."""
        if self._keywords is None:
            self._keywords = load_keywords(app_config.get_path("keywords"))
        return self._keywords

    @property
    def name(self) -> str:
        return self.card_name

    @name.setter
    def name(self, value: str) -> None:
        self.card_name = value

    @property
    def release_date(self) -> Optional[date]:
        """Return the release date of the newest printing's set."""
        np = self.newest_printing_rel
        if np and np.set and np.set.release_date:
            return np.set.release_date
        return None

    @property
    def newest_printing(self) -> Optional["CardPrintingDB"]:
        """
        Returns the most recent printing of the card,
        or None if no printings exist.
        Uses the cached DB relationship if available,
        otherwise falls back to calculation.
        """
        if self.newest_printing_rel is not None:
            return self.newest_printing_rel

        if self._newest_printing_cache is not None:
            return self._newest_printing_cache

        if not self.printings:
            self._newest_printing_cache = None
            return None

        def get_safe_release_date(printing_obj: CardPrintingDB) -> date:
            if printing_obj.set and printing_obj.set.release_date:
                return printing_obj.set.release_date
            return date.min

        determined_newest_printing = max(
            self.printings, key=get_safe_release_date
        )
        self._newest_printing_cache = determined_newest_printing
        return determined_newest_printing

    @newest_printing.setter
    def newest_printing(self, value: Optional["CardPrintingDB"]) -> None:
        self._newest_printing_cache = value

    @property
    def type(self) -> Optional[str]:
        """Returns the card type from the newest printing."""
        np = self.newest_printing
        return np.type if np else None

    @property
    def types(self) -> Optional[List[str]]:
        """Returns the basic card types from the newest printing."""
        np = self.newest_printing
        return np.types if np else None

    @property
    def basic_type(self) -> Optional[str]:
        """Returns the basic card type from the newest printing."""
        np = self.newest_printing
        if not np or not np.types:
            return None

        # Get the basic types from CardTypes.json
        basic_types = self.card_types.data.keys()

        # Look for first matching basic type in card's types
        for card_type in np.types:
            if card_type.lower() in (t.lower() for t in basic_types):
                return card_type

        return None

    @property
    def subtype(self) -> Optional[str]:
        """Returns the subtype from the newest printing."""
        np = self.newest_printing
        if not np or not np.types:
            return None
        # Get the basic type of the card
        basic_type = self.basic_type
        if not basic_type or not np.subtypes:
            return None
        # Get valid subtypes for this card type from CARD_TYPES
        valid_subtypes = self.card_types.data.get(
            basic_type.lower(), {}
            ).get("subTypes", [])

        # Filter subtypes to only include valid ones
        card_subtypes = [
            subtype for subtype in np.subtypes if subtype in valid_subtypes
        ]
        return " ".join(card_subtypes) if card_subtypes else None

    @property
    def supertype(self) -> Optional[str]:
        """Returns the supertype from the newest printing."""
        np = self.newest_printing
        if not np or not np.types:
            return None

        # Get the basic type of the card
        basic_type = self.basic_type
        if not basic_type or not np.supertypes:
            return None

        # Get valid supertypes for this card type from CARD_TYPES
        valid_supertypes = self.card_types.data.get(basic_type.lower(), {}).get(
            "superTypes", []
        )

        # Filter supertypes to only include valid ones
        card_supertypes = [
            st
            for st in np.supertypes
            if st in valid_supertypes
        ]

        return " ".join(card_supertypes) if card_supertypes else None

    @property
    def rarity(self) -> Optional[str]:
        """Returns the rarity from the newest printing."""
        np = self.newest_printing
        return np.rarity if np else None

    @property
    def mana_cost(self) -> Optional[str]:
        """Returns the mana cost from the newest printing."""
        np = self.newest_printing
        return np.mana_cost if np else None

    @property
    def power(self) -> Optional[str]:
        """Returns the power from the newest printing."""
        np = self.newest_printing
        return np.power if np else None

    @property
    def toughness(self) -> Optional[str]:
        """Returns the toughness from the newest printing."""
        np = self.newest_printing
        return np.toughness if np else None

    def get_abilities(self, ability_keywords: List[str] = []) -> List[str]:
        """
        Return a list of abilities from the newest printing that match the
        given keywords.

        Args:
            ability_keywords (List[str]): List of ability keywords to filter
                by (case-insensitive).

        Returns:
            List[str]: List of matching abilities. If no keywords are
                provided, returns an empty list.
        """
        output = []
        ability_keywords = [keyword.lower() for keyword in ability_keywords]
        np = self.newest_printing
        if np and np.keywords:
            for keyword in np.keywords:
                if keyword.lower() in ability_keywords:
                    output.append(keyword)
        return output

    @property
    def flavor_text(self) -> Optional[str]:
        """Returns the flavor text from the newest printing."""
        np = self.newest_printing
        return np.flavor_text if np else None

    @property
    def text(self) -> str:
        """Returns the text from the newest printing."""
        np = self.newest_printing
        return np.text if np else ""

    @property
    def colors(self) -> List[str]:
        """
        Returns the color identity (preferred) or printed colors from the
        newest printing.
        """
        np = self.newest_printing
        if not np:
            return []
        # Use color_identity for deck-building color filtering
        if np.color_identity:
            if isinstance(np.color_identity, list):
                return np.color_identity
            return [str(np.color_identity)]
        # Fallback to colors if color_identity is missing
        if np.colors:
            if isinstance(np.colors, list):
                return np.colors
            return [str(np.colors)]
        return []

    @property
    def legalities(self) -> Dict[str, str]:
        """Returns the legality dictionary from the newest printing."""
        np = self.newest_printing
        if not np or not np.legalities:
            return {}
        if isinstance(np.legalities, dict):
            return np.legalities
        return {}

    @property
    def rulings(self) -> List[str]:
        """Returns the list of rulings from the newest printing."""
        np = self.newest_printing
        if not np or not np.rulings:
            return []
        if isinstance(np.rulings, list):
            return np.rulings
        return [str(np.rulings)]

    @property
    def foreign_data(self) -> Dict[str, Any]:
        """Returns the foreign language data from the newest printing."""
        np = self.newest_printing
        if not np or not np.foreign_data:
            return {}
        if isinstance(np.foreign_data, dict):
            return np.foreign_data
        return {}

    @property
    def converted_mana_cost(self) -> int:
        """
        Calculates the converted mana cost (CMC) from the mana cost string.
        """
        try:
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
        except Exception:
            return 0

    @property
    def color_identity(self) -> Optional[List[str]]:
        """Returns the color identity from the newest printing."""
        np = self.newest_printing
        return np.color_identity if np else None

    def matches_type(self, type_string: str) -> bool:
        """
        Checks if the card's type matches the given type string
        (case-insensitive).

        Args:
            type_string (str): Type string to match (e.g., 'creature').

        Returns:
            bool: True if the card's type matches, False otherwise.
        """
        t = self.type
        if not t or not type_string:
            return False
        return type_string.lower() in t.lower()

    @property
    def abilities(self) -> Optional[str]:
        """Returns the basic type from the newest printing."""
        np = self.newest_printing
        return np.basic_type if np else None

    def __repr__(self) -> str:
        # Show name, type, colors, rarity, CMC, and owned_qty for debugging
        return (
            f"<CardDB(name='{self.name}', "
            f"type='{self.type}', "
            f"colors={self.colors}, "
            f"rarity='{self.rarity}', "
            f"cmc={self.converted_mana_cost}, "
            f"owned_qty={self.owned_qty})>"
        )

    def __str__(self) -> str:
        return self.name

    def matches_color_identity(
        self, colors: List[str], match_mode: str = "subset"
    ) -> bool:
        """
        Checks if the card's color identity matches the given colors.

        Args:
            colors (List[str]): List of color codes to match (e.g.,
                ['W', 'U']).
            match_mode (str): 'any', 'subset', or 'exact'.

        Returns:
            bool: True if the card matches the color identity criteria.
        """
        if not colors:
            return True
        requested = set(colors)
        card_colors = set(self.colors or [])
        # Special handling for truly colorless cards (no colors, no mana cost)
        if not card_colors and not (
            self.mana_cost and any(c in self.mana_cost for c in "WUBRG")
        ):
            return "C" in requested and (match_mode in ("subset", "exact"))
        # If the card is colorless but has a mana cost
        # treat as colorless
        if not card_colors and self.mana_cost:
            return "C" in requested and (match_mode in ("subset", "exact"))
        # For exact mode, we need to handle colorless cards specially
        if match_mode == "exact":
            # If the card is colorless, it should only match if 'C' is in the
            # requested colors
            if not card_colors:
                return "C" in requested and len(requested) == 1
            # For colored cards, they must match exactly
            return card_colors == requested
        # For other modes, remove 'C' from requested colors
        requested.discard("C")
        if match_mode == "any":
            return bool(card_colors & requested)
        elif match_mode == "subset":
            # All card colors must be in requested, and card must have at least
            # one color
            return bool(card_colors) and card_colors.issubset(requested)
        raise ValueError(f"Invalid match_mode '{match_mode}'")

    def is_basic_land(self) -> bool:
        """Returns True if the card is a basic land."""
        t = self.type
        return t is not None and "basic" in t.lower()

    def get_preferred_printing(self) -> Optional[CardPrintingDB]:
        """
        Returns the preferred printing for this card (currently the newest
        printing).
        """
        return self.newest_printing

    @property
    def owned_qty(self) -> int:
        """Returns the number of copies owned."""
        # First check if owned_qty is manually set
        if hasattr(self, '_owned_qty'):
            return self._owned_qty
        # If you have a relationship set up, use it:
        if hasattr(self, 'inventory_items') and self.inventory_items:
            return sum(item.quantity for item in self.inventory_items)
        # Otherwise, fallback to a direct query (requires session context)
        from mtg_deck_builder.db.models import InventoryItemDB
        from sqlalchemy.orm import object_session
        session = object_session(self)
        if session:
            item = session.query(InventoryItemDB).filter_by(
                card_name=self.card_name
            ).first()
            return item.quantity if item else 0
        return 0

    @owned_qty.setter
    def owned_qty(self, value: int) -> None:
        self._owned_qty = value

    def _eager_load_relationships(self):
        """
        Eagerly load relationships to avoid lazy loading issues.
        """
        try:
            if (
                hasattr(self, 'newest_printing_rel') and
                self.newest_printing_rel is not None
            ):
                _ = self.newest_printing_rel.card_type
                _ = self.newest_printing_rel.colors
                _ = self.newest_printing_rel.rarity
                _ = self.newest_printing_rel.mana_cost
                _ = self.newest_printing_rel.power
                _ = self.newest_printing_rel.toughness
                _ = self.newest_printing_rel.text
                _ = self.newest_printing_rel.abilities
                _ = self.newest_printing_rel.legalities
                _ = self.newest_printing_rel.rulings
                _ = self.newest_printing_rel.foreign_data
                if hasattr(self.newest_printing_rel, 'set'):
                    _ = self.newest_printing_rel.set
        except DetachedInstanceError:
            # If we're detached, just skip eager loading
            pass

    def to_dict(self, eager: bool = False) -> Dict[str, Any]:
        if eager:
            self._eager_load_relationships()
        # ... existing serialization logic ...
        return {
            'card_name': self.card_name,  # Primary key
            'name': self.name,
            'type': self.type,
            'types': self.types,
            'basic_type': self.basic_type,
            'subtypes': self.subtypes,
            'subtype': self.subtype,
            'supertypes': self.supertypes,
            'supertype': self.supertype,
            'mana_cost': self.mana_cost,
            'colors': self.colors,
            'color_identity': self.color_identity,
            'rarity': self.rarity,
            'power': self.power,
            'toughness': self.toughness,
            'text': self.text,
            'abilities': self.get_abilities(),
            'converted_mana_cost': self.converted_mana_cost,
            'legalities': self.legalities,
            'rulings': self.rulings,
            'foreign_data': self.foreign_data,
            'owned_qty': self.owned_qty,
            'newest_printing_uid': self.newest_printing_uid,
            'release_date': (
                self.release_date.isoformat() if self.release_date else None
            )
        }

    @classmethod
    def from_dict(cls, card_dict: Dict[str, Any], session) -> 'CardDB':
        """Create a CardDB instance from a dictionary.
        Args:
            card_dict (Dict[str, Any]): Dictionary containing card data
            session: SQLAlchemy session for database operations
        Returns:
            CardDB: A new CardDB instance with the data from the dictionary
        """
        # First try to get existing card from database
        card = session.query(cls).get(card_dict['card_name'])
        if not card:
            # If card doesn't exist, create new instance
            card = cls()
            card.card_name = card_dict['card_name']
            card.name = card_dict['name']

        # Set newest printing if available
        if card_dict.get('newest_printing_uid'):
            card.newest_printing_uid = card_dict['newest_printing_uid']

        # Set owned quantity
        if 'owned_qty' in card_dict:
            card._owned_qty = card_dict['owned_qty']

        return card


# Invalidate newest_printing cache when printings relationship changes
@event.listens_for(CardDB.printings, "append")
@event.listens_for(CardDB.printings, "remove")
@event.listens_for(CardDB.printings, "set")
def _invalidate_newest_printing_cache(card: CardDB, *args, **kwargs) -> None:
    """Invalidate the newest printing cache when printings relationship changes."""
    card._newest_printing_cache = None


class CardSetDB(Base):
    """Database model for card sets."""

    __tablename__ = "sets"

    # Primary key
    code: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    release_date: Mapped[Optional[date]] = mapped_column(Date)
    block: Mapped[Optional[str]] = mapped_column(String)
    set_metadata: Mapped[dict] = mapped_column(JSON)

    # Relationships
    printings: Mapped[List["CardPrintingDB"]] = relationship(
        "CardPrintingDB",
        back_populates="set",
        foreign_keys="[CardPrintingDB.set_code]"
    )

    def __repr__(self) -> str:
        return f"<CardSetDB(code='{self.code}', name='{self.name}')>"

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"

class ImportLog(Base):
    """
    Tracks import operations for card data files.
    """
    __tablename__ = 'import_log'
    
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    json_path: Mapped[str] = mapped_column(
        String, nullable=False, index=True, unique=True
    )
    meta_date: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    mtime: Mapped[Float] = mapped_column(Float, nullable=False)

    def __repr__(self) -> str:
        return f"<ImportLog(path='{self.json_path}', date='{self.meta_date}')>"

class InventoryItemDB(Base):
    """
    Represents an inventory item for a card, tracking quantity.
    """
    __tablename__ = "inventory_items"
    
    card_name: Mapped[str] = mapped_column(String, primary_key=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)

    def __repr__(self) -> str:
        return f"<InventoryItemDB(card='{self.card_name}', qty={self.quantity})>"


