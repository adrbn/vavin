"""Stroke measurement, shared by the contrast filter and the QA scripts.

Thin re-export layer: the measuring code lives in scripts/08_strokes.py, which
is a command-line tool, and importing a module whose name starts with a digit
needs importlib. This keeps that ugliness in one place.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "_vavin_strokes", Path(__file__).resolve().parents[1] / "08_strokes.py"
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

hairline = _mod.hairline
stem_width = _mod.stem_width
cap_stem = _mod.cap_stem
outline = _mod.outline
