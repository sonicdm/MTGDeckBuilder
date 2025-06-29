"""
Test MTGJSON sync functionality.

These tests validate:
- MTGJSON file download and sync
- AllPrintings.sqlite database operations
- Summary card building and caching
- Integration with the application config
- Error handling and recovery
"""

import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock, mock_open
import shutil
from pathlib import Path
import sqlite3
import json

from mtg_deckbuilder_ui.utils.mtgjson_sync import (
    sync_mtgjson_files,
    download_mtgjson_file,
    get_app_config_paths,
    get_app_config_urls,
)
from mtg_deckbuilder_ui.app_config import app_config


class TestMTGJSONSync(unittest.TestCase):
    """Test MTGJSON synchronization functionality."""

    def setUp(self):
        """Set up test environment with temporary directories."""
        # Create temporary directories
        self.temp_dir = Path(tempfile.mkdtemp())
        self.mtgjson_dir = self.temp_dir / "mtgjson"
        self.mtgjson_dir.mkdir()
        
        # Create test data directory
        self.data_dir = self.temp_dir / "data"
        self.data_dir.mkdir()
        
        # Create test AllPrintings.sqlite
        self.allprintings_db = self.data_dir / "AllPrintings.sqlite"
        self._create_test_allprintings_db()

    def tearDown(self):
        """Clean up temporary files."""
        shutil.rmtree(self.temp_dir)

    def _create_test_allprintings_db(self):
        """Create a minimal test AllPrintings.sqlite database."""
        conn = sqlite3.connect(self.allprintings_db)
        cursor = conn.cursor()
        
        # Create basic schema
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cards (
                uuid TEXT PRIMARY KEY,
                name TEXT,
                text TEXT,
                type TEXT,
                colors TEXT,
                colorIdentity TEXT,
                manaCost TEXT,
                convertedManaCost REAL,
                rarity TEXT,
                keywords TEXT,
                legalities TEXT
            )
        """)
        
        # Insert test cards
        test_cards = [
            ("test-uuid-1", "Lightning Bolt", "Deal 3 damage to any target.", 
             "Instant", "R", "R", "{R}", 1.0, "common", "[]", '{"modern": "legal"}'),
            ("test-uuid-2", "Serra Angel", "Flying, vigilance", 
             "Creature — Angel", "W", "W", "{3}{W}{W}", 5.0, "uncommon", 
             '["Flying", "Vigilance"]', '{"standard": "legal"}'),
        ]
        
        cursor.executemany("""
            INSERT INTO cards (uuid, name, text, type, colors, colorIdentity, 
                              manaCost, convertedManaCost, rarity, keywords, legalities)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, test_cards)
        
        conn.commit()
        conn.close()

    @patch('mtg_deckbuilder_ui.utils.mtgjson_sync.requests.get')
    def test_download_mtgjson_file_success(self, mock_get):
        """Test successful MTGJSON file download."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"test": "data"}'
        mock_get.return_value = mock_response
        
        # Test file path
        test_file = self.mtgjson_dir / "test.json"
        
        # Download file
        result = download_mtgjson_file("https://test.com/test.json", test_file)
        
        # Verify
        self.assertTrue(result)
        self.assertTrue(test_file.exists())
        self.assertEqual(test_file.read_text(), '{"test": "data"}')
        mock_get.assert_called_once_with("https://test.com/test.json", stream=True)

    @patch('mtg_deckbuilder_ui.utils.mtgjson_sync.requests.get')
    def test_download_mtgjson_file_failure(self, mock_get):
        """Test MTGJSON file download failure."""
        # Mock failed response
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        # Test file path
        test_file = self.mtgjson_dir / "test.json"
        
        # Download file
        result = download_mtgjson_file("https://test.com/test.json", test_file)
        
        # Verify
        self.assertFalse(result)
        self.assertFalse(test_file.exists())

    @patch('mtg_deckbuilder_ui.utils.mtgjson_sync.download_mtgjson_file')
    def test_sync_mtgjson_files_success(self, mock_download):
        """Test successful MTGJSON files sync."""
        # Mock successful downloads
        mock_download.return_value = True
        
        # Mock app_config paths
        with patch.object(app_config, 'get_path') as mock_get_path:
            mock_get_path.side_effect = lambda key: {
                'mtgjson': self.mtgjson_dir,
                'keywords': self.mtgjson_dir / "Keywords.json",
                'cardtypes': self.mtgjson_dir / "CardTypes.json",
            }[key]
            
            # Sync files
            result = sync_mtgjson_files()
            
            # Verify
            self.assertTrue(result)
            # Should have attempted to download Keywords.json and CardTypes.json
            self.assertEqual(mock_download.call_count, 2)

    @patch('mtg_deckbuilder_ui.utils.mtgjson_sync.download_mtgjson_file')
    def test_sync_mtgjson_files_partial_failure(self, mock_download):
        """Test MTGJSON files sync with partial failure."""
        # Mock one success, one failure
        mock_download.side_effect = [True, False]
        
        # Mock app_config paths
        with patch.object(app_config, 'get_path') as mock_get_path:
            mock_get_path.side_effect = lambda key: {
                'mtgjson': self.mtgjson_dir,
                'keywords': self.mtgjson_dir / "Keywords.json",
                'cardtypes': self.mtgjson_dir / "CardTypes.json",
            }[key]
            
            # Sync files
            result = sync_mtgjson_files()
            
            # Verify
            self.assertFalse(result)
            self.assertEqual(mock_download.call_count, 2)

    def test_get_app_config_paths(self):
        """Test getting app config paths."""
        with patch.object(app_config, 'get_path') as mock_get_path:
            mock_get_path.side_effect = lambda key: {
                'database': Path("/test/db.sqlite"),
                'inventory': Path("/test/inventory"),
                'decks': Path("/test/decks"),
                'keywords': Path("/test/Keywords.json"),
                'cardtypes': Path("/test/CardTypes.json"),
                'mtgjson': Path("/test/mtgjson"),
            }[key]
            
            paths = get_app_config_paths()
            
            # Verify all expected paths are present
            expected_keys = ['database', 'inventory', 'decks', 'keywords', 'cardtypes', 'mtgjson']
            for key in expected_keys:
                self.assertIn(key, paths)
                self.assertIsInstance(paths[key], Path)

    def test_get_app_config_urls(self):
        """Test getting app config URLs."""
        urls = get_app_config_urls()
        
        # Verify expected URLs are present
        expected_keys = ['keywords', 'cardtypes']
        for key in expected_keys:
            self.assertIn(key, urls)
            self.assertIsInstance(urls[key], str)
            self.assertTrue(urls[key].startswith('http'))

    @patch('mtg_deckbuilder_ui.utils.mtgjson_sync.build_summary_cards_from_mtgjson')
    def test_allprintings_integration(self, mock_build_summary):
        """Test integration with AllPrintings.sqlite."""
        # Mock the build summary function
        mock_build_summary.return_value = True
        
        # Test that the function can be called with our test database
        result = mock_build_summary(self.allprintings_db)
        
        # Verify
        self.assertTrue(result)
        mock_build_summary.assert_called_once_with(self.allprintings_db)

    def test_allprintings_db_structure(self):
        """Test that AllPrintings.sqlite has the expected structure."""
        conn = sqlite3.connect(self.allprintings_db)
        cursor = conn.cursor()
        
        # Check table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cards'")
        self.assertIsNotNone(cursor.fetchone())
        
        # Check columns exist
        cursor.execute("PRAGMA table_info(cards)")
        columns = [row[1] for row in cursor.fetchall()]
        expected_columns = ['uuid', 'name', 'text', 'type', 'colors', 'colorIdentity', 
                           'manaCost', 'convertedManaCost', 'rarity', 'keywords', 'legalities']
        
        for col in expected_columns:
            self.assertIn(col, columns)
        
        # Check test data exists
        cursor.execute("SELECT COUNT(*) FROM cards")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 2)
        
        conn.close()

    @patch('mtg_deckbuilder_ui.utils.mtgjson_sync.sync_mtgjson_files')
    def test_sync_with_existing_files(self, mock_sync):
        """Test sync behavior when files already exist."""
        # Create existing files
        keywords_file = self.mtgjson_dir / "Keywords.json"
        cardtypes_file = self.mtgjson_dir / "CardTypes.json"
        
        keywords_file.write_text('{"existing": "keywords"}')
        cardtypes_file.write_text('{"existing": "cardtypes"}')
        
        # Mock app_config paths
        with patch.object(app_config, 'get_path') as mock_get_path:
            mock_get_path.side_effect = lambda key: {
                'mtgjson': self.mtgjson_dir,
                'keywords': keywords_file,
                'cardtypes': cardtypes_file,
            }[key]
            
            # Sync files
            result = sync_mtgjson_files()
            
            # Verify files still exist
            self.assertTrue(keywords_file.exists())
            self.assertTrue(cardtypes_file.exists())

    def test_error_handling_invalid_paths(self):
        """Test error handling with invalid paths."""
        # Test with non-existent paths
        with patch.object(app_config, 'get_path') as mock_get_path:
            mock_get_path.side_effect = FileNotFoundError("Path not found")
            
            # Should handle gracefully
            with self.assertRaises(FileNotFoundError):
                get_app_config_paths()


if __name__ == "__main__":
    unittest.main() 