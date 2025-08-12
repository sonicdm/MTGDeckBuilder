from setuptools import setup, find_packages

setup(
    name="mtg_deckbuilder_ui",
    version="0.1.0",
    description="Gradio-based UI for Magic: The Gathering Deckbuilder",
    author="Your Name",
    packages=find_packages(
        include=["mtg_deckbuilder_ui", "mtg_deck_builder", "mtg_deck_builder.*"]
    ),
    install_requires=[
        "gradio",
        "sqlalchemy",
        "pyyaml",
        "tqdm",
    ],
    python_requires=">=3.12",
    include_package_data=True,
    entry_points={
        "console_scripts": ["mtg-deckbuilder-ui = mtg_deckbuilder_ui.app:main"]
    },
)
