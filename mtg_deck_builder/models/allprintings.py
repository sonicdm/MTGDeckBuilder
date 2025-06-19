from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# --- Submodels ---

class Identifiers(BaseModel):
    cardKingdomFoilId: Optional[str]
    cardsphereFoilId: Optional[str]
    deckboxId: Optional[str]
    mcmId: Optional[str]
    mtgjsonV4Id: Optional[str]
    scryfallCardBackId: Optional[str]
    scryfallId: Optional[str]
    scryfallIllustrationId: Optional[str]
    scryfallOracleId: Optional[str]
    tcgplayerProductId: Optional[str]
    # Add other fields as needed

class Legalities(BaseModel):
    commander: Optional[str]
    duel: Optional[str]
    legacy: Optional[str]
    modern: Optional[str]
    oathbreaker: Optional[str]
    penny: Optional[str]
    pioneer: Optional[str]
    vintage: Optional[str]
    # Add other formats as needed

class Ruling(BaseModel):
    date: str
    text: str

class PurchaseUrls(BaseModel):
    cardKingdomFoil: Optional[str]
    tcgplayer: Optional[str]
    # Add other vendors as needed

class LeadershipSkills(BaseModel):
    brawl: Optional[bool]
    commander: Optional[bool]
    oathbreaker: Optional[bool]

# --- Card (Set) Model ---

class CardSet(BaseModel):
    artist: Optional[str] = None
    artistIds: Optional[List[str]] = None
    asciiName: Optional[str] = None
    attractionLights: Optional[List[int]] = None
    availability: List[str]
    boosterTypes: Optional[List[str]] = None
    borderColor: str
    cardParts: Optional[List[str]] = None
    colorIdentity: List[str]
    colorIndicator: Optional[List[str]] = None
    colors: List[str]
    convertedManaCost: Optional[float] = None
    defense: Optional[str] = None
    duelDeck: Optional[str] = None
    edhrecRank: Optional[int] = None
    edhrecSaltiness: Optional[float] = None
    faceConvertedManaCost: Optional[float] = None
    faceFlavorName: Optional[str] = None
    faceManaValue: Optional[float] = None
    faceName: Optional[str] = None
    finishes: List[str]
    flavorName: Optional[str] = None
    flavorText: Optional[str] = None
    foreignData: Optional[List[Any]] = None
    frameEffects: Optional[List[str]] = None
    frameVersion: str
    hand: Optional[str] = None
    hasAlternativeDeckLimit: Optional[bool] = None
    hasContentWarning: Optional[bool] = None
    hasFoil: Optional[bool] = None
    hasNonFoil: Optional[bool] = None
    identifiers: Identifiers
    isAlternative: Optional[bool] = None
    isFullArt: Optional[bool] = None
    isFunny: Optional[bool] = None
    isOnlineOnly: Optional[bool] = None
    isOversized: Optional[bool] = None
    isPromo: Optional[bool] = None
    isRebalanced: Optional[bool] = None
    isReprint: Optional[bool] = None
    isReserved: Optional[bool] = None
    isStarter: Optional[bool] = None
    isStorySpotlight: Optional[bool] = None
    isTextless: Optional[bool] = None
    isTimeshifted: Optional[bool] = None
    keywords: Optional[List[str]] = None
    language: str
    layout: str
    leadershipSkills: Optional[LeadershipSkills] = None
    legalities: Legalities
    life: Optional[str] = None
    loyalty: Optional[str] = None
    manaCost: Optional[str] = None
    manaValue: float
    name: str
    number: str
    originalPrintings: Optional[List[str]] = None
    originalReleaseDate: Optional[str] = None
    originalText: Optional[str] = None
    originalType: Optional[str] = None
    otherFaceIds: Optional[List[str]] = None
    power: Optional[str] = None
    printings: Optional[List[str]] = None
    promoTypes: Optional[List[str]] = None
    purchaseUrls: PurchaseUrls
    rarity: str
    relatedCards: Optional[Any] = None
    rebalancedPrintings: Optional[List[str]] = None
    rulings: Optional[List[Ruling]] = None
    securityStamp: Optional[str] = None
    setCode: str
    side: Optional[str] = None
    signature: Optional[str] = None
    sourceProducts: Optional[Any] = None
    subsets: Optional[List[str]] = None
    subtypes: List[str]
    supertypes: List[str]
    text: Optional[str] = None
    toughness: Optional[str] = None
    type: str
    types: List[str]
    uuid: str
    variations: Optional[List[str]] = None
    watermark: Optional[str] = None

# --- Set Model ---

class SetModel(BaseModel):
    baseSetSize: int
    block: Optional[str]
    booster: Optional[Dict[str, Any]]
    cards: List[CardSet]
    cardsphereSetId: Optional[int]
    code: str
    codeV3: Optional[str]
    decks: Optional[List[Any]]
    isForeignOnly: Optional[bool]
    isFoilOnly: bool
    isNonFoilOnly: Optional[bool]
    isOnlineOnly: bool
    isPaperOnly: Optional[bool]
    isPartialPreview: Optional[bool]
    keyruneCode: str
    languages: Optional[List[str]]
    mcmId: Optional[int]
    mcmIdExtras: Optional[int]
    mcmName: Optional[str]
    mtgoCode: Optional[str]
    name: str
    parentCode: Optional[str]
    releaseDate: str
    sealedProduct: Optional[List[Any]]
    tcgplayerGroupId: Optional[int]
    tokens: Optional[List[Any]]
    tokenSetCode: Optional[str]
    totalSetSize: int
    translations: Optional[Dict[str, str]]
    type: str

# --- Loader Function ---

class AllPrintings(BaseModel):
    data: Dict[str, SetModel]
    meta: Dict[str, Any]
    

def load_allprintings(path: str) -> Dict[str, SetModel]:
    """Load and validate AllPrintings JSON into SetModel objects."""

    import json
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return AllPrintings.model_validate(data)

def load_allprintings_parallel(path: str, max_workers: int = 8) -> AllPrintings:
    """
    Load and validate AllPrintings JSON in parallel by set using ThreadPoolExecutor,
    with a progress bar and graceful Ctrl+C handling.
    """
    import json
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    sets = data["data"]
    meta = data.get("meta", {})

    def validate_set(item):
        set_code, set_data = item
        return set_code, SetModel.model_validate(set_data)

    validated_sets = {}
    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(validate_set, item) for item in sets.items()]
            for future in tqdm(as_completed(futures), total=len(futures), desc="Validating sets"):
                set_code, set_obj = future.result()
                validated_sets[set_code] = set_obj
    except KeyboardInterrupt:
        print("\nValidation interrupted by user (Ctrl+C). Exiting gracefully...")
        # Optionally, cancel all futures
        for future in futures:
            future.cancel()
        raise SystemExit(1)

    return AllPrintings(data=validated_sets, meta=meta)
