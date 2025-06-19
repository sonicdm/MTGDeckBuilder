import configparser
import shutil
from pathlib import Path
from typing import Any, Optional, List, Union

# Define the project root as the directory containing the 'mtg_deckbuilder_ui' directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class AppConfig:
    """
    Centralized application configuration interface.
    Handles persistent settings storage and retrieval from an INI file.
    """

    _instance: Optional["AppConfig"] = None

    def __new__(cls) -> "AppConfig":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        """Initialize the configuration system."""
        self.config_dir = PROJECT_ROOT / "mtg_deckbuilder_ui" / "config"
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.config_file: Path = self.config_dir / "application_settings.ini"
        self.default_config_file: Path = (
            self.config_dir / "default.application_settings.ini"
        )

        self.config: configparser.ConfigParser = configparser.ConfigParser()

        if not self.config_file.exists():
            self._create_from_default()
        else:
            self.config.read(self.config_file)

    def _create_from_default(self) -> None:
        """Create a new config file by copying the default."""
        if not self.default_config_file.is_file():
            raise FileNotFoundError(
                f"The default configuration file was not found at {self.default_config_file}"
            )
        shutil.copy(self.default_config_file, self.config_file)
        self.config.read(self.config_file)

    def get(
        self, section: str, key: str, fallback: Optional[str] = None
    ) -> Optional[str]:
        """
        Get a string value from the configuration.

        Args:
            section: Section name in config.
            key: Setting name.
            fallback: Default value if setting doesn't exist.

        Returns:
            The setting value or fallback.
        """
        return self.config.get(section, key, fallback=fallback)

    def get_bool(self, section: str, key: str, fallback: bool = False) -> bool:
        """
        Get a boolean value from the configuration.

        Args:
            section: Section name in config.
            key: Setting name.
            fallback: Default value if setting doesn't exist.

        Returns:
            The boolean setting value or fallback.
        """
        return self.config.getboolean(section, key, fallback=fallback)

    def get_int(self, section: str, key: str, fallback: int = 0) -> int:
        """
        Get an integer value from the configuration.

        Args:
            section: Section name in config.
            key: Setting name.
            fallback: Default value if setting doesn't exist.

        Returns:
            The integer setting value or fallback.
        """
        return self.config.getint(section, key, fallback=fallback)

    def get_list(
        self, section: str, key: str, fallback: Optional[List[str]] = None
    ) -> List[str]:
        """
        Get a list of strings from a comma-separated value in the configuration.

        Args:
            section: Section name in config.
            key: Setting name.
            fallback: Default value if setting doesn't exist.

        Returns:
            A list of strings.
        """
        value = self.get(section, key)
        if value is None:
            return fallback or []
        return [item.strip() for item in value.split(",") if item.strip()]

    def get_path(self, key: str) -> Path:
        """
        Get a path from the [Paths] section of the config.
        Paths are stored relative to the project root and are returned as absolute paths.

        Args:
            key: The path key to retrieve from the [Paths] section.

        Returns:
            An absolute Path object.
        """
        relative_path_str = self.config.get("Paths", key)
        if not relative_path_str:
            raise KeyError(
                f"Path key '{key}' not found or is empty in the [Paths] section."
            )
        return (PROJECT_ROOT / relative_path_str).resolve()

    def get_db_url(self) -> str:
        """Get the fully-formed SQLite database URL."""
        return f"sqlite:///{self.get_path('database')}"

    def set(self, section: str, key: str, value: Any) -> None:
        """
        Set a setting value in the configuration.

        Args:
            section: Section name in config.
            key: Setting name.
            value: Value to set. It will be converted to a string.
        """
        if not self.config.has_section(section):
            self.config.add_section(section)

        str_value = str(value)
        # If the value is a path, try to make it relative to the project root
        if isinstance(value, Path):
            try:
                str_value = str(value.relative_to(PROJECT_ROOT))
            except ValueError:
                str_value = str(value)  # Not within project root, use absolute path

        self.config.set(section, key, str_value)
        self.save()

    def save(self) -> None:
        """Save the current configuration to the file."""
        with open(self.config_file, "w") as f:
            self.config.write(f)

    def get_default_config(self):
        """Get the default configuration."""
        config = configparser.ConfigParser()

        # UI section
        config["UI"] = {
            "auto_load_collection": "False",
            "last_loaded_config": "",  # Store the last loaded config filename
        }

        # Paths section
        config["Paths"] = {
            "data_dir": "data",
            "config_dir": "configs",
            "inventory_dir": "inventories",
            "deck_dir": "decks",
        }

        return config
    
    def get_paths(self) -> List[str]:
        """Get all paths from the [Paths] section of the config."""
        directories = []
        for key in self.config["Paths"]:
            if key != "database":
                directories.append(self.get_path(key))
        return directories
    def get_last_loaded_inventory(self) -> str:
        """Get the last loaded inventory file from the [InventoryManager] section of the config."""
        return self.config.get("InventoryManager", "last_loaded_inventory")
    
    def get_last_loaded_config(self) -> str:
        """Get the last loaded config file from the [DeckBuilder] section of the config."""
        return self.config.get("DeckBuilder", "last_loaded_config")
    
    def get_last_loaded_deck(self) -> str:
        """Get the last loaded deck file from the [DeckBuilder] section of the config."""
        return self.config.get("DeckBuilder", "last_loaded_deck")
    
    def get_last_loaded_library(self) -> str:
        """Get the last loaded library file from the [LibraryViewer] section of the config."""
# Create a singleton instance for application-wide access
app_config: AppConfig = AppConfig()
