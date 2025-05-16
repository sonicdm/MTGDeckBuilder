from typing import Dict, Optional
from pydantic import BaseModel
from uuid import UUID

class CardSet(BaseModel):
    set_name: str
    set_code: str
    release_date: Optional[str] = None
    block: Optional[str] = None
    cards: Dict[UUID, int]