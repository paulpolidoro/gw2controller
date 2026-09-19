from __future__ import annotations

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
SRC_DIR = PACKAGE_DIR.parent
ROOT = SRC_DIR.parent
PROFILES_DIR = ROOT / "profiles"
ASSETS_DIR = ROOT / "assets"
GLYPHS_DIR = ASSETS_DIR / "glyphs"
