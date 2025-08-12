from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from mtg_deck_builder.db.repository import SummaryCardRepository
from mtg_deck_builder.models.deck import Deck
from mtg_deck_builder.models.deck_exporter import DeckExporter


SNAPSHOT_VERSION = "1.0"


def _file_sha1(path: Path) -> Optional[str]:
    try:
        h = hashlib.sha1()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except FileNotFoundError:
        return None


def deck_to_snapshot(
    deck: Deck,
    deck_config: Dict[str, Any],
    seed_yaml: Optional[str] = None,
    build_hints: Optional[Dict[str, Any]] = None,
    inventory_key: Optional[str] = None,
    sqlite_path: Optional[Path] = None,
) -> Dict[str, Any]:
    deck_rows = [
        {
            "qty": deck.inventory.get(name, 0),
            "name": name,
            "uuid": getattr(card, "uuid", None),
            "set": getattr(card, "set_code", getattr(card, "setCode", None)),
            "number": getattr(card, "number", None),
            "type": getattr(card, "type", ""),
            "mv": getattr(card, "converted_mana_cost", getattr(card, "manaValue", 0)),
        }
        for name, card in deck.cards.items()
    ]
    arena = DeckExporter(deck).mtg_arena_import()
    db_fingerprint = None
    if sqlite_path:
        sqlite_path = Path(sqlite_path)
        db_fingerprint = {
            "sqlite_path": str(sqlite_path),
            "mtime": sqlite_path.stat().st_mtime if sqlite_path.exists() else None,
            "sha1": _file_sha1(sqlite_path),
        }
    return {
        "version": SNAPSHOT_VERSION,
        "created": datetime.utcnow().isoformat() + "Z",
        "app": {"name": "mtg_deck_builder", "schema": "deck-snapshot"},
        "config": deck_config,
        "seed_yaml": seed_yaml,
        "build_hints": build_hints or {},
        "inventory_key": inventory_key,
        "db_fingerprint": db_fingerprint,
        "deck": deck_rows,
        "sideboard": [],
        "analysis": {},
        "mana_base": {},
        "arena": arena,
        "build_log": [],
        "unmet": [],
    }


def save_snapshot(snapshot: Dict[str, Any], path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")


def load_snapshot(path: Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def reconstruct_deck_from_snapshot(snapshot: Dict[str, Any], repo: SummaryCardRepository) -> Deck:
    deck = Deck(name=snapshot.get("config", {}).get("deck", {}).get("name", "Snapshot Deck"), session=repo.session)
    for row in snapshot.get("deck", []):
        name = row.get("name")
        qty = int(row.get("qty") or 0)
        if not name or qty <= 0:
            continue
        card = repo.find_by_name(name, exact=True)
        if not card:
            continue
        deck.insert_card(card, quantity=qty)
    return deck


