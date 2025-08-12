from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from backend.config_adapter import ConfigService
from backend.security.paths import set_roots, Scope, safe_path, configs_root
from mtg_deck_builder.models.deck_config import DeckConfig


router = APIRouter(prefix="/api", tags=["config"])


def _service() -> ConfigService:
    from backend.app import _data_root  # lazy import to avoid cycles
    return ConfigService(_data_root())


@router.get("/config")
def get_config() -> Dict[str, Any]:
    return _service().get()


@router.put("/config")
def put_config(patch: Dict[str, Any]) -> Dict[str, Any]:
    updated = _service().update(patch)
    paths = updated["paths"]
    set_roots(
        decks=Path(paths["deck_configs_dir"]),
        mtgjson=Path(paths["mtgjson_dir"]),
        inventory=Path(paths["inventory_dir"]),
        configs=_service().configs_dir,
        exports=Path(paths["deck_outputs_dir"]),
    )
    return updated


@router.get("/config/files")
def list_config_files() -> Dict[str, list]:
    base = configs_root()
    json_files = [str(p.relative_to(base)) for p in base.rglob("*.json")]
    yaml_files = [str(p.relative_to(base)) for p in base.rglob("*.yml")] + [str(p.relative_to(base)) for p in base.rglob("*.yaml")]
    return {"json": json_files, "yaml": yaml_files}


@router.get("/config/file")
def read_config_file(path: str) -> Dict[str, str]:
    p = safe_path(Scope.CONFIGS, path)
    if p.suffix.lower() not in (".json", ".yml", ".yaml"):
        raise HTTPException(status_code=400, detail="Only .json/.yml/.yaml files are allowed")
    if not p.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return {"path": path, "text": p.read_text(encoding="utf-8")}


@router.post("/config/file")
def write_config_file(payload: Dict[str, str]) -> Dict[str, str]:
    path = payload.get("path")
    text = payload.get("text")
    if not path or text is None:
        raise HTTPException(status_code=400, detail="path and text are required")
    p = safe_path(Scope.CONFIGS, path)
    if p.suffix.lower() not in (".json", ".yml", ".yaml"):
        raise HTTPException(status_code=400, detail="Only .json/.yml/.yaml files are allowed")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return {"ok": "true", "path": path}


@router.post("/config/save_yaml")
def save_config_yaml(payload: Dict[str, Any]) -> Dict[str, str]:
    """Validate a DeckConfig dict and save as YAML under configs dir.

    Body: { path: "rel/name.yaml", config: { ... DeckConfig dict ... } }
    """
    path = payload.get("path")
    cfg = payload.get("config")
    if not path or not isinstance(cfg, dict):
        raise HTTPException(status_code=400, detail="path and config are required")
    p = safe_path(Scope.CONFIGS, path)
    if p.suffix.lower() not in (".yaml", ".yml"):
        raise HTTPException(status_code=400, detail="path must end with .yaml or .yml")
    # Validate deck config using library model
    try:
        deck_config = DeckConfig.from_dict(cfg)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid DeckConfig: {e}")
    p.parent.mkdir(parents=True, exist_ok=True)
    deck_config.to_yaml(p)
    return {"ok": "true", "path": str(p)}


