\
from typing import List, Optional
from pydantic import BaseModel, Field

class AtomicCard(BaseModel):
    name: str
    layout: Optional[str] = None
    manaCost: Optional[str] = None
    manaValue: Optional[float] = Field(None, alias="convertedManaCost")
    text: Optional[str] = None
    type: Optional[str] = Field(None, alias="type")
    types: Optional[List[str]] = None
    subtypes: Optional[List[str]] = None
    supertypes: Optional[List[str]] = None
    colorIdentity: Optional[List[str]] = None
    colors: Optional[List[str]] = None
    power: Optional[str] = None
    toughness: Optional[str] = None
    # Add more fields as needed (printings, legalities, etc.)

    class Config:
        allow_population_by_field_name = True

class AtomicCards(BaseModel):
    data: Dict[str, AtomicCard]

    class Config:
        allow_population_by_field_name = True
