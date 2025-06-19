import os

def print_tree(root_dir, prefix=""):
    entries = [e for e in os.listdir(root_dir) if not e.startswith(".") and e != "__pycache__"]
    entries = [e for e in entries if not is_ignored(os.path.join(root_dir, e))]
    entries.sort()
    for idx, entry in enumerate(entries):
        path = os.path.join(root_dir, entry)
        connector = "└── " if idx == len(entries) - 1 else "├── "
        print(prefix + connector + entry)
        if os.path.isdir(path):
            extension = "    " if idx == len(entries) - 1 else "│   "
            print_tree(path, prefix + extension)

def is_ignored(path):
    # Add more ignore rules as needed, or parse .gitignore
    basename = os.path.basename(path)
    return basename in {".git", ".venv", "venv", "env", ".mypy_cache", ".pytest_cache", ".idea", ".vscode", "node_modules"}

if __name__ == "__main__":
    print("Project file tree:")
    print_tree(os.path.dirname(os.path.abspath(__file__)))
