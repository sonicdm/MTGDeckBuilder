from setuptools import setup, find_packages

setup(
    name="mtg_deck_builder",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "pydantic",
        "pandas",
        "gradio"
    ],
    entry_points={
        "console_scripts": [
            "mtg-deck=mtg_deck_builder.cli:main"
        ]
    },
)
