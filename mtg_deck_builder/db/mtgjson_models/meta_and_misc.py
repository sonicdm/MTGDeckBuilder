from sqlalchemy import Column, String, Integer, Float, Text, Boolean, Date
from .base import MTGJSONBase

class MTGJSONMeta(MTGJSONBase):
    __tablename__ = "meta"
    date = Column(Date, primary_key=True)
    version = Column(Text, nullable=True)

    def __repr__(self):
        return f"<MTGJSONMeta(date={self.date!r}, version={self.version!r})>"

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class MTGJSONCardRuling(MTGJSONBase):
    __tablename__ = "cardRulings"
    uuid = Column(String(36), primary_key=True)
    date = Column(Date, nullable=True)
    text = Column(Text, nullable=True)

    def __repr__(self):
        return f"<MTGJSONCardRuling(uuid={self.uuid}, date={self.date})>"

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class MTGJSONCardForeignData(MTGJSONBase):
    __tablename__ = "cardForeignData"
    uuid = Column(Text, primary_key=True, nullable=True)
    faceName = Column(Text, nullable=True)
    flavorText = Column(Text, nullable=True)
    identifiers = Column(Text, nullable=True)
    language = Column(Text, nullable=True)
    multiverseId = Column(Integer, nullable=True)
    name = Column(Text, nullable=True)
    text = Column(Text, nullable=True)
    type = Column(Text, nullable=True)

    def __repr__(self):
        return f"<MTGJSONCardForeignData(uuid={self.uuid}, language={self.language})>"

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class MTGJSONCardPurchaseUrl(MTGJSONBase):
    __tablename__ = "cardPurchaseUrls"
    uuid = Column(Text, primary_key=True, nullable=True)
    cardKingdom = Column(Text, nullable=True)
    cardKingdomEtched = Column(Text, nullable=True)
    cardKingdomFoil = Column(Text, nullable=True)
    cardmarket = Column(Text, nullable=True)
    tcgplayer = Column(Text, nullable=True)
    tcgplayerEtched = Column(Text, nullable=True)

    def __repr__(self):
        return f"<MTGJSONCardPurchaseUrl(uuid={self.uuid})>"

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns} 