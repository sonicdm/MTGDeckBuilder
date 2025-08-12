from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from backend.deps import get_db_url

from mtg_deck_builder.db import get_session
from mtg_deck_builder.db.repository import SummaryCardRepository
from mtg_deck_builder.models.deck_analyzer import DeckAnalyzer
from mtg_deck_builder.models.deck_exporter import DeckExporter
from mtg_deck_builder.utils.arena_deck_creator import create_deck_from_arena_import


router = APIRouter(prefix="/api", tags=["arena"])


@router.post("/import/arena")
def import_arena(payload: Dict[str, Any], db_url: str = Depends(get_db_url)) -> Dict[str, Any]:
    text: Optional[str] = payload.get("text")
    deck_name: str = payload.get("deck_name") or "Imported Deck"
    if not text or len(text) > 1_000_000:
        raise HTTPException(status_code=400, detail="text is required and must be <1MB")

    with get_session(db_url=db_url) as session:
        deck = create_deck_from_arena_import(text, deck_name=deck_name, session=session)
        if deck is None:
            raise HTTPException(status_code=400, detail="Failed to import Arena deck")
        analysis = DeckAnalyzer(deck).summary_dict()
        arena = DeckExporter(deck).mtg_arena_import()
        decklist = [
            {"qty": deck.inventory.get(name, 0), "name": name, "type": getattr(card, "type", ""), "mv": getattr(card, "converted_mana_cost", 0)}
            for name, card in deck.cards.items()
        ]
        # Simple resolution report placeholder until detailed resolution is added
        report = {"missing": [], "resolved": [name for name in deck.cards.keys()]}
        return {"decklist": decklist, "analysis": analysis, "arena_import": arena, "resolution": report}


