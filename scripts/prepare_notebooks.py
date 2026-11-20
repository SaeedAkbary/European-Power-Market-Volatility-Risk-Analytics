"""Compatibility entrypoint for the upgraded research notebook generator."""
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).with_name("build_research_notebooks.py")), run_name="__main__")
