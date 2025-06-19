# mtg_deckbuilder_ui/ui/ui_objects.py

from typing import Dict, Any, Optional, List, Union, Type, get_type_hints, Callable
import gradio as gr
import re
import yaml
from mtg_deck_builder.models.deck_config import DeckConfig
from abc import ABC, abstractmethod


class UIBase(ABC):
    @abstractmethod
    def get_components(self) -> Dict[str, gr.components.Component]:
        """
        Return a dictionary of all components in this UI object.
        Should be overridden by subclasses.
        """
        raise NotImplementedError

    def get_component_map(self) -> Dict[str, gr.components.Component]:
        """
        Alias for get_components for compatibility.
        """
        return self.get_components()

    @abstractmethod
    def render(self):
        """
        Renders the component in the current Gradio Blocks context.
        """
        raise NotImplementedError


class UIElement(UIBase):
    """
    Represents a single Gradio component with a name for unified state management.
    Now uses a factory to create the component inside the correct Gradio context.
    """

    def __init__(
        self, name: str, component_factory: Callable[[], gr.components.Component]
    ):
        self.name = name
        self._component_factory = component_factory
        self._component = None
        self.sanitizers: List[Callable[[Any], Any]] = []

    def get_component(self) -> gr.components.Component:
        return self._component

    def get_name(self) -> str:
        return self.name

    def set_state(self, value: Any) -> gr.update:
        """
        Return a Gradio update object for setting the component's value in a callback.
        """
        return gr.update(value=value)

    def get_state(self, value: Any) -> Any:
        """
        This function assumes you provide the live value from inputs in your callback.
        """
        return value

    def render(self):
        """
        Render the Gradio component inside the current context.
        """
        self._component = self._component_factory()

    def add_sanitizer(self, sanitizer: Callable[[Any], Any]):
        """
        Add a sanitizer function to clean input values.

        Args:
            sanitizer: Function that takes a value and returns sanitized value
        """
        self.sanitizers.append(sanitizer)

    def sanitize(self, value: Any) -> Any:
        """
        Apply all registered sanitizers to a value.

        Args:
            value: Value to sanitize

        Returns:
            Sanitized value
        """
        result = value
        for sanitizer in self.sanitizers:
            result = sanitizer(result)
        return result

    def add_comma_list_sanitizer(self):
        """
        Add a sanitizer that converts comma-separated strings to lists.
        """

        def sanitize_comma_list(value: str) -> List[str]:
            if not value:
                return []
            return [x.strip() for x in value.split(",") if x.strip()]

        self.add_sanitizer(sanitize_comma_list)

    def add_yaml_sanitizer(self):
        """
        Add a sanitizer that parses YAML strings.
        """

        def sanitize_yaml(value: str) -> Any:
            if not value:
                return {}
            try:
                return yaml.safe_load(value)
            except yaml.YAMLError:
                return {}

        self.add_sanitizer(sanitize_yaml)

    def add_number_sanitizer(
        self, min_value: Optional[float] = None, max_value: Optional[float] = None
    ):
        """
        Add a sanitizer that ensures numeric values are within bounds.

        Args:
            min_value: Minimum allowed value
            max_value: Maximum allowed value
        """

        def sanitize_number(value: Any) -> float:
            try:
                num = float(value)
                if min_value is not None:
                    num = max(min_value, num)
                if max_value is not None:
                    num = min(max_value, num)
                return num
            except (ValueError, TypeError):
                return min_value if min_value is not None else 0.0

        self.add_sanitizer(sanitize_number)

    def add_regex_sanitizer(self, pattern: str, replacement: str = ""):
        """
        Add a sanitizer that applies regex replacement.

        Args:
            pattern: Regex pattern to match
            replacement: String to replace matches with
        """

        def sanitize_regex(value: str) -> str:
            if not value:
                return ""
            return re.sub(pattern, replacement, value)

        self.add_sanitizer(sanitize_regex)

    def get_components(self) -> Dict[str, gr.components.Component]:
        """
        Return a dictionary of all components in this element.
        """
        return {self.get_name(): self.get_component()}


class UIContainer(UIBase):
    """
    Wraps multiple UIElements or nested UIContainers with layout instructions.
    """

    def __init__(
        self,
        layout_type: str,
        label: Optional[str] = None,
        children: Optional[List[Union["UIElement", "UIContainer"]]] = None,
    ):
        self.layout_type = layout_type
        self.label = label
        self.children = children or []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def render(self):
        """Render the container and its children."""
        if self.layout_type == "row":
            with gr.Row():
                for child in self.children:
                    child.render()
        elif self.layout_type == "column":
            with gr.Column():
                for child in self.children:
                    child.render()
        elif self.layout_type == "accordion":
            with gr.Accordion(label=self.label):
                for child in self.children:
                    child.render()
        elif self.layout_type == "group":
            with gr.Group():
                for child in self.children:
                    child.render()
        else:
            raise ValueError(f"Unsupported layout type: {self.layout_type}")

    def get_components(self) -> Dict[str, gr.components.Component]:
        """
        Return a dictionary of all components in this container.
        """
        components = {}
        for child in self.children:
            components.update(child.get_components())
        return components


