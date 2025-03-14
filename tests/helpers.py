import os

def get_sample_data_dir() -> str:
    """
    Starting from the current file's directory, walk upwards until we find a folder named 'tests'.
    Then return the path to 'tests/sample_data'.
    If not found, raise an error.
    """
    current_dir = os.path.abspath(os.path.dirname(__file__))

    while True:
        if os.path.basename(current_dir) == "tests":
            # Found the 'tests' directory
            return os.path.join(current_dir, "sample_data")

        parent_dir = os.path.dirname(current_dir)
        if parent_dir == current_dir:
            # We've reached the filesystem root without finding 'tests'
            raise RuntimeError("Could not locate a 'tests' directory in the path hierarchy.")

        current_dir = parent_dir

def get_sample_data_path(filename: str) -> str:
    return os.path.join(get_sample_data_dir(), filename)