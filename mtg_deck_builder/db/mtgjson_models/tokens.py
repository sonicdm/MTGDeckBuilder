from sqlalchemy import Column, String, Integer, Float, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship, foreign
from .base import MTGJSONBase

class MTGJSONToken(MTGJSONBase):
    __tablename__ = "tokens"
    uuid = Column(String(36), primary_key=True)
    name = Column(Text, nullable=True)
    setCode = Column(Text, ForeignKey('sets.code'), nullable=True)
    artist = Column(Text, nullable=True)
    artistIds = Column(Text, nullable=True)
    asciiName = Column(Text, nullable=True)
    availability = Column(Text, nullable=True)
    boosterTypes = Column(Text, nullable=True)
    borderColor = Column(Text, nullable=True)
    colorIdentity = Column(Text, nullable=True)
    colors = Column(Text, nullable=True)
    edhrecSaltiness = Column(Float, nullable=True)
    faceName = Column(Text, nullable=True)
    finishes = Column(Text, nullable=True)
    flavorName = Column(Text, nullable=True)
    flavorText = Column(Text, nullable=True)
    frameEffects = Column(Text, nullable=True)
    frameVersion = Column(Text, nullable=True)
    hasFoil = Column(Boolean, nullable=True)
    hasNonFoil = Column(Boolean, nullable=True)
    isFullArt = Column(Boolean, nullable=True)
    isFunny = Column(Boolean, nullable=True)
    isOversized = Column(Boolean, nullable=True)
    isPromo = Column(Boolean, nullable=True)
    isReprint = Column(Boolean, nullable=True)
    isTextless = Column(Boolean, nullable=True)
    keywords = Column(Text, nullable=True)
    language = Column(Text, nullable=True)
    layout = Column(Text, nullable=True)
    manaCost = Column(Text, nullable=True)
    orientation = Column(Text, nullable=True)
    originalText = Column(Text, nullable=True)
    otherFaceIds = Column(Text, nullable=True)
    power = Column(Text, nullable=True)
    promoTypes = Column(Text, nullable=True)
    relatedCards = Column(Text, nullable=True)
    reverseRelated = Column(Text, nullable=True)
    securityStamp = Column(Text, nullable=True)
    side = Column(Text, nullable=True)
    signature = Column(Text, nullable=True)
    subtypes = Column(Text, nullable=True)
    supertypes = Column(Text, nullable=True)
    text = Column(Text, nullable=True)
    toughness = Column(Text, nullable=True)
    type = Column(Text, nullable=True)
    types = Column(Text, nullable=True)
    watermark = Column(Text, nullable=True)
    set = relationship("MTGJSONSet", back_populates="tokens", primaryjoin="MTGJSONToken.setCode==MTGJSONSet.code")
    identifiers = relationship("MTGJSONTokenIdentifier", back_populates="token", uselist=False, primaryjoin="MTGJSONToken.uuid==foreign(MTGJSONTokenIdentifier.uuid)")

    def __repr__(self):
        return f"<MTGJSONToken(name={self.name!r}, uuid={self.uuid!r})>"

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class MTGJSONTokenIdentifier(MTGJSONBase):
    __tablename__ = "tokenIdentifiers"
    uuid = Column(String(36), ForeignKey('tokens.uuid'), primary_key=True)
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
    token = relationship("MTGJSONToken", back_populates="identifiers", primaryjoin="foreign(MTGJSONTokenIdentifier.uuid)==MTGJSONToken.uuid")

    def __repr__(self):
        return f"<MTGJSONTokenIdentifier(uuid={self.uuid!r})>"

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns} 