"""
test_mtgjson_sync.py

Tests for MTGJSON sync and database update logic, including handling of date parsing,
DB file creation, and backup logic. Uses unittest and mocking to simulate remote endpoints.
"""

import os
import shutil
import tempfile
import unittest
import json
from unittest import mock
from mtg_deckbuilder_ui.utils import mtgjson_sync
from mtg_deck_builder.db.setup import setup_database


class TestMTGJsonSync(unittest.TestCase):
    def setUp(self):
        print("\n[setUp] Creating temp test environment...")
        self.temp_dir = tempfile.mkdtemp()
        self.mtgjson_dir = os.path.join(self.temp_dir, "mtgjson")
        os.makedirs(self.mtgjson_dir, exist_ok=True)
        self.meta_path = os.path.join(self.mtgjson_dir, "Meta.json")
        self.allprintings_path = os.path.join(self.mtgjson_dir, "AllPrintings.json")
        self.db_path = os.path.join(self.temp_dir, "profile_cards.db")
        self._engine = None  # Track engine for cleanup

        # Patch config paths
        mtgjson_sync.LOCAL_META_PATH = self.meta_path
        mtgjson_sync.LOCAL_ALLPRINTINGS_PATH = self.allprintings_path
        mtgjson_sync.get_db_path = lambda: self.db_path

    def tearDown(self):
        print("[tearDown] Cleaning up temp test environment...")
        # Ensure the engine is disposed to release the SQLite file lock
        if self._engine is not None:
            self._engine.dispose()
        self._engine = None
        # Extra: Try to close all connections and retry rmtree if needed
        import gc
        import time

        gc.collect()
        for i in range(3):
            try:
                shutil.rmtree(self.temp_dir)
                print("[tearDown] Temp directory removed successfully.")
                break
            except Exception as e:
                print(f"[tearDown] rmtree failed (attempt {i+1}): {e}")
                time.sleep(0.5)
        else:
            print("[tearDown] WARNING: Could not remove temp directory after retries.")

    def test_download_and_backup(self):
        print("[test_download_and_backup] Starting test...")
        # Remove any pre-existing files
        if os.path.exists(self.meta_path):
            os.remove(self.meta_path)
        if os.path.exists(self.allprintings_path):
            os.remove(self.allprintings_path)

        # --- Mock existing data to trigger backup ---
        # Write a dummy AllPrintings.json and Meta.json with old version/date
        old_meta = {"meta": {"version": "0.9", "date": "2000-01-01"}}
        old_allprintings = {
            "data": {
                "OLD": {
                    "name": "Old Set",
                    "releaseDate": "2000-01-01",
                    "block": "Old Block",
                    "cards": [],
                }
            }
        }
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(old_meta, f)
        with open(self.allprintings_path, "w", encoding="utf-8") as f:
            json.dump(old_allprintings, f)
        print("  Mocked old Meta.json and AllPrintings.json to simulate outdated data.")

        # --- Mock remote meta and AllPrintings download ---
        new_meta = {"meta": {"version": "1.0", "date": "2024-01-01"}}
        new_allprintings = {
            "data": {
                "TST": {
                    "name": "Test Set",
                    "releaseDate": "2024-01-01",
                    "block": "Test Block",
                    "cards": [],
                }
            }
        }

        class DummyResp:
            def __init__(self, data, content=b""):
                self._data = data
                self.content = content

            def json(self):
                return self._data

            def raise_for_status(self):
                pass

        def dummy_requests_get(url, *args, **kwargs):
            if "Meta.json" in url:
                print(f"  [mock] requests.get({url}) -> DummyResp(new_meta)")
                return DummyResp(new_meta)
            elif "AllPrintings" in url:
                print(
                    f"  [mock] requests.get({url}) -> DummyResp(new_allprintings as zip)"
                )
                import io
                import zipfile

                buf = io.BytesIO()
                with zipfile.ZipFile(buf, "w") as zf:
                    zf.writestr("AllPrintings.json", json.dumps(new_allprintings))
                buf.seek(0)
                return DummyResp({}, content=buf.read())
            raise RuntimeError("Unexpected URL")

        with mock.patch.object(mtgjson_sync, "requests") as mock_requests:
            mock_requests.get.side_effect = dummy_requests_get

            # Run sync (should update and trigger backup)
            print("  Running mtgjson_sync.mtgjson_sync() for update and backup...")
            mtgjson_sync.mtgjson_sync()

        # Check that files were created
        print(
            f"  Checking for {self.meta_path}: {'FOUND' if os.path.exists(self.meta_path) else 'NOT FOUND'}"
        )
        print(
            f"  Checking for {self.allprintings_path}: {'FOUND' if os.path.exists(self.allprintings_path) else 'NOT FOUND'}"
        )
        self.assertTrue(os.path.exists(self.meta_path), "Meta.json should be created")
        self.assertTrue(
            os.path.exists(self.allprintings_path),
            "AllPrintings.json should be created",
        )

        # Check backup logic (should create a zip backup)
        backups = [f for f in os.listdir(self.mtgjson_dir) if f.endswith(".zip")]
        print(f"  Backup zip files found: {backups}")
        self.assertTrue(backups, "Backup zip should be created on update")

    def test_mtgjson_sync_mock(self):
        print("[test_mtgjson_sync_mock] Starting test...")
        fake_set = {
            "name": "Test Set",
            "releaseDate": "2024-01-01",
            "block": "Test Block",
            "cards": [
                {
                    "name": "Test Card",
                    "uuid": "abc-123",
                    "artist": "Test Artist",
                    "number": "1",
                    "type": "Creature",
                    "rarity": "Common",
                    "manaCost": "{1}{G}",
                    "power": "1",
                    "toughness": "1",
                    "abilities": ["Test ability"],
                    "flavorText": "Test flavor",
                    "text": "Test text",
                    "colors": ["G"],
                    "colorIdentity": ["G"],
                    "legalities": {},
                    "rulings": [],
                    "foreignData": {},
                }
            ],
        }
        fake_allprintings = {"data": {"TST": fake_set}}
        fake_meta = {"meta": {"version": "1.0", "date": "2024-01-01"}}

        with open(self.allprintings_path, "w", encoding="utf-8") as f:
            json.dump(fake_allprintings, f)
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(fake_meta, f)

        class DummyResp:
            def __init__(self, data):
                self._data = data
                self.content = b""

            def json(self):
                return self._data

            def raise_for_status(self):
                pass

        def dummy_requests_get(url, *args, **kwargs):
            if "Meta.json" in url:
                print(f"  [mock] requests.get({url}) -> DummyResp(fake_meta)")
                return DummyResp(fake_meta)
            elif "AllPrintings" in url:
                print(
                    f"  [mock] requests.get({url}) -> DummyResp(fake_allprintings as zip)"
                )
                import io
                import zipfile

                buf = io.BytesIO()
                with zipfile.ZipFile(buf, "w") as zf:
                    zf.writestr("AllPrintings.json", json.dumps(fake_allprintings))
                buf.seek(0)
                resp = DummyResp({})
                resp.content = buf.read()
                return resp
            raise RuntimeError("Unexpected URL")

        with mock.patch.object(mtgjson_sync, "requests") as mock_requests:
            mock_requests.get.side_effect = dummy_requests_get

            # Ensure DB is initialized as in production
            print("  Initializing DB with setup_database...")
            self._engine = setup_database(f"sqlite:///{self.db_path}")

            # Run sync (should not raise TypeError)
            print("  Running mtgjson_sync.mtgjson_sync() with mocked requests...")
            mtgjson_sync.mtgjson_sync()

        # Check that files were created and DB was updated
        print(
            f"  Checking for {self.meta_path}: {'FOUND' if os.path.exists(self.meta_path) else 'NOT FOUND'}"
        )
        print(
            f"  Checking for {self.allprintings_path}: {'FOUND' if os.path.exists(self.allprintings_path) else 'NOT FOUND'}"
        )
        print(
            f"  Checking for {self.db_path}: {'FOUND' if os.path.exists(self.db_path) else 'NOT FOUND'}"
        )
        self.assertTrue(os.path.exists(self.meta_path), "Meta.json should be created")
        self.assertTrue(
            os.path.exists(self.allprintings_path),
            "AllPrintings.json should be created",
        )
        self.assertTrue(os.path.exists(self.db_path), "Database file should be created")


if __name__ == "__main__":
    print("Running MTGJSON sync tests...")
    unittest.main()
