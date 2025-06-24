"""Test script for the YAML deck builder.

A command-line interface for testing deck building from YAML configurations.
It handles database setup, deck building, and analysis of the resulting deck.
"""

import os
import logging
import argparse
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Dict, Optional, Union, Callable, Any
import json
import time

from mtg_deck_builder.db.mtgjson_models.inventory import load_inventory_items
from mtg_deck_builder.yaml_builder.yaml_deckbuilder import build_deck_from_yaml
from mtg_deck_builder.db import get_session
from mtg_deck_builder.db.repository import SummaryCardRepository
from mtg_deck_builder.models.deck import Deck
from mtg_deck_builder.models.deck_config import DeckConfig
from mtg_deck_builder.models.deck_analyzer import DeckAnalyzer as DeckAnalyzerBase
from mtg_deck_builder.models.deck_exporter import DeckExporter

try:
    import pyperclip
    HAS_CLIPBOARD = True
except ImportError:
    HAS_CLIPBOARD = False



@dataclass
class PathConfig:
    """Configuration for file paths used by the deck builder."""
    db_path: Path
    all_printings: Path
    card_types: Path
    keywords: Path
    inventory: Path
    yaml_dir: Path

    @classmethod
    def get_default(cls) -> 'PathConfig':
        """Get default path configuration."""
        base_dir = Path(__file__).parent
        return cls(
            db_path=base_dir / "data/mtgjson/AllPrintings.sqlite",
            all_printings=base_dir / "data/mtgjson/AllPrintings.json",
            card_types=base_dir / "data/mtgjson/CardTypes.json",
            keywords=base_dir / "data/mtgjson/Keywords.json",
            inventory=base_dir / "inventory_files/card inventory.txt",
            yaml_dir=base_dir / "tests/sample_data/sample_deck_configs"
        )


class DeckAnalyzer:
    """Analyzes and prints information about a built deck."""
    
    def __init__(self, deck: Deck):
        self.deck = deck
        self.analyzer = DeckAnalyzerBase(deck)
    
    def print_basic_info(self) -> None:
        """Print basic deck information."""
        print("\nDeck Analysis:")
        print("=" * 40)
        print(f"Total Cards: {self.deck.size()}")
        lands = self.analyzer.count_lands()
        print(f"Lands: {lands}")
        print(f"Non-Lands: {self.deck.size() - lands}")

    def print_mana_curve(self) -> None:
        """Print mana curve analysis."""
        print("\nMana Curve:")
        curve = self.analyzer.mana_curve()
        for cmc, count in sorted(curve.items()):
            print(f"CMC {cmc}: {'*' * count} ({count})")

    def print_color_balance(self) -> None:
        """Print color balance analysis."""
        print("\nColor Balance:")
        colors = self.analyzer.color_balance()
        for color, count in sorted(colors.items()):
            print(f"  {color}: {count}")

    def print_card_types(self) -> None:
        """Print card type distribution."""
        print("\nCard Types:")
        type_counts = self.analyzer.count_card_types()
        if type_counts:
            sorted_types = sorted(
                type_counts.items(), key=lambda x: x[1], reverse=True
                )
            for type_name, count in sorted_types:
                print(f"  {type_name}: {count}")
        else:
            print("  No type information available")

    def print_sample_hand(self) -> None:
        """Print a sample hand."""
        print("\nSample Hand:")
        try:
            hand = self.deck.sample_hand(7)
            for card in hand:
                if card.is_basic_land():
                    print(f"  {card.name} (Basic Land)")
                else:
                    print(f"  {card.name} ({getattr(card, 'mana_cost', '')})")
        except ValueError as e:
            print(f"  Error: {e}")

    def print_deck_stats(self) -> None:
        """Print additional deck statistics."""
        print(f"\nRamp Spells: {self.analyzer.count_mana_ramp()}")
        print(f"Synergy Score: {self.analyzer.synergy_score():.1f}/10")

    def print_analysis(self) -> None:
        """Print complete deck analysis."""
        self.print_basic_info()
        self.print_mana_curve()
        self.print_color_balance()
        self.print_card_types()
        self.print_sample_hand()
        self.print_deck_stats()


