"""에피소드 매니페스트(YAML) 읽기 + 검증."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import load_yaml
from .util import norm_path

CUT_TYPES = ("lip", "vo", "insert")
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


class ManifestError(ValueError):
    pass


@dataclass
class Cut:
    id: str
    index: int
    type: str
    media: Path | None = None
    audio: Path | None = None
    speaker: str | None = None
    subtitle: Any = None                 # 문자열 또는 페이지 리스트
    effects: list[tuple[str, Any]] = field(default_factory=list)   # (이름, 파라미터 원본)
    sfx: list[dict] = field(default_factory=list)                  # {name, at, gain_db}
    transition: dict | None = None
    bgm_cue: Any = None
    duration: float | None = None        # 강제 길이 (없으면 자동)
    focus: tuple[float, float] | None = None   # 얼굴 위치 (0~1, 0~1)
    emphasis: list[str] = field(default_factory=list)
    raw: dict = field(default_factory=dict)

    @property
    def is_still(self) -> bool:
        return self.media is None or self.media.suffix.lower() in IMAGE_EXT


@dataclass
class Manifest:
    path: Path
    dir: Path
    meta: dict
    cuts: list[Cut]
    bgm: dict
    shorts: dict
    raw: dict

    @property
    def fps(self) -> int:
        return int(self.meta.get("fps", 30))

    @property
    def size(self) -> tuple[int, int]:
        w, h = self.meta.get("size") or [self.meta.get("width", 1920), self.meta.get("height", 1080)]
        return int(w), int(h)

    @property
    def preset(self) -> str:
        return str(self.meta.get("preset", "buakom"))

    @property
    def title(self) -> str:
        return str(self.meta.get("title", self.path.stem))


def _parse_effects(items: Any, where: str) -> list[tuple[str, Any]]:
    """효과 목록 표기 3가지 허용:
        - punch_zoom                      (이름만)
        - {punch_zoom: {at: 0.5}}         (이름: 파라미터)
        - {dialect_note: "(*뭇나 = 먹었나)"} (이름: 대표값)
        - {name: punch_zoom, at: 0.5}
    """
    out: list[tuple[str, Any]] = []
    for it in items or []:
        if isinstance(it, str):
            out.append((it, {}))
        elif isinstance(it, dict):
            if "name" in it:
                p = {k: v for k, v in it.items() if k != "name"}
                out.append((str(it["name"]), p))
            elif len(it) == 1:
                (k, v), = it.items()
                out.append((str(k), v if v is not None else {}))
            else:
                raise ManifestError(f"{where}: 효과 표기를 이해할 수 없습니다: {it}")
        else:
            raise ManifestError(f"{where}: 효과 표기를 이해할 수 없습니다: {it}")
    return out


def _parse_sfx(items: Any, where: str) -> list[dict]:
    out = []
    for it in items or []:
        if isinstance(it, str):
            out.append({"name": it, "at": 0.0, "gain_db": 0.0})
        elif isinstance(it, dict) and "name" in it:
            out.append({"name": str(it["name"]), "at": float(it.get("at", 0.0)),
                        "gain_db": float(it.get("gain_db", 0.0))})
        else:
            raise ManifestError(f"{where}: sfx는 {{name, at}} 형태여야 합니다: {it}")
    return out


def _parse_transition(v: Any) -> dict | None:
    if v is None:
        return None
    if isinstance(v, str):
        return {"type": v}
    if isinstance(v, dict):
        if "type" not in v and len(v) == 1:
            (k, p), = v.items()
            return dict(p or {}, type=k)
        return dict(v)
    raise ManifestError(f"transition 표기 오류: {v}")


def load_manifest(path: str | Path) -> Manifest:
    path = Path(path).resolve()
    if not path.exists():
        raise ManifestError(f"매니페스트 파일이 없습니다: {path}")
    raw = load_yaml(path)
    base = path.parent
    meta = raw.get("meta") or {}
    cuts_raw = raw.get("cuts") or []
    if not cuts_raw:
        raise ManifestError("cuts가 비어 있습니다.")
    cuts: list[Cut] = []
    seen: set[str] = set()
    for i, c in enumerate(cuts_raw):
        if not isinstance(c, dict):
            raise ManifestError(f"{i + 1}번째 컷 형식 오류: {c}")
        cid = str(c.get("id", i + 1))
        where = f"컷 {cid}"
        if cid in seen:
            raise ManifestError(f"{where}: id가 중복됩니다.")
        seen.add(cid)
        ctype = str(c.get("type", "insert"))
        if ctype not in CUT_TYPES:
            raise ManifestError(f"{where}: type은 {CUT_TYPES} 중 하나여야 합니다 (받은 값: {ctype})")
        media = norm_path(c["media"], base) if c.get("media") else None
        audio = norm_path(c["audio"], base) if c.get("audio") else None
        focus = c.get("focus")
        emph = c.get("emphasis") or []
        cuts.append(Cut(
            id=cid, index=i, type=ctype, media=media, audio=audio,
            speaker=c.get("speaker"), subtitle=c.get("subtitle"),
            effects=_parse_effects(c.get("effects"), where),
            sfx=_parse_sfx(c.get("sfx"), where),
            transition=_parse_transition(c.get("transition")),
            bgm_cue=c.get("bgm_cue"),
            duration=float(c["duration"]) if c.get("duration") is not None else None,
            focus=(float(focus[0]), float(focus[1])) if focus else None,
            emphasis=[emph] if isinstance(emph, str) else list(emph),
            raw=c,
        ))
    bgm = {}
    for name, v in (raw.get("bgm") or {}).items():
        item = {"file": v} if isinstance(v, str) else dict(v)
        item["file"] = norm_path(item["file"], base) if item.get("file") else None
        bgm[str(name)] = item
    return Manifest(path=path, dir=base, meta=meta, cuts=cuts, bgm=bgm, shorts=raw.get("shorts") or {}, raw=raw)


def validate_files(m: Manifest) -> list[str]:
    """없는 파일 목록 (렌더 전에 한꺼번에 알려주기 위함)."""
    missing = []
    for c in m.cuts:
        for label, p in (("media", c.media), ("audio", c.audio)):
            if p is not None and not p.exists():
                missing.append(f"컷 {c.id} {label}: {p}")
        if c.type in ("lip", "vo") and c.media is None:
            missing.append(f"컷 {c.id}: {c.type} 컷에는 media가 필요합니다")
    for name, b in m.bgm.items():
        if b.get("file") is not None and not Path(b["file"]).exists():
            missing.append(f"bgm {name}: {b['file']}")
    return missing


def select_range(m: Manifest, spec: str) -> list[Cut]:
    """'8-27' / 'c08-c27' / '5' → 해당 구간 컷들 (매니페스트 순서, 양끝 포함).

    id가 정확히 일치하는 컷을 먼저 찾고, 없으면 id 속 숫자로 비교한다.
    """
    a, sep, b = spec.partition("-")
    b = b if sep else a

    def find(key: str) -> int:
        key = key.strip()
        for c in m.cuts:
            if c.id == key:
                return c.index
        digits = "".join(ch for ch in key if ch.isdigit())
        if digits:
            for c in m.cuts:
                cd = "".join(ch for ch in c.id if ch.isdigit())
                if cd and int(cd) == int(digits):
                    return c.index
        raise ManifestError(f"컷 id '{key}'를 찾을 수 없습니다. (있는 id: {', '.join(c.id for c in m.cuts)})")

    i, j = find(a), find(b)
    if j < i:
        i, j = j, i
    return m.cuts[i:j + 1]
