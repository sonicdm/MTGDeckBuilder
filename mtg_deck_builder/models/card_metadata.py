# models/foreign_data.py
from typing import Optional

from pydantic import BaseModel

BASIC_LAND_NAMES = {"Plains", "Island", "Swamp", "Mountain", "Forest"}

class ForeignData(BaseModel):
    language: str
    multiverse_id: Optional[int] = None
    name: str
    text: Optional[str] = None
    type: Optional[str] = None
    flavor_text: Optional[str] = None


# models/legalities.py
from pydantic import BaseModel


class Legalities(BaseModel):
    format: str
    legality: str


# models/rulings.py
from pydantic import BaseModel


class Ruling(BaseModel):
    date: str
    text: str
