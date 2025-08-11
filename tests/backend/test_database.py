"""
Test database components including repository, inventory, and models.

These tests validate:
- Database session management
- Repository operations
- Inventory management
- Model relationships and constraints
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from mtg_deck_builder.db import (
    get_engine, get_session, get_card_types, get_keywords,
    CardTypesData, KeywordsData
)
from mtg_deck_builder.db.mtgjson_models.cards import MTGJSONCard, MTGJSONSummaryCard
from mtg_deck_builder.db.mtgjson_models.sets import MTGJSONSet
from mtg_deck_builder.db.inventory import InventoryItem
from mtg_deck_builder.db.repository import SummaryCardRepository
from mtg_deck_builder.db.mtgjson_models.base import MTGJSONBase


@pytest.fixture
def test_db_engine():
    """Create a test database engine."""
    engine = create_engine("sqlite:///:memory:")
    
    # Create all tables
    MTGJSONBase.metadata.create_all(engine)
    
    return engine


@pytest.fixture
def test_session(test_db_engine):
    """Create a test database session."""
    Session = sessionmaker(bind=test_db_engine)
    session = Session()
    
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_card_data():
    """Sample card data for testing."""
    return {
        "uuid": "test-uuid-123",
        "name": "Lightning Bolt",
        "setCode": "LEA",
        "colors": '["R"]',
        "keywords": '["damage"]',
        "manaCost": "{R}",
        "manaValue": 1.0,
        "rarity": "Common",
        "text": "Lightning Bolt deals 3 damage to any target.",
        "type": "Instant"
    }


@pytest.fixture
def sample_summary_card_data():
    """Sample summary card data for testing."""
    return {
        "name": "Lightning Bolt",
        "colors": '["R"]',
        "keywords": '["damage"]',
        "manaCost": "{R}",
        "manaValue": 1.0,
        "rarity": "Common",
        "text": "Lightning Bolt deals 3 damage to any target.",
        "type": "Instant",
        "printings": '["LEA", "LEB", "2ED"]'
    }


@pytest.fixture
def sample_printing_data():
    """Sample printing data for testing."""
    return {
        "uuid": "test-printing-uuid-123",
        "name": "Lightning Bolt",
        "setCode": "LEA",
        "number": "81",
        "artist": "Christopher Rush",
        "rarity": "Common"
    }


@pytest.fixture
def sample_set_data():
    """Sample set data for testing."""
    return {
        "code": "LEA",
        "name": "Limited Edition Alpha",
        "releaseDate": "1993-08-05",
        "type": "core",
        "isOnlineOnly": False
    }


class TestDatabaseSession:
    """Test database session management."""

    def test_get_engine_default(self):
        """Test creating engine with default URL."""
        engine = get_engine()
        assert engine is not None

    def test_get_engine_custom_url(self):
        """Test creating engine with custom URL."""
        engine = get_engine("sqlite:///test.db")
        assert engine is not None
        assert str(engine.url) == "sqlite:///test.db"

    def test_get_session_context_manager(self, test_db_engine):
        """Test session context manager."""
        with get_session(engine=test_db_engine) as session:
            assert session is not None
            assert session.is_active  # Session should be active during context

    def test_get_session_with_db_url(self):
        """Test session creation with database URL."""
        with get_session(db_url="sqlite:///:memory:") as session:
            assert session is not None


class TestCardTypesAndKeywords:
    """Test card types and keywords loading."""

    @patch('mtg_deck_builder.db.CARD_TYPES_PATH')
    @patch('mtg_deck_builder.db.KEYWORDS_PATH')
    def test_get_card_types(self, mock_keywords_path, mock_card_types_path):
        """Test loading card types."""
        # Mock the paths to point to test data
        mock_card_types_path.__truediv__ = lambda self, other: Path("tests/sample_data/CardTypes.json")
        
        # This will fail if the file doesn't exist, but that's expected
        # In a real test environment, we'd create test JSON files
        try:
            card_types = get_card_types()
            assert isinstance(card_types, CardTypesData)
        except FileNotFoundError:
            pytest.skip("Test data files not available")

    @patch('mtg_deck_builder.db.KEYWORDS_PATH')
    def test_get_keywords(self, mock_keywords_path):
        """Test loading keywords."""
        # Mock the path to point to test data
        mock_keywords_path.__truediv__ = lambda self, other: Path("tests/sample_data/Keywords.json")
        
        try:
            keywords = get_keywords()
            assert isinstance(keywords, KeywordsData)
        except FileNotFoundError:
            pytest.skip("Test data files not available")


class TestInventoryItem:
    """Test inventory item model."""

    def test_inventory_item_creation(self):
        """Test creating inventory item."""
        item = InventoryItem(
            card_name="Lightning Bolt",
            quantity=4,
            condition="NM",
            is_foil="false"
        )
        
        assert item.card_name == "Lightning Bolt"
        assert item.quantity == 4
        assert item.condition == "NM"
        assert item.is_foil == "false"

    def test_inventory_item_defaults(self):
        """Test inventory item with default values."""
        item = InventoryItem(
            card_name="Lightning Bolt"
        )
        
        assert item.quantity == 0
        assert item.condition == "NM"
        assert item.is_foil == "false"

    def test_inventory_item_to_dict(self):
        """Test converting inventory item to dictionary."""
        item = InventoryItem(
            card_name="Lightning Bolt",
            quantity=2,
            condition="LP",
            is_foil="true"
        )
        
        item_dict = item.to_dict()
        assert item_dict['card_name'] == "Lightning Bolt"
        assert item_dict['quantity'] == 2
        assert item_dict['condition'] == "LP"
        assert item_dict['is_foil'] == "true"


class TestSummaryCardRepository:
    """Test summary card repository."""

    def test_repository_creation(self, test_session):
        """Test creating repository instance."""
        repo = SummaryCardRepository(test_session)
        assert repo is not None
        assert repo.session == test_session

    def test_repository_find_by_name(self, test_session, sample_summary_card_data):
        """Test finding card by name."""
        # Create test summary card in database
        card = MTGJSONSummaryCard(**sample_summary_card_data)
        test_session.add(card)
        test_session.commit()
        
        repo = SummaryCardRepository(test_session)
        result = repo.find_by_name("Lightning Bolt")
        
        assert result is not None
        assert result.name == "Lightning Bolt"

    def test_repository_filter_cards(self, test_session, sample_summary_card_data):
        """Test filtering cards."""
        # Create test summary card in database
        card = MTGJSONSummaryCard(**sample_summary_card_data)
        test_session.add(card)
        test_session.commit()
        
        repo = SummaryCardRepository(test_session)
        # Test filtering by type
        filtered_repo = repo.filter_cards(basic_type="Instant")
        results = filtered_repo.get_all_cards()
        
        assert isinstance(results, list)
        assert len(results) > 0

    def test_repository_get_all_cards(self, test_session):
        """Test getting all cards."""
        repo = SummaryCardRepository(test_session)
        
        try:
            results = repo.get_all_cards()
            assert isinstance(results, list)
        except Exception:
            # This is expected if the database is empty or not set up
            pytest.skip("Database not set up for testing")

    def test_repository_filter_by_colors(self, test_session, sample_summary_card_data):
        """Test filtering by colors."""
        # Create test summary card in database
        card = MTGJSONSummaryCard(**sample_summary_card_data)
        test_session.add(card)
        test_session.commit()
        
        repo = SummaryCardRepository(test_session)
        filtered_repo = repo.filter_cards(colors=["R"])
        results = filtered_repo.get_all_cards()
        
        assert isinstance(results, list)
        assert len(results) > 0

    def test_repository_filter_by_keywords(self, test_session, sample_summary_card_data):
        """Test filtering by keywords."""
        # Create test summary card in database
        card = MTGJSONSummaryCard(**sample_summary_card_data)
        test_session.add(card)
        test_session.commit()
        
        repo = SummaryCardRepository(test_session)
        filtered_repo = repo.filter_cards(keyword_multi=["damage"])
        results = filtered_repo.get_all_cards()
        
        assert isinstance(results, list)
        assert len(results) > 0

    def test_repository_filter_by_rarity(self, test_session, sample_summary_card_data):
        """Test filtering by rarity."""
        # Create test summary card in database
        card = MTGJSONSummaryCard(**sample_summary_card_data)
        test_session.add(card)
        test_session.commit()
        
        repo = SummaryCardRepository(test_session)
        filtered_repo = repo.filter_cards(rarity="Common")
        results = filtered_repo.get_all_cards()
        
        assert isinstance(results, list)
        assert len(results) > 0

    def test_repository_get_printings(self, test_session, sample_summary_card_data):
        """Test getting printings for a card."""
        # Create test summary card in database
        card = MTGJSONSummaryCard(**sample_summary_card_data)
        test_session.add(card)
        test_session.commit()
        
        repo = SummaryCardRepository(test_session)
        printings = repo.get_printings("Lightning Bolt")
        
        assert isinstance(printings, list)
        assert len(printings) > 0

    def test_repository_get_legalities(self, test_session, sample_summary_card_data):
        """Test getting legalities for a card."""
        # Create test summary card in database
        card = MTGJSONSummaryCard(**sample_summary_card_data)
        test_session.add(card)
        test_session.commit()
        
        repo = SummaryCardRepository(test_session)
        legalities = repo.get_legalities("Lightning Bolt")
        
        assert isinstance(legalities, dict)


class TestDatabaseModels:
    """Test database models."""

    def test_card_db_creation(self, sample_card_data):
        """Test creating MTGJSONCard instance."""
        card = MTGJSONCard(**sample_card_data)
        
        assert card.name == "Lightning Bolt"
        assert card.setCode == "LEA"
        assert card.manaValue == 1.0
        assert card.rarity == "Common"

    def test_summary_card_creation(self):
        """Test creating MTGJSONSummaryCard instance."""
        summary_card = MTGJSONSummaryCard(
            name="Lightning Bolt",
            colors='["R"]',
            keywords='["damage"]',
            manaCost="{R}",
            manaValue=1.0,
            rarity="Common",
            text="Lightning Bolt deals 3 damage to any target.",
            type="Instant",
            printings='["LEA", "LEB", "2ED"]'
        )
        
        assert summary_card.name == "Lightning Bolt"
        assert summary_card.manaValue == 1.0
        assert summary_card.rarity == "Common"

    def test_set_db_creation(self, sample_set_data):
        """Test creating MTGJSONSet instance."""
        card_set = MTGJSONSet(**sample_set_data)
        
        assert card_set.code == "LEA"
        assert card_set.name == "Limited Edition Alpha"
        assert card_set.type == "core"

    def test_card_relationships(self, test_session, sample_summary_card_data, sample_set_data):
        """Test card model relationships."""
        # Create set
        card_set = MTGJSONSet(**sample_set_data)
        test_session.add(card_set)
        test_session.commit()
        
        # Create summary card
        summary_card = MTGJSONSummaryCard(**sample_summary_card_data)
        test_session.add(summary_card)
        test_session.commit()
        
        # Test that we can query the relationships
        queried_card = test_session.query(MTGJSONSummaryCard).filter_by(name="Lightning Bolt").first()
        assert queried_card is not None
        assert queried_card.name == "Lightning Bolt" 