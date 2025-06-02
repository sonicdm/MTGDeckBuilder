import json
import pytest
import tempfile
import os
from mtg_deck_builder.db.bootstrap import bootstrap, bootstrap_inventory
from mtg_deck_builder.db.models import CardDB, CardSetDB, CardPrintingDB
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from mtg_deck_builder.db.setup import setup_database

def make_minimal_json(tmp_path):
    data = {
        "meta": {"date": "2024-01-01"},
        "data": {
            "ABC": {
                "name": "Test Set",
                "releaseDate": "2024-01-01",
                "block": "Test Block",
                "cards": [
                    {"uuid": "1111", "name": "Test Card", "rarity": "common"}
                ]
            }
        }
    }
    file = tmp_path / "cards.json"
    file.write_text(json.dumps(data), encoding="utf-8")
    return str(file)

def make_minimal_inventory(tmp_path):
    file = tmp_path / "inv.txt"
    file.write_text("1 Test Card", encoding="utf-8")
    return str(file)

def test_bootstrap_creates_db(tmp_path):
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    json_path = make_minimal_json(tmp_path)
    inv_path = make_minimal_inventory(tmp_path)
    bootstrap(json_path=json_path, inventory_path=inv_path, db_url=db_url, use_tqdm=False)
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    assert session.query(CardDB).count() == 1
    assert session.query(CardSetDB).count() == 1
    assert session.query(CardPrintingDB).count() == 1
    session.close()

def test_bootstrap_missing_json(tmp_path, caplog):
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    missing_json = tmp_path / "missing.json"
    bootstrap(json_path=str(missing_json), db_url=db_url, use_tqdm=False)
    assert any("File not found" in r.getMessage() for r in caplog.records)

def test_bootstrap_inventory_missing_file(tmp_path, caplog):
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    missing_inv = tmp_path / "missing_inv.txt"
    bootstrap_inventory(inventory_path=str(missing_inv), db_url=db_url, use_tqdm=False)
    assert any("File not found" in r.getMessage() for r in caplog.records)

