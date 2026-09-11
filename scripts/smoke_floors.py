"""Compatibility entry for independent floor processing and export regression."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).with_name('smoke_workspace.py')),run_name='__main__')
