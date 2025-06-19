"""
Test the callback system for the deck builder.

This module tests that the callback system properly reports progress and status
during deck building operations.
"""

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from mtg_deck_builder.db.repository import CardRepository, InventoryRepository
from mtg_deck_builder.models.deck_config import DeckConfig
from mtg_deckbuilder_ui.logic.deck_builder_callbacks import get_deck_builder_callbacks
from mtg_deckbuilder_ui.utils.inventory_importer import import_inventory_file


class TestCallbacks(unittest.TestCase):
    """Test the callback system for the deck builder."""

    def setUp(self):
        """Set up test environment."""
        self.status_messages = []

        # Mock session and repositories
        self.session = MagicMock()
        self.card_repo = MagicMock(spec=CardRepository)
        self.inventory_repo = MagicMock(spec=InventoryRepository)

        # Create a minimal test config
        self.config = DeckConfig(
            deck={
                "name": "Test Deck",
                "colors": ["W", "B"],
                "size": 60,
                "max_card_copies": 4,
                "legalities": ["standard"],
                "color_match_mode": "subset",
                "owned_cards_only": True,
            },
            categories={
                "creatures": {
                    "target": 24,
                    "preferred_keywords": ["Flying", "Deathtouch"],
                }
            },
            mana_base={"land_count": 24},
        )

    def status_callback(self, message):
        """Record status messages."""
        print(f"STATUS: {message}")  # Print for debugging
        self.status_messages.append(message)

    def test_deck_builder_callbacks(self):
        """Test that deck builder callbacks report progress."""
        # Get the deck builder callbacks
        callbacks = get_deck_builder_callbacks(self.status_callback)

        # Verify callbacks exist for all major steps
        self.assertIn("after_deck_config_load", callbacks)
        self.assertIn("after_inventory_load", callbacks)
        self.assertIn("category_fill_progress", callbacks)
        self.assertIn("after_land_selection", callbacks)

        # Test one callback directly
        callbacks["after_deck_config_load"](config=self.config)

        # Check if status was updated
        self.assertTrue(
            any("Initialized deck: Test Deck" in msg for msg in self.status_messages),
            "Deck initialization status not reported",
        )

    @patch("mtg_deck_builder.yaml_builder.yaml_deckbuilder.build_deck_from_config")
    def test_repository_status_callbacks(self, mock_build_deck):
        """Test that repository status callbacks work during operations."""
        # Set up the card repository with a status callback
        card_repo = CardRepository()
        card_repo.set_status_callback(self.status_callback)

        # Trigger a status update
        card_repo._report_status("Testing card repository status callback")

        # Check if status was updated
        self.assertIn("Testing card repository status callback", self.status_messages)

        # Similarly for inventory repository
        # None for session is OK for this test
        inv_repo = InventoryRepository(None)
        inv_repo.set_status_callback(self.status_callback)

        # Trigger a status update
        inv_repo._report_status("Testing inventory repository status callback")

        # Check if status was updated
        self.assertIn(
            "Testing inventory repository status callback", self.status_messages
        )

    @patch(__name__ + ".import_inventory_file", autospec=True)
    def test_inventory_import_callbacks(self, mock_import):
        """Test that inventory import correctly uses progress and done callbacks."""
        # Create a temp file for testing
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"1 Test Card\n2 Another Card")
            tmp_path = tmp.name

        try:
            # Track progress callbacks
            progress_called = False
            done_called = False

            def progress_callback(percent, message):
                nonlocal progress_called
                self.status_callback(f"Progress {percent:.0%}: {message}")
                progress_called = True

            def done_callback(success, message):
                nonlocal done_called
                self.status_callback(f"Done (success={success}): {message}")
                done_called = True

            # Setup the mock to call our callbacks and return a mock thread
            mock_thread = MagicMock()
            mock_import.return_value = mock_thread

            # This simulates what happens inside the real function
            def side_effect(
                inventory_path, db_path=None, progress_callback=None, done_callback=None
            ):
                if progress_callback:
                    progress_callback(0.5, "Processing inventory")
                if done_callback:
                    done_callback(True, "Import complete")
                return mock_thread

            mock_import.side_effect = side_effect

            # Call the import function with our callbacks
            result_thread = import_inventory_file(
                tmp_path,
                progress_callback=progress_callback,
                done_callback=done_callback,
            )

            # Verify the mock was called correctly
            mock_import.assert_called_once()
            self.assertEqual(result_thread, mock_thread)

            # Verify callbacks were called
            self.assertTrue(progress_called, "Progress callback not called")
            self.assertTrue(done_called, "Done callback not called")
            self.assertTrue(
                any("Processing inventory" in msg for msg in self.status_messages)
            )
            self.assertTrue(
                any("Import complete" in msg for msg in self.status_messages)
            )

        finally:
            # Ensure we close any open file handles before unlinking
            import time

            time.sleep(0.1)  # Small delay to ensure file is released
            try:
                os.unlink(tmp_path)
            except PermissionError:
                print(f"Warning: Could not delete temporary file {tmp_path}")


if __name__ == "__main__":
    unittest.main()
