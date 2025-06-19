# Typed Gradio field definitions for deck config

from typing import Literal, TypedDict, Optional, Union

ComponentType = Literal["Textbox", "Checkbox", "CheckboxGroup", "Slider", "Dropdown"]


class DeckFieldSchema(TypedDict):
    component: ComponentType
    label: str
    default: Union[str, int, bool, list]
    options: Optional[list]


deck_fields = {
    "name": {
        "component": "Textbox",
        "label": "Deck Name",
        "default": "Unnamed Deck",
        "options": None,
    },
    "colors": {
        "component": "CheckboxGroup",
        "label": "Deck Colors",
        "default": ["W", "G"],
        "options": ["W", "U", "B", "R", "G"],
    },
    "size": {
        "component": "Slider",
        "label": "Deck Size",
        "default": 60,
        "options": [40, 100],
    },
    "max_card_copies": {
        "component": "Slider",
        "label": "Max Copies per Card",
        "default": 4,
        "options": [1, 4],
    },
    "allow_colorless": {
        "component": "Checkbox",
        "label": "Allow Colorless Cards",
        "default": True,
        "options": None,
    },
    "legalities": {
        "component": "Dropdown",
        "label": "Format(s)",
        "default": ["standard"],
        "options": ["standard", "modern", "commander"],
    },
    "owned_cards_only": {
        "component": "Checkbox",
        "label": "Use Owned Cards Only",
        "default": True,
        "options": None,
    },
}