class UISection(UIBase):
    """
    Represents a logical section of the UI, grouping multiple UIElements.
    """

    def __init__(self, name: str, label: Optional[str] = None):
        self.name = name
        self.label = label or name
        self.elements: Dict[str, UIElement] = {}
        self.layout: Optional[UIContainer] = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def add_element(self, element: UIElement):
        self.elements[element.get_name()] = element

    def get_element(self, name: str) -> Optional[UIElement]:
        return self.elements.get(name)

    def get_components(self) -> Dict[str, gr.components.Component]:
        """
        Return a dictionary of all components in this section.
        """
        components = {}
        if self.layout:
            components.update(self.layout.get_components())

        for element in self.elements.values():
            components.update(element.get_components())

        return components

    def get_state(self, values: Dict[str, Any]) -> Dict[str, Any]:
        """
        Expects a mapping from element names to live input values.
        """
        return {
            k: self.elements[k].get_state(v)
            for k, v in values.items()
            if k in self.elements
        }

    def set_state(self, state: Dict[str, Any]) -> Dict[str, gr.update]:
        """
        Returns Gradio update objects for components in this section.
        """
        return {
            k: self.elements[k].set_state(v)
            for k, v in state.items()
            if k in self.elements
        }

    def keys(self):
        return self.elements.keys()

    def items(self):
        return self.elements.items()

    def values(self):
        return self.elements.values()

    def set_layout(self, layout: UIContainer):
        """
        Define the layout for this section.
        """
        self.layout = layout

    def render(self):
        """
        Render all UIElement components in this section.
        """
        if self.layout:
            self.layout.render()
        else:
            for element in self.elements.values():
                element.render()


class UITab(UIBase):
    """
    Represents a Gradio tab composed of multiple UISections.
    """

    def __init__(self, tab_name: str):
        self.tab_name = tab_name
        self.sections: Dict[str, UISection] = {}
        self.validators: Dict[str, Callable[[Any], bool]] = {}
        self.error_messages: Dict[str, str] = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def add_section(self, section: UISection):
        self.sections[section.name] = section

    def get_section(self, name: str) -> Optional[UISection]:
        return self.sections.get(name)

    def get_element(self, name: str) -> Optional[UIElement]:
        for section in self.sections.values():
            if name in section.elements:
                return section.elements[name]
        return None

    def get_components(self) -> Dict[str, gr.components.Component]:
        """
        Flatten all components from all sections for easy wiring.
        """
        components = {}
        for section in self.sections.values():
            components.update(section.get_components())
        return components

    def get_state(self, inputs: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Aggregate state from all sections, given a nested dict of live values.
        """
        return {
            name: section.get_state(values)
            for name, (section, values) in (
                (k, (self.sections[k], v))
                for k, v in inputs.items()
                if k in self.sections
            )
        }

    def set_state(
        self, state: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, gr.update]]:
        """
        Return update objects for all sections given a nested state dict.

        Args:
            state: A dictionary mapping section names to their state dictionaries.

        Returns:
            A dictionary mapping section names to their update dictionaries.
        """
        updates: Dict[str, Dict[str, gr.update]] = {}
        for name, values in state.items():
            section = self.sections.get(name)
            if section is not None:
                updates[name] = section.set_state(values)
        return updates

    def add_validator(
        self, element_name: str, validator: Callable[[Any], bool], error_message: str
    ):
        """
        Add a validator function for a specific element.

        Args:
            element_name: Name of the element to validate
            validator: Function that takes a value and returns True if valid
            error_message: Message to show if validation fails
        """
        self.validators[element_name] = validator
        self.error_messages[element_name] = error_message

    def validate(self, values: Dict[str, Any]) -> List[str]:
        """
        Validate all form values against registered validators.

        Args:
            values: Dictionary of element names to their values

        Returns:
            List of error messages, empty if all valid
        """
        errors = []
        for element_name, validator in self.validators.items():
            if element_name in values:
                try:
                    if not validator(values[element_name]):
                        errors.append(self.error_messages[element_name])
                except Exception as e:
                    errors.append(f"Validation error for {element_name}: {str(e)}")
        return errors

    def validate_deck_config(self, values: Dict[str, Any]) -> List[str]:
        """
        Validate form values against a DeckConfig.

        Args:
            values: Dictionary of element names to their values

        Returns:
            List of error messages, empty if all valid
        """
        try:
            DeckConfig(**values)
            return []
        except Exception as e:
            return [str(e)]

    def sanitize(self, values: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize form values by applying registered sanitizers.

        Args:
            values: Dictionary of element names to their values

        Returns:
            Sanitized values dictionary
        """
        sanitized = {}
        for name, value in values.items():
            element = self.get_element(name)
            if element and hasattr(element, "sanitize"):
                sanitized[name] = element.sanitize(value)
            else:
                sanitized[name] = value
        return sanitized

    def render(self):
        """
        Render all UISection components in this tab.
        """
        for section in self.sections.values():
            section.render()
