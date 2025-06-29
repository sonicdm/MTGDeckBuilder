from pathlib import Path

def get_sample_data_dir() -> Path:
    """
    Starting from the current file's directory, walk upwards until we find a folder named 'tests'.
    Then return the path to 'tests/sample_data'.
    If not found, raise an error.
    """
    current_dir = Path(__file__).parent.absolute()

    while True:
        if current_dir.name == "tests":
            # Found the 'tests' directory
            return current_dir / "sample_data"

        parent_dir = current_dir.parent
        if parent_dir == current_dir:
            # We've reached the filesystem root without finding 'tests'
            raise RuntimeError("Could not locate a 'tests' directory in the path hierarchy.")

        current_dir = parent_dir

def get_sample_data_path(filename: str) -> Path:
    return get_sample_data_dir() / filename

# DummyCard, DummyRepo, and DummyInventoryRepo classes were here
# They have been moved to tests/fixtures.py

