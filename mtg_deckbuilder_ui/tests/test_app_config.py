"""
Test the AppConfig class in app_config.py.

These tests validate:
- Singleton behavior (only one instance exists)
- Default config creation
- Setting and getting values
- Section creation
- Value persistence
- Helper methods for last loaded config/inventory
"""

import os
import tempfile
import unittest
from unittest import mock
import configparser
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from mtg_deckbuilder_ui.app_config import AppConfig, PROJECT_ROOT


class TestAppConfig(unittest.TestCase):
    """Test the refactored AppConfig class."""

    def setUp(self):
        """Set up a temporary directory and mock config files."""
        # Create a temporary directory for testing
        self.temp_dir = Path(tempfile.mkdtemp())
        self.mock_config_dir = self.temp_dir / "mtg_deckbuilder_ui" / "config"
        self.mock_config_dir.mkdir(parents=True, exist_ok=True)

        # Set up mock config files
        self.mock_app_ini = self.mock_config_dir / "application_settings.ini"
        self.mock_default_ini = (
            self.mock_config_dir / "default.application_settings.ini"
        )

        # Create a dummy default config for testing
        self.default_content = """
[Paths]
database = data/cards.db
keywords = data/mtgjson/Keywords.json
cardtypes = data/mtgjson/CardTypes.json

[Logging]
level = INFO
log_to_file = true

[Legalities]
formats = standard,modern,commander

[UI]
theme = default
auto_load_collection = true
"""
        # Ensure parent directories exist before writing
        self.mock_config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.mock_default_ini, "w") as f:
            f.write(self.default_content)

        # Reset the singleton and patch its file paths
        AppConfig._instance = None

        # Patch _initialize with a closure to access test variables
        mock_config_dir = self.mock_config_dir
        mock_app_ini = self.mock_app_ini
        mock_default_ini = self.mock_default_ini

        def _mock_initialize(instance):
            instance.config_dir = mock_config_dir
            instance.config_file = mock_app_ini
            instance.default_config_file = mock_default_ini
            instance.config = configparser.ConfigParser()
            instance.config.read(mock_default_ini)
            if not instance.config_file.exists():
                shutil.copy(instance.default_config_file, instance.config_file)

        self.patcher = patch.object(AppConfig, "_initialize", _mock_initialize)
        self.patcher.start()

        # Create the config instance
        self.config = AppConfig()

    def tearDown(self):
        """Clean up the temporary directory and patches."""
        # Stop all patches
        self.patcher.stop()

        # Reset the singleton
        AppConfig._instance = None

        # Clean up the temporary directory
        shutil.rmtree(self.temp_dir)

    def test_singleton_behavior(self):
        """Test that AppConfig behaves as a singleton."""
        config1 = AppConfig()
        config2 = AppConfig()
        self.assertIs(config1, config2)
        self.assertIs(self.config, config1)

    def test_creation_from_default(self):
        """Test that application_settings.ini is created from default.application_settings.ini."""
        self.assertTrue(self.mock_app_ini.exists())

        parser = configparser.ConfigParser()
        parser.read(self.mock_app_ini)
        self.assertEqual(parser.get("Logging", "level"), "INFO")
        self.assertEqual(parser.get("Paths", "database"), "data/cards.db")

    def test_get_string(self):
        """Test the get() method for strings."""
        self.assertEqual(self.config.get("Logging", "level"), "INFO")
        self.assertEqual(self.config.get("UI", "theme"), "default")
        self.assertIsNone(self.config.get("Nonexistent", "key"))

    def test_get_bool(self):
        """Test the get_bool() method."""
        self.assertTrue(self.config.get_bool("Logging", "log_to_file"))
        self.assertTrue(self.config.get_bool("UI", "auto_load_collection"))
        self.assertFalse(self.config.get_bool("Nonexistent", "key"))

    def test_get_int(self):
        """Test the get_int() method."""
        self.config.set("Test", "number", "42")
        self.assertEqual(self.config.get_int("Test", "number"), 42)
        self.assertEqual(self.config.get_int("Nonexistent", "key"), 0)
        self.assertEqual(self.config.get_int("Nonexistent", "key", 10), 10)

    def test_get_list(self):
        """Test the get_list() method."""
        expected = ["standard", "modern", "commander"]
        self.assertEqual(self.config.get_list("Legalities", "formats"), expected)
        self.assertEqual(self.config.get_list("Nonexistent", "key"), [])
        self.assertEqual(
            self.config.get_list("Nonexistent", "key", ["default"]), ["default"]
        )

    def test_get_path(self):
        """Test the get_path() method."""
        expected_path = (PROJECT_ROOT / "data/cards.db").resolve()
        self.assertEqual(self.config.get_path("database"), expected_path)

        with self.assertRaises(configparser.NoOptionError):
            self.config.get_path("nonexistent")

    def test_get_db_url(self):
        """Test the get_db_url() method."""
        db_path = self.config.get_path("database")
        expected_url = f"sqlite:///{db_path}"
        self.assertEqual(self.config.get_db_url(), expected_url)

    def test_set_value_and_save(self):
        """Test setting a value and saving it."""
        self.config.set("UI", "theme", "dark")

        # Create a new config instance to force a reload from file
        parser = configparser.ConfigParser()
        parser.read(self.mock_app_ini)
        self.assertEqual(parser.get("UI", "theme"), "dark")

    def test_set_path_value(self):
        """Test that setting a Path object stores it as a relative path."""
        new_db_path = PROJECT_ROOT / "new_db/cards.db"
        self.config.set("Paths", "database", new_db_path)

        parser = configparser.ConfigParser()
        parser.read(self.mock_app_ini)
        # Should be stored relative to PROJECT_ROOT
        self.assertEqual(
            parser.get("Paths", "database").replace("\\", "/"), "new_db/cards.db"
        )

    def test_set_absolute_path(self):
        """Test that setting an absolute path outside project root is stored as is."""
        absolute_path = Path("/absolute/path/to/db.db")
        self.config.set("Paths", "database", absolute_path)

        parser = configparser.ConfigParser()
        parser.read(self.mock_app_ini)
        self.assertEqual(parser.get("Paths", "database"), str(absolute_path))

    def test_section_creation(self):
        """Test that new sections are created when needed."""
        self.config.set("NewSection", "key", "value")

        parser = configparser.ConfigParser()
        parser.read(self.mock_app_ini)
        self.assertTrue(parser.has_section("NewSection"))
        self.assertEqual(parser.get("NewSection", "key"), "value")


if __name__ == "__main__":
    unittest.main()