class DeckBuilder:
    """Handles the deck building process."""
 
    def __init__(self, paths: PathConfig, logger: logging.Logger):
        self.paths = paths
        self.logger = logger

    def setup_database(self) -> None:
        """Ensure database exists and is bootstrapped."""
        # Ensure parent directory exists
        self.paths.db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            bootstrap(
                json_path=str(self.paths.all_printings),
                inventory_path=str(self.paths.inventory),
                db_url=f"sqlite:///{self.paths.db_path}",
                use_tqdm=True
            )
            self.logger.info("Database bootstrapped successfully")
        except Exception as e:
            raise RuntimeError(f"Failed to bootstrap database: {e}")

    def setup_callbacks(self) -> Dict[str, Callable]:
        """Set up callback functions for deck building process."""
        def log_callback(**kwargs: Any) -> None:
            event_name = kwargs.pop('event_name', 'unknown')
            self.logger.info(
                "Callback '{}' called with args: {}".format(
                    event_name, kwargs
                )
            )
        
        return {
            "after_inventory_load": log_callback,
            "after_deck_build": log_callback,
            "after_deck_finalize": log_callback,
            "after_mana_base": log_callback,
            "after_priority_cards": log_callback,
            "after_special_lands": log_callback,
            "after_fill_categories": log_callback,
            "after_fill_with_any": log_callback,
            "after_deck_config_load": log_callback,
        }

    def resolve_yaml_path(self, yaml_path: Union[str, Path]) -> str:
        """Resolve YAML path to string."""
        if isinstance(yaml_path, Path):
            return str(yaml_path)
        if os.path.isabs(yaml_path):
            return yaml_path
        return str(self.paths.yaml_dir / yaml_path)

    def get_yaml_path(self, user_input: Optional[str] = None) -> str:
        """Get YAML path from user input or list available configs."""
        if user_input:
            return self.resolve_yaml_path(user_input)

        print("\nAvailable deck configurations:")
        yaml_files = list(self.paths.yaml_dir.glob('*.yaml'))
        for i, yaml_file in enumerate(yaml_files, 1):
            print(f"  {i}. {yaml_file.name}")
        
        selection = input("\nEnter number of deck to test (or full path): ")
        try:
            idx = int(selection) - 1
            return str(yaml_files[idx])
        except (ValueError, IndexError):
            return self.resolve_yaml_path(selection)

    def build_deck(self, yaml_path: str) -> Optional[Deck]:
        """Build a deck from YAML configuration."""
        try:
            with get_session(db_url=f"sqlite:///{self.paths.db_path}") as session:
                load_inventory_items(str(self.paths.inventory), session)
                card_repo = SummaryCardRepository(session=session)
                print(f"Total Cards in Repository: {len(card_repo.get_all_cards())}")
                # inventory_repo = InventoryRepository(session)
                callbacks = self.setup_callbacks()
                
                self.logger.info("Building deck from YAML...")
                return build_deck_from_yaml(
                    yaml_path,
                    card_repo,
                    # inventory_repo=inventory_repo,
                    callbacks=callbacks,
                )
        except Exception as e:
            self.logger.error(f"Error building deck: {e}", exc_info=True)
            return None

    def print_deck_list(self, deck: Deck) -> None:
        """Print the deck list."""
        print("\nDeck List:")
        print("=" * 40)
        for card in deck.cards.values():
            if card.is_basic_land():
                print(
                    "{} | Type: Basic Land | Colors: {} | Qty: {}".format(
                        card.name,
                        ", ".join(card.color_identity or ['C']),
                        deck.get_quantity(card.name)
                    )
                )
            else:
                print(
                    "{} | Type: {} | Colors: {} | Qty: {}".format(
                        card.name,
                        card.type,
                        ", ".join(card.colors or ['C']),
                        deck.get_quantity(card.name)
                    )
                )


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    for logger_name in [
        'mtg_deck_builder.db.repository',
        'mtg_deck_builder.yaml_builder.yaml_deckbuilder',
        'mtg_deck_builder.deck_builder'
    ]:
        logging.getLogger(logger_name).setLevel(logging.DEBUG)
    return logging.getLogger(__name__)


def load_test_config(config_path: str) -> Dict[str, Any]:
    """Load a test configuration from a YAML file."""
    with open(config_path, 'r') as f:
        return json.load(f)



def main() -> None:
    """Main entry point for the deck builder test script."""
    parser = argparse.ArgumentParser(description='Test YAML deck builder')
    parser.add_argument('--yaml', help='Path to YAML deck config')
    parser.add_argument(
        '--verbose',
        '-v', action='store_true',
        help='Enable verbose logging'
        )
    args = parser.parse_args()
    
    logger = setup_logging(verbose=True)
    paths = PathConfig.get_default()
    
    try:
        builder = DeckBuilder(paths, logger)
        # builder.setup_database()
        
        yaml_path = builder.get_yaml_path(args.yaml)
        logger.info(f"Using YAML config: {yaml_path}")
        
        deck = builder.build_deck(yaml_path)
        if deck is None:
            logger.error("Deck build failed")
            return
            
        builder.print_deck_list(deck)
        DeckAnalyzer(deck).print_analysis()
        
        print("\nMTG Arena Import:")
        exporter = DeckExporter(deck)
        arena_import = exporter.mtg_arena_import()
        print(arena_import)
        
        if HAS_CLIPBOARD:
            while True:
                response = input(
                    "\nCopy MTG Arena import code to clipboard? (y/n): "
                    ).lower()
                if response in ['y', 'n']:
                    break
                print("Please enter 'y' or 'n'")
            
            if response == 'y':
                pyperclip.copy(arena_import)
                print(
                    "MTG Arena import code has been copied to your clipboard!"
                    )
        else:
            print("\nTo enable clipboard functionality, install pyperclip:")
            print("pip install pyperclip")
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
