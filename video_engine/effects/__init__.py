"""효과 플러그인 모음. 이 폴더의 모든 모듈을 불러와 등록부(EFFECTS)를 채운다."""
from __future__ import annotations

import importlib
import pkgutil

from .registry import EFFECTS, TRANSITIONS, effect, get, is_enabled, transition  # noqa: F401

_loaded = False


def load_all() -> None:
    global _loaded
    if _loaded:
        return
    for mod in pkgutil.iter_modules(__path__):
        if mod.name != "registry":
            importlib.import_module(f"{__name__}.{mod.name}")
    importlib.import_module("video_engine.transitions")
    _loaded = True


load_all()
