from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, field_validator
import json

# --- Utilities for list/dict parsing ---
def parse_text_list(val: Optional[Union[str, List[str]]]) -> List[str]:
    if not val:
        return []
    if isinstance(val, list):
        return val
    try:
        obj = json.loads(val)
        if isinstance(obj, list):
            return obj
    except Exception:
        pass
    return [v.strip() for v in val.split(',') if v.strip()]

def parse_text_dict(val: Optional[Union[str, Dict[str, Any]]]) -> Dict[str, Any]:
    if not val:
        return {}
    if isinstance(val, dict):
        return val
    try:
        obj = json.loads(val)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    return {}

# --- Relationship models (minimal) ---
class SetModel(BaseModel):
    code: str
    name: Optional[str]
    releaseDate: Optional[str]
    # Add any other relevant fields...

    class Config:
        from_attributes = True

class CardLegalityModel(BaseModel):
    uuid: str
    format: Optional[str]
    legality: Optional[str]
    class Config:
        from_attributes = True

class CardIdentifierModel(BaseModel):
    uuid: str
    cardKingdomId: Optional[str]
    cardKingdomFoilId: Optional[str]
    mtgoFoilId: Optional[str]
    mtgoId: Optional[str]
    multiverseId: Optional[str]
    scryfallId: Optional[str]
    scryfallIllustrationId: Optional[str]
    scryfallOracleId: Optional[str]
    tcgplayerProductId: Optional[str]
    class Config:
        from_attributes = True

class CardPurchaseUrlModel(BaseModel):
    uuid: str
    cardKingdom: Optional[str]
    cardKingdomFoil: Optional[str]
    cardmarket: Optional[str]
    tcgplayer: Optional[str]
    class Config:
        from_attributes = True

class CardRulingModel(BaseModel):
    uuid: str
    date: Optional[str]
    text: Optional[str]
    class Config:
        from_attributes = True

class CardForeignDataModel(BaseModel):
    uuid: str
    flavorText: Optional[str]
    language: Optional[str]
    multiverseId: Optional[int]
    name: Optional[str]
    text: Optional[str]
    type: Optional[str]
    class Config:
        from_attributes = True

