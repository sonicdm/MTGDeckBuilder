from sqlalchemy import Column, String, Integer, Float, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship, backref
from .base import MTGJSONBase
from .tokens import MTGJSONToken

class MTGJSONSet(MTGJSONBase):
    __tablename__ = "sets"
    code = Column(String(8), primary_key=True)
    baseSetSize = Column(Integer)
    block = Column(Text)
    cardsphereSetId = Column(Integer)
    isFoilOnly = Column(Boolean)
    isForeignOnly = Column(Boolean)
    isNonFoilOnly = Column(Boolean)
    isOnlineOnly = Column(Boolean)
    isPartialPreview = Column(Boolean)
    keyruneCode = Column(Text)
    languages = Column(Text)
    mcmId = Column(Integer)
    mcmIdExtras = Column(Integer)
    mcmName = Column(Text)
    mtgoCode = Column(Text)
    name = Column(Text)
    parentCode = Column(Text)
    releaseDate = Column(Text)
    tcgplayerGroupId = Column(Integer)
    tokenSetCode = Column(Text)
    totalSetSize = Column(Integer)
    type = Column(Text)

    def __repr__(self):
        return f"<MTGJSONSet(name={self.name!r}, code={self.code!r})>"

    # Relationships
    cards = relationship(
        "MTGJSONCard",
        primaryjoin="MTGJSONSet.code==foreign(MTGJSONCard.setCode)",
        back_populates="set"
    )
    tokens = relationship(
        "MTGJSONToken",
        primaryjoin="MTGJSONSet.code==foreign(MTGJSONToken.setCode)",
        back_populates="set"
    ) 