from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from mtg_deckbuilder_ui.app_config import AppConfig


DEFAULT_DIRS = {
    "mtgjson_dir": "data/mtgjson",
    "deck_configs_dir": "data/decks",
    "deck_outputs_dir": "data/exports",
    "inventory_dir": "data/inventory",
    "configs_dir": "data/configs",
}


class ConfigService:
    def __init__(self, root: Path) -> None:
        self.root = Path(root).resolve()
        self.configs_dir = (self.root / "configs").resolve()
        self.configs_dir.mkdir(parents=True, exist_ok=True)
        self.file = self.configs_dir / "app_config.json"
        self._app_config = AppConfig()

    def _backfill(self, data: Dict[str, Any]) -> Dict[str, Any]:
        paths = data.setdefault("paths", {})
        for key, rel in DEFAULT_DIRS.items():
            if key not in paths:
                paths[key] = str((self.root / rel.replace("data/", "")).resolve())
        # Also ensure allprintings_sqlite path exists
        if "allprintings_sqlite" not in paths:
            paths["allprintings_sqlite"] = str(
                (Path(paths["mtgjson_dir"]) / "AllPrintings.sqlite").resolve()
            )
        return data

    def load(self) -> Dict[str, Any]:
        if self.file.exists():
            data = json.loads(self.file.read_text(encoding="utf-8"))
        else:
            data = {"paths": {}}
        data = self._backfill(data)
        return data

    def save(self, data: Dict[str, Any]) -> None:
        self.file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def get(self) -> Dict[str, Any]:
        return self.load()

    def update(self, patch: Dict[str, Any]) -> Dict[str, Any]:
        current = self.load()
        for k, v in patch.items():
            if isinstance(v, dict) and isinstance(current.get(k), dict):
                current[k].update(v)
            else:
                current[k] = v
        current = self._backfill(current)

        # Re-validate via AppConfig by syncing relevant paths
        paths = current.get("paths", {})
        ac = self._app_config
        # Map into AppConfig Paths section
        mapping = {
            "deck_configs_dir": "deck_configs_dir",
            "inventory_dir": "inventory_dir",
            "mtgjson_dir": "mtgjson_dir",
            "deck_outputs_dir": "deck_outputs_dir",
            # AppConfig also expects keywords/cardtypes/meta, but we keep JSON model separate
            "allprintings_sqlite": "allprintings_sqlite",
        }
        for src, dst in mapping.items():
            if src in paths:
                ac.set("Paths", dst, Path(paths[src]))

        self.save(current)
        return current

    def list_configs(self) -> Dict[str, str]:
        return {p.name: str(p) for p in self.configs_dir.glob("*.json")}


