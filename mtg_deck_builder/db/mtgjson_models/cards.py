from sqlalchemy import Column, String, Integer, Float, Text, Boolean, ForeignKey, ForeignKeyConstraint, JSON, Date
from sqlalchemy.orm import relationship, foreign, Mapped, mapped_column

from mtg_deck_builder.db import get_session
from .base import MTGJSONBase
from .sets import MTGJSONSet
import ast
from typing import List, Optional, Dict, Any, Union, cast
from sqlalchemy.ext.declarative import declared_attr
import json
from mtg_deck_builder.db.models import InventoryItemDB
from mtg_deck_builder.db.mtgjson_models.inventory import InventoryItem
from mtg_deck_builder.models.card import SummaryCard, InventoryItem

class MTGJSONCard(MTGJSONBase):
    __tablename__ = "cards"

    uuid = Column(String(36), primary_key=True)
    name = Column(Text, ForeignKey('summary_cards.name'))
    setCode = Column(String(8), ForeignKey('sets.code'))
    artist = Column(Text)
    artistIds = Column(Text)  # List of artist IDs
    asciiName = Column(Text)
    attractionLights = Column(Text)  # List of attraction lights
    availability = Column(Text)  # List of availability types
    boosterTypes = Column(Text)  # List of booster types
    borderColor = Column(Text)
    cardParts = Column(Text)  # List of card parts
    colorIdentity = Column(Text)  # List of colors, stored as text (may be JSON or CSV or empty)
    colorIndicator = Column(Text)  # List of colors
    colors = Column(Text)  # List of colors, stored as text (may be JSON or CSV or empty)
    defense = Column(Text)
    duelDeck = Column(Text)
    edhrecRank = Column(Integer)
    edhrecSaltiness = Column(Float)
    faceConvertedManaCost = Column(Float)
    faceFlavorName = Column(Text)
    faceManaValue = Column(Float)
    faceName = Column(Text)
    finishes = Column(Text)  # List of finishes
    flavorName = Column(Text)
    flavorText = Column(Text)
    frameEffects = Column(Text)  # List of frame effects
    frameVersion = Column(Text)
    hand = Column(Text)
    hasAlternativeDeckLimit = Column(Boolean)
    hasContentWarning = Column(Boolean)
    hasFoil = Column(Boolean)
    hasNonFoil = Column(Boolean)
    isAlternative = Column(Boolean)
    isFullArt = Column(Boolean)
    isFunny = Column(Boolean)
    isGameChanger = Column(Boolean)
    isOnlineOnly = Column(Boolean)
    isOversized = Column(Boolean)
    isPromo = Column(Boolean)
    isRebalanced = Column(Boolean)
    isReprint = Column(Boolean)
    isReserved = Column(Boolean)
    isStarter = Column(Boolean)
    isStorySpotlight = Column(Boolean)
    isTextless = Column(Boolean)
    isTimeshifted = Column(Boolean)
    keywords = Column(Text)  # List of keywords, stored as text
    language = Column(Text)
    layout = Column(Text)
    leadershipSkills = Column(Text)  # Dictionary of leadership skills
    life = Column(Text)
    loyalty = Column(Text)
    manaCost = Column(Text)
    manaValue = Column(Float)
    number = Column(Text)
    originalPrintings = Column(Text)  # List of original printings
    originalReleaseDate = Column(Text)
    originalText = Column(Text)
    originalType = Column(Text)
    otherFaceIds = Column(Text)  # List of other face IDs
    power = Column(Text)
    printings = Column(Text)  # List of printings
    promoTypes = Column(Text)  # List of promo types
    rarity = Column(Text)
    rebalancedPrintings = Column(Text)  # List of rebalanced printings
    relatedCards = Column(Text)  # List of related cards
    securityStamp = Column(Text)
    side = Column(Text)
    signature = Column(Text)
    sourceProducts = Column(Text)  # List of source products
    subsets = Column(Text)  # List of subsets
    supertypes = Column(Text)  # List of supertypes, stored as text
    subtypes = Column(Text)  # List of subtypes, stored as text
    text = Column(Text)
    toughness = Column(Text)
    type = Column(Text)
    types = Column(Text)  # List of types
    variations = Column(Text)  # List of variations
    watermark = Column(Text)

    # Relationships
    set = relationship(
        "MTGJSONSet",
        primaryjoin="foreign(MTGJSONCard.setCode)==MTGJSONSet.code",
        back_populates="cards"
    )
    legalities = relationship(
        "MTGJSONCardLegality",
        primaryjoin="MTGJSONCard.uuid==foreign(MTGJSONCardLegality.uuid)",
        uselist=False
    )
    identifiers = relationship(
        "MTGJSONCardIdentifier",
        primaryjoin="MTGJSONCard.uuid==foreign(MTGJSONCardIdentifier.uuid)",
        uselist=False
    )
    purchase_urls = relationship(
        "MTGJSONCardPurchaseUrl",
        primaryjoin="MTGJSONCard.uuid==foreign(MTGJSONCardPurchaseUrl.uuid)",
        uselist=False
    )
    rulings = relationship(
        "MTGJSONCardRuling",
        primaryjoin="MTGJSONCard.uuid==foreign(MTGJSONCardRuling.uuid)"
    )
    foreign_data = relationship(
        "MTGJSONCardForeignData",
        primaryjoin="MTGJSONCard.uuid==foreign(MTGJSONCardForeignData.uuid)"
    )
    summary = relationship(
        "MTGJSONSummaryCard",
        back_populates="printings",
        primaryjoin="MTGJSONCard.name==MTGJSONSummaryCard.name",
        foreign_keys=[name]
    )
    inventory = relationship(
        "InventoryItem",
        back_populates="card",
        primaryjoin="foreign(InventoryItem.card_name)==MTGJSONCard.name",
        uselist=False
    )

    def __repr__(self):
        return f"<MTGJSONCard(name={self.name!r})>"

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class MTGJSONCardIdentifier(MTGJSONBase):
    __tablename__ = "cardIdentifiers"

    uuid = Column(String(36), ForeignKey('cards.uuid'), primary_key=True)
    cardKingdomEtchedId = Column(Text, nullable=True)
    cardKingdomFoilId = Column(Text, nullable=True)
    cardKingdomId = Column(Text, nullable=True)
    cardsphereFoilId = Column(Text, nullable=True)
    cardsphereId = Column(Text, nullable=True)
    deckboxId = Column(Text, nullable=True)
    mcmId = Column(Text, nullable=True)
    mcmMetaId = Column(Text, nullable=True)
    mtgArenaId = Column(Text, nullable=True)
    mtgjsonFoilVersionId = Column(Text, nullable=True)
    mtgjsonNonFoilVersionId = Column(Text, nullable=True)
    mtgjsonV4Id = Column(Text, nullable=True)
    mtgoFoilId = Column(Text, nullable=True)
    mtgoId = Column(Text, nullable=True)
    multiverseId = Column(Text, nullable=True)
    scryfallCardBackId = Column(Text, nullable=True)
    scryfallId = Column(Text, nullable=True)
    scryfallIllustrationId = Column(Text, nullable=True)
    scryfallOracleId = Column(Text, nullable=True)
    tcgplayerEtchedProductId = Column(Text, nullable=True)
    tcgplayerProductId = Column(Text, nullable=True)
    card = relationship("MTGJSONCard", back_populates="identifiers")

    def __repr__(self):
        return f"<MTGJSONCardIdentifier(uuid={self.uuid!r})>"

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class MTGJSONCardLegality(MTGJSONBase):
    __tablename__ = "cardLegalities"

    uuid = Column(String(36), ForeignKey('cards.uuid'), primary_key=True)
    alchemy = Column(Text, nullable=True)
    brawl = Column(Text, nullable=True)
    commander = Column(Text, nullable=True)
    duel = Column(Text, nullable=True)
    explorer = Column(Text, nullable=True)
    future = Column(Text, nullable=True)
    gladiator = Column(Text, nullable=True)
    historic = Column(Text, nullable=True)
    legacy = Column(Text, nullable=True)
    modern = Column(Text, nullable=True)
    oathbreaker = Column(Text, nullable=True)
    oldschool = Column(Text, nullable=True)
    pauper = Column(Text, nullable=True)
    paupercommander = Column(Text, nullable=True)
    penny = Column(Text, nullable=True)
    pioneer = Column(Text, nullable=True)
    predh = Column(Text, nullable=True)
    premodern = Column(Text, nullable=True)
    standard = Column(Text, nullable=True)
    standardbrawl = Column(Text, nullable=True)
    timeless = Column(Text, nullable=True)
    vintage = Column(Text, nullable=True)
    card = relationship("MTGJSONCard", back_populates="legalities")

    def __repr__(self):
        return f"<MTGJSONCardLegality(uuid={self.uuid!r})>"

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class MTGJSONCardRuling(MTGJSONBase):
    __tablename__ = "cardRulings"

    uuid = Column(String(36), ForeignKey('cards.uuid'), primary_key=True)
    date = Column(Date, nullable=True)
    text = Column(Text, nullable=True)
    card = relationship("MTGJSONCard", back_populates="rulings")

    def __repr__(self):
        return f"<MTGJSONCardRuling(uuid={self.uuid!r}, date={self.date!r})>"

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class MTGJSONCardForeignData(MTGJSONBase):
    __tablename__ = "cardForeignData"

    uuid = Column(String(36), ForeignKey('cards.uuid'), primary_key=True)
    faceName = Column(Text, nullable=True)
    flavorText = Column(Text, nullable=True)
    identifiers = Column(JSON, nullable=True)  # Dictionary of identifiers
    language = Column(Text, nullable=True)
    multiverseId = Column(Integer, nullable=True)
    name = Column(Text, nullable=True)
    text = Column(Text, nullable=True)
    type = Column(Text, nullable=True)
    card = relationship("MTGJSONCard", back_populates="foreign_data")

    def __repr__(self):
        return f"<MTGJSONCardForeignData(uuid={self.uuid!r}, language={self.language!r})>"

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class MTGJSONCardPurchaseUrl(MTGJSONBase):
    __tablename__ = "cardPurchaseUrls"

    uuid = Column(String(36), ForeignKey('cards.uuid'), primary_key=True)
    cardKingdom = Column(Text, nullable=True)
    cardKingdomEtched = Column(Text, nullable=True)
    cardKingdomFoil = Column(Text, nullable=True)
    cardmarket = Column(Text, nullable=True)
    tcgplayer = Column(Text, nullable=True)
    tcgplayerEtched = Column(Text, nullable=True)
    card = relationship("MTGJSONCard", back_populates="purchase_urls")

    def __repr__(self):
        return f"<MTGJSONCardPurchaseUrl(uuid={self.uuid!r})>"

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class MTGJSONSummaryCard(MTGJSONBase):
    """
    A model that represents a card as a summary of its printings.
    It is based off of the newest printing of the card.
    """
    __tablename__ = "summary_cards"
    name: Mapped[str] = mapped_column(String, primary_key=True)
    set_code: Mapped[Optional[str]] = mapped_column(String)
    rarity: Mapped[Optional[str]] = mapped_column(String)
    type: Mapped[Optional[str]] = mapped_column(String)
    mana_cost: Mapped[Optional[str]] = mapped_column(String)
    converted_mana_cost: Mapped[Optional[float]] = mapped_column(Float)
    power: Mapped[Optional[str]] = mapped_column(String)
    toughness: Mapped[Optional[str]] = mapped_column(String)
    loyalty: Mapped[Optional[str]] = mapped_column(String)
    text: Mapped[Optional[str]] = mapped_column(Text)
    flavor_text: Mapped[Optional[str]] = mapped_column(Text)
    artist: Mapped[Optional[str]] = mapped_column(Text)

    printing_set_codes: Mapped[Optional[List[str]]] = mapped_column(JSON)
    color_identity: Mapped[Optional[List[str]]] = mapped_column(JSON)
    colors: Mapped[Optional[List[str]]] = mapped_column(JSON)
    types: Mapped[Optional[List[str]]] = mapped_column(JSON)
    supertypes: Mapped[Optional[List[str]]] = mapped_column(JSON)
    subtypes: Mapped[Optional[List[str]]] = mapped_column(JSON)
    keywords: Mapped[Optional[List[str]]] = mapped_column(JSON)
    legalities: Mapped[Optional[Dict[str, str]]] = mapped_column(JSON)

    printings: Mapped[List['MTGJSONCard']] = relationship(
        "MTGJSONCard",
        back_populates="summary",
        primaryjoin="MTGJSONSummaryCard.name==MTGJSONCard.name"
    )
    inventory_item: Mapped[Optional['InventoryItem']] = relationship(
        "InventoryItem",
        primaryjoin="foreign(InventoryItem.card_name)==MTGJSONSummaryCard.name",
        uselist=False,
        viewonly=True
    )

    def __repr__(self):
        return f"<MTGJSONSummaryCard(name={self.name!r}, color_identity={self.color_identity!r}, type={self.type!r})>"

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    @property
    def quantity(self):
        if self.inventory_item is not None:
            return self.inventory_item.quantity
        return 0

    @property
    def colors_list(self):
        v = self.colors
        from sqlalchemy.orm.attributes import InstrumentedAttribute
        from sqlalchemy.sql.schema import Column as SAColumn
        if v is None or isinstance(v, (InstrumentedAttribute, SAColumn)):
            return []
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                return []
        return []

    @property
    def color_identity_list(self):
        v = self.color_identity
        from sqlalchemy.orm.attributes import InstrumentedAttribute
        from sqlalchemy.sql.schema import Column as SAColumn
        if v is None or isinstance(v, (InstrumentedAttribute, SAColumn)):
            return []
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                return []
        return []

    @property
    def supertypes_list(self):
        v = self.supertypes
        from sqlalchemy.orm.attributes import InstrumentedAttribute
        from sqlalchemy.sql.schema import Column as SAColumn
        if v is None or isinstance(v, (InstrumentedAttribute, SAColumn)):
            return []
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                return []
        return []

    @property
    def subtypes_list(self):
        v = self.subtypes
        from sqlalchemy.orm.attributes import InstrumentedAttribute
        from sqlalchemy.sql.schema import Column as SAColumn
        if v is None or isinstance(v, (InstrumentedAttribute, SAColumn)):
            return []
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                return []
        return []

    @property
    def keywords_list(self):
        v = self.keywords
        from sqlalchemy.orm.attributes import InstrumentedAttribute
        from sqlalchemy.sql.schema import Column as SAColumn
        if v is None or isinstance(v, (InstrumentedAttribute, SAColumn)):
            return []
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                return []
        return []

    def matches_color_identity(self, color_identity, mode="subset", allow_colorless=False):
        card_ci = set(self.color_identity_list)
        query_ci = set(color_identity or [])
        if not allow_colorless and not card_ci:
            return False
        if mode == "exact":
            return card_ci == query_ci
        elif mode == "subset":
            return card_ci.issubset(query_ci)
        elif mode == "any":
            return bool(card_ci & query_ci)
        return False

    def matches_colors(self, colors: List[str], mode: str = "subset") -> bool:
        card_colors = set(self.colors_list)
        query_colors = set(colors or [])
        if mode == "exact":
            return card_colors == query_colors
        elif mode == "subset":
            return card_colors.issubset(query_colors)
        elif mode == "any":
            return bool(card_colors & query_colors)
        return False

    def has_keywords(self, keywords: List[str]):
        card_keywords = set(kw.lower() for kw in self.keywords_list)
        query_keywords = set(kw.lower() for kw in keywords or [])
        return bool(query_keywords.intersection(card_keywords))

    @property
    def owned_qty(self):
        "For backwards compatibility"
        return self.quantity
    
    def is_basic_land(self):
        """
        Determine if the card is a basic land.

        Returns:
            bool: True if the card is a basic land, False otherwise.
        """
        if not self.type or not self.name:
            return False
        basic_lands = {
            "Plains",
            "Island",
            "Swamp",
            "Mountain",
            "Forest",
            "Snow-Covered Plains",
            "Snow-Covered Island",
            "Snow-Covered Swamp",
            "Snow-Covered Mountain",
            "Snow-Covered Forest",
            "Wastes",
        }
        return self.name.strip() in basic_lands
    
    
    def is_land(self):
        t = self.type
        if t is None:
            return False
        return 'Land' in t
    
    def is_creature(self):
        t = self.type
        if t is None:
            return False
        return 'Creature' in t

    def matches_type(self, type_query):
        t = self.type
        if t is None or type_query is None:
            return False
        return type_query.lower() in t.lower()
        
    def matches_supertype(self, supertype):
        t = self.type
        if t is None or supertype is None:
            return False
        return supertype.lower() in t.lower()
        
    def matches_subtype(self, subtype):
        t = self.type
        if t is None or subtype is None:
            return False
        return subtype.lower() in t.lower()
    
    def matches_keyword(self, keyword):
        txt = self.text
        if txt is None or keyword is None:
            return False
        return keyword.lower() in txt.lower()
    
    def matches_color(self, color):
        colors = self.colors
        if colors is None or color is None:
            return False
        return color.lower() in [c.lower() for c in colors] if isinstance(colors, list) else color.lower() in str(colors).lower()
    
    def is_legal_in(self, format: Union[str, List[str]]) -> bool:
        if self.legalities is None:
            return False
        if isinstance(format, str):
            return self.legalities.get(format, "") == "Legal"
        elif isinstance(format, list):
            return all(self.legalities.get(f, "") == "Legal" for f in format)
  
    
    def to_pydantic(self) -> SummaryCard:
        return SummaryCard.model_validate(self)