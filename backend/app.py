from __future__ import annotations

import os
import zipfile
from pathlib import Path
from typing import Callable

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config_adapter import ConfigService
from backend.security.paths import Scope, set_roots, mtgjson_root
from backend.routers import build as build_router
from backend.routers import arena_import as arena_router
from backend.routers import snapshots as snapshots_router
from backend.routers import configs as configs_router
from backend.routers import decks_fs as decks_router
from backend.routers import inventory_fs as inventory_router


def _data_root() -> Path:
    env = os.environ.get("MTG_DATA")
    return Path(env).resolve() if env else (Path(__file__).resolve().parent.parent / "data").resolve()


def _ensure_tree(root: Path) -> None:
    for sub in ["mtgjson", "configs", "decks", "exports", "inventory", "user_uploads"]:
        (root / sub).mkdir(parents=True, exist_ok=True)


def _ensure_sqlite(mtgjson_dir: Path) -> Path:
    sqlite_path = mtgjson_dir / "AllPrintings.sqlite"
    if sqlite_path.exists():
        return sqlite_path
    zip_path = mtgjson_dir / "AllPrintings.sqlite.zip"
    if zip_path.exists():
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(mtgjson_dir)
        if sqlite_path.exists():
            return sqlite_path
    json_path = mtgjson_dir / "AllPrintings.json"
    if json_path.exists():
        # Placeholder: could trigger importer if available
        raise HTTPException(status_code=500, detail="SQLite missing; JSON present but importer not wired yet. Place AllPrintings.sqlite or .zip in /data/mtgjson")
    raise HTTPException(status_code=500, detail="Place AllPrintings.sqlite or AllPrintings.sqlite.zip in /data/mtgjson")


def create_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    data_root = _data_root()
    _ensure_tree(data_root)
    cfg = ConfigService(data_root)
    cfg_data = cfg.load()
    paths = cfg_data["paths"]

    set_roots(
        decks=Path(paths["deck_configs_dir"]),
        mtgjson=Path(paths["mtgjson_dir"]),
        inventory=Path(paths["inventory_dir"]),
        configs=cfg.configs_dir,
        exports=Path(paths["deck_outputs_dir"]),
    )
    sqlite_path = _ensure_sqlite(mtgjson_root())
    db_url = f"sqlite:///{sqlite_path}"

    # Provide db_url dependency
    def _db_url_dep() -> str:
        return db_url

    # Provide a concrete function for dependency override
    from backend import deps as deps_module
    app.dependency_overrides[deps_module.get_db_url] = _db_url_dep

    app.include_router(build_router.router)
    app.include_router(arena_router.router)
    app.include_router(snapshots_router.router)
    app.include_router(configs_router.router)
    app.include_router(decks_router.router)
    app.include_router(inventory_router.router)

    # Static frontend if built
    frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
    if frontend_dist.exists():
        app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")

    return app


app = create_app()