# --- Main Printing Model ---
class Printing(BaseModel):
    uuid: str
    name: str
    setCode: str
    artist: Optional[str]
    artistIds: List[str] = []
    attractionLights: List[str] = []
    availability: List[str] = []
    boosterTypes: List[str] = []
    borderColor: Optional[str]
    cardParts: List[str] = []
    colorIdentity: List[str] = []
    colorIndicator: List[str] = []
    colors: List[str] = []
    defense: Optional[str]
    duelDeck: Optional[str]
    edhrecRank: Optional[int]
    edhrecSaltiness: Optional[float]
    faceConvertedManaCost: Optional[float]
    faceFlavorName: Optional[str]
    faceManaValue: Optional[float]
    faceName: Optional[str]
    finishes: List[str] = []
    flavorName: Optional[str]
    flavorText: Optional[str]
    frameEffects: List[str] = []
    frameVersion: Optional[str]
    hand: Optional[str]
    hasAlternativeDeckLimit: Optional[bool]
    hasContentWarning: Optional[bool]
    hasFoil: Optional[bool]
    hasNonFoil: Optional[bool]
    isAlternative: Optional[bool]
    isFullArt: Optional[bool]
    isFunny: Optional[bool]
    isGameChanger: Optional[bool]
    isOnlineOnly: Optional[bool]
    isOversized: Optional[bool]
    isPromo: Optional[bool]
    isRebalanced: Optional[bool]
    isReprint: Optional[bool]
    isReserved: Optional[bool]
    isStarter: Optional[bool]
    isStorySpotlight: Optional[bool]
    isTextless: Optional[bool]
    isTimeshifted: Optional[bool]
    keywords: List[str] = []
    language: Optional[str]
    layout: Optional[str]
    leadershipSkills: Dict[str, Any] = {}
    life: Optional[str]
    loyalty: Optional[str]
    manaCost: Optional[str]
    manaValue: Optional[float]
    number: Optional[str]
    originalPrintings: List[str] = []
    originalReleaseDate: Optional[str]
    originalText: Optional[str]
    originalType: Optional[str]
    otherFaceIds: List[str] = []
    power: Optional[str]
    printings: List[str] = []
    promoTypes: List[str] = []
    rarity: Optional[str]
    rebalancedPrintings: List[str] = []
    relatedCards: List[str] = []
    securityStamp: Optional[str]
    side: Optional[str]
    signature: Optional[str]
    sourceProducts: List[str] = []
    subsets: List[str] = []
    supertypes: List[str] = []
    subtypes: List[str] = []
    text: Optional[str]
    toughness: Optional[str]
    type: Optional[str]
    types: List[str] = []
    variations: List[str] = []
    watermark: Optional[str]

    # Relationships (fully included)
    set: Optional[SetModel] = None
    legalities: Optional[CardLegalityModel] = None
    identifiers: Optional[CardIdentifierModel] = None
    purchase_urls: Optional[CardPurchaseUrlModel] = None
    rulings: List[CardRulingModel] = []
    foreign_data: List[CardForeignDataModel] = []

    @field_validator(
        'artistIds', 'attractionLights', 'availability', 'boosterTypes', 'cardParts', 'colorIdentity',
        'colorIndicator', 'colors', 'finishes', 'frameEffects', 'keywords', 'originalPrintings', 'otherFaceIds',
        'printings', 'promoTypes', 'rebalancedPrintings', 'relatedCards', 'sourceProducts', 'subsets',
        'supertypes', 'subtypes', 'types', 'variations',
        mode='before'
    )
    @classmethod
    def _parse_list_fields(cls, v):
        return parse_text_list(v)

    @field_validator('leadershipSkills', mode='before')
    @classmethod
    def _parse_dict_fields(cls, v):
        return parse_text_dict(v)

    class Config:
        from_attributes = True

    def __repr__(self) -> str:
        return f"<Printing(name={self.name!r}, setCode={self.setCode!r})>"

class InventoryItem(BaseModel):
    name: str
    quantity: int
    class Config:
        from_attributes = True

class SummaryCard(BaseModel):
    name: str = ""
    set_code: str = ""
    rarity: str = ""
    type: str = ""
    mana_cost: str = ""
    converted_mana_cost: float = 0.0
    power: str = ""
    toughness: str = ""
    loyalty: str = ""
    text: str = ""
    flavor_text: str = ""
    artist: str = ""

    printing_set_codes: List[str] = []
    color_identity: List[str] = []
    colors: List[str] = []
    types: List[str] = []
    supertypes: List[str] = []
    subtypes: List[str] = []
    keywords: List[str] = []
    legalities: Dict[str, str] = {}

    # Inventory/relationships (optional)
    inventory_item: Optional[Any] = None
    printings: List[Printing] = []

    class Config:
        from_attributes = True
    
    def __repr__(self):
        return f"<SummaryCard(name={self.name!r}, color_identity={self.color_identity!r}, type={self.type!r})>"

    def to_dict(self):
        return self.model_dump()

    @property
    def quantity(self):
        if self.inventory_item is not None and hasattr(self.inventory_item, 'quantity'):
            return self.inventory_item.quantity
        return 0

    @property
    def colors_list(self):
        return self.colors or []

    @property
    def color_identity_list(self):
        return self.color_identity or []

    @property
    def supertypes_list(self):
        return self.supertypes or []

    @property
    def subtypes_list(self):
        return self.subtypes or []

    @property
    def keywords_list(self):
        return self.keywords or []

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
        # deprecated warning
        return self.quantity

    def is_basic_land(self):
        t = self.type
        if t is None:
            return False
        return 'Basic Land' in t

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