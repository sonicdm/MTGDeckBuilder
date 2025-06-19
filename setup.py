from setuptools import setup, find_packages

setup(
    name="mtg_deckbuilder_ui",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pydantic",
        "pandas",
        "gradio",
        "matplotlib",
        "pyperclip",
        "sqlalchemy",
        "fastapi",
        "uvicorn"
    ],
    entry_points={
        "console_scripts": [
            "mtg-deck=mtg_deck_builder.cli:main",
            "mtg-deck-ui=mtg_deckbuilder_ui.app:main"
        ]
    },
)
