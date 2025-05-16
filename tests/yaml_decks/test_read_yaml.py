import unittest
from mtg_deck_builder.templating.yaml_reader import load_yaml_deck
from tests.helpers import get_sample_data_path

class TestYamlParsing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.yaml_path = get_sample_data_path('dmir.yaml')

    def test_load_yaml(self):
        """Test loading the YAML file and verifying its contents."""
        yaml_criteria = load_yaml_deck(self.yaml_path)

        # Check if YAML is a dictionary
        self.assertIsInstance(yaml_criteria, dict, "YAML file should be loaded as a dictionary")

        # Verify expected keys exist
        self.assertIn('deck', yaml_criteria, "YAML should contain 'deck' key")
        self.assertIn('categories', yaml_criteria, "YAML should contain 'categories' key")

        # Check deck-specific details
        deck_info = yaml_criteria.get('deck', {})
        self.assertIn('colors', deck_info, "Deck section should have 'colors'")
        self.assertIsInstance(deck_info['colors'], list, "Colors should be a list")

        # Check if categories contain expected structure
        categories = yaml_criteria.get('categories', {})
        self.assertIsInstance(categories, dict, "Categories should be a dictionary")

        for category, rules in categories.items():
            self.assertIsInstance(rules, dict, f"Rules for category {category} should be a dictionary")

            if 'preferred_keywords' in rules:
                self.assertIsInstance(rules['preferred_keywords'], list, "preferred_keywords should be a list")
            if 'priority_text' in rules:
                self.assertIsInstance(rules['priority_text'], list, "priority_text should be a list")


if __name__ == "__main__":
    unittest.main()