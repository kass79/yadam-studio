"""작은 공용 도구들: 딕셔너리 병합, 경로 처리, 로그."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

VERBOSE = os.environ.get("VIDEO_ENGINE_VERBOSE", "") not in ("", "0")


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def debug(msg: str) -> None:
    if VERBOSE:
        log("  · " + msg)


def deep_merge(base: dict, over: dict | None) -> dict:
    """base 위에 over를 덮어쓴 새 dict (중첩 dict는 재귀 병합, 리스트는 통째로 교체)."""
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def norm_path(p: str | os.PathLike, base_dir: Path | None = None) -> Path:
    """매니페스트/설정에 적힌 경로를 실제 Path로.

    - 윈도우 역슬래시(C:\\a\\b)와 슬래시 모두 허용
    - 상대경로는 base_dir(매니페스트가 있는 폴더) 기준
    - ~ 와 %USERPROFILE% 같은 환경변수 확장
    """
    s = os.path.expandvars(os.path.expanduser(str(p)))
    # 리눅스에서 윈도우식 경로를 받았을 때도 최대한 살린다 (테스트용)
    if os.sep == "/" and "\\" in s and not s.startswith("\\\\"):
        s = s.replace("\\", "/")
    path = Path(s)
    if not path.is_absolute() and base_dir is not None:
        path = Path(base_dir) / path
    return path


def ff_path(p: Path | str) -> str:
    """ffmpeg에 넘길 경로 문자열. 윈도우에서도 슬래시로 통일한다."""
    return str(p).replace("\\", "/")


def stable_hash(*parts: Any) -> str:
    h = hashlib.sha1()
    for part in parts:
        h.update(json.dumps(part, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8"))
    return h.hexdigest()[:12]


def file_sig(p: Path | None) -> str:
    """캐시 키용 파일 서명(경로+크기+수정시각)."""
    if p is None:
        return ""
    try:
        st = Path(p).stat()
        return f"{p}|{st.st_size}|{int(st.st_mtime)}"
    except OSError:
        return f"{p}|missing"


def fnum(x: float) -> str:
    """ffmpeg 표현식에 넣을 숫자 (지수표기 방지)."""
    s = f"{float(x):.6f}".rstrip("0").rstrip(".")
    return s if s not in ("", "-0") else "0"


def safe_name(s: Any) -> str:
    keep = [c if (c.isalnum() or c in "-_") else "_" for c in str(s)]
    return "".join(keep)[:40] or "x"
