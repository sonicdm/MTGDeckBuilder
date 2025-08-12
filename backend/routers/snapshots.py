from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from backend.deps import get_db_url

from backend.security.paths import Scope, safe_path, exports_root
from mtg_deck_builder.db import get_session
from mtg_deck_builder.db.repository import SummaryCardRepository
from mtg_deck_builder.models.deck_exporter import DeckExporter
from mtg_deck_builder.snapshot_io import (
    deck_to_snapshot,
    load_snapshot,
    save_snapshot,
    reconstruct_deck_from_snapshot,
)


router = APIRouter(prefix="/api/snapshots", tags=["snapshots"])


def _reconstruct_temp_decklist(decklist: List[Dict[str, Any]]):
    # Placeholder: we will rely on reconstruct endpoint which uses snapshot + repo.
    return decklist


@router.post("/save")
def save_snapshot_endpoint(payload: Dict[str, Any], db_url: str = Depends(get_db_url)) -> Dict[str, Any]:
    rel_path: Optional[str] = payload.get("path")
    deck_config: Dict[str, Any] = payload.get("deck_config") or {}
    seed_yaml: Optional[str] = payload.get("seed_yaml")
    build_hints: Optional[Dict[str, Any]] = payload.get("build_hints")
    decklist: List[Dict[str, Any]] = payload.get("decklist") or []
    analysis: Optional[Dict[str, Any]] = payload.get("analysis")
    arena: Optional[str] = payload.get("arena")

    if not rel_path or not rel_path.endswith((".deck.json",)):
        raise HTTPException(status_code=400, detail="path must end with .deck.json")
    if len(seed_yaml or "") > 1_000_000:
        raise HTTPException(status_code=400, detail="seed_yaml too large")
    path = safe_path(Scope.EXPORTS, rel_path)

    with get_session(db_url=db_url) as session:
        repo = SummaryCardRepository(session)
        # For now, snapshot requires a live Deck; we store basic fields
        snapshot = {
            "version": "1.0",
            "config": deck_config,
            "seed_yaml": seed_yaml,
            "build_hints": build_hints or {},
            "deck": decklist,
            "analysis": analysis or {},
            "arena": arena or "",
        }
        save_snapshot(snapshot, Path(path))
    return {"ok": True, "path": str(path)}


@router.post("/load")
def load_snapshot_endpoint(payload: Dict[str, Any]) -> Dict[str, Any]:
    rel_path: Optional[str] = payload.get("path")
    if not rel_path or not rel_path.endswith((".deck.json",)):
        raise HTTPException(status_code=400, detail="path must end with .deck.json")
    path = safe_path(Scope.EXPORTS, rel_path)
    snap = load_snapshot(Path(path))
    return snap


@router.post("/reconstruct")
def reconstruct_snapshot_endpoint(payload: Dict[str, Any], db_url: str = Depends(get_db_url)) -> Dict[str, Any]:
    snapshot: Dict[str, Any] = payload.get("snapshot") or {}
    with get_session(db_url=db_url) as session:
        repo = SummaryCardRepository(session)
        deck = reconstruct_deck_from_snapshot(snapshot, repo)
        arena = DeckExporter(deck).mtg_arena_import()
        decklist = [
            {"qty": deck.inventory.get(name, 0), "name": name, "type": getattr(card, "type", ""), "mv": getattr(card, "converted_mana_cost", 0)}
            for name, card in deck.cards.items()
        ]
        return {"decklist": decklist, "arena_import": arena}


