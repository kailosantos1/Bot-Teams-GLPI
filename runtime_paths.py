"""Deployment files live beside the executable, never in PyInstaller's extraction."""
from pathlib import Path
import sys


def deployment_root():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


ROOT = deployment_root()
