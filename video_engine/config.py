"""설정 병합: 엔진 기본값 < 채널 프리셋 < config.yaml < 매니페스트.

- 프리셋(presets/*.yaml): 채널 성격 (효과 on/off, 자막 스타일, 화자 스타일, 템포)
- config.yaml: PC 사정 (ffmpeg 위치, 폰트 경로, 효과음 파일 매핑, 인코더)
- 매니페스트: 에피소드별 덮어쓰기 (meta.overrides, speakers, sfx)
"""
from __future__ import annotations

import os
from pathlib import Path

import yaml

from .util import deep_merge, norm_path

PKG_DIR = Path(__file__).resolve().parent
PRESET_DIR = PKG_DIR / "presets"

_WIN_FONTS = os.path.expandvars(r"%WINDIR%\Fonts") if os.name == "nt" else "C:/Windows/Fonts"
_WIN_USER_FONTS = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Fonts") if os.name == "nt" else ""


def _font_candidates(*names: str) -> list[str]:
    """윈도우(시스템/사용자 폰트 폴더), 리눅스, 맥 순서로 찾아볼 후보 경로."""
    out: list[str] = []
    for n in names:
        if "/" in n:  # 이미 경로
            out.append(n)
            continue
        out += [f"{_WIN_FONTS}/{n}"]
        if _WIN_USER_FONTS:
            out.append(f"{_WIN_USER_FONTS}/{n}")
        out += [f"~/.fonts/{n}", f"/usr/share/fonts/truetype/{n}", f"/Library/Fonts/{n}"]
    return out


DEFAULTS: dict = {
    "engine": {
        "ffmpeg": "ffmpeg",
        "ffprobe": None,
        "jobs": 0,           # 0 = CPU 코어 수에 맞춰 자동
        "work_dir": None,    # 기본: 매니페스트 폴더/_work/<파일명>
        "cache": True,       # 바뀐 컷만 다시 렌더
    },
    "video": {
        "encoder": "libx264",       # RTX 그래픽카드면 h264_nvenc
        "crf": 18,
        "preset": "medium",
        "nvenc_preset": "p5",
        "nvenc_cq": 19,
        "intermediate_crf": 12,     # 컷 단위 중간 파일 화질 (최종 전에 한 번 더 인코딩됨)
        "intermediate_preset": "veryfast",
    },
    "audio": {
        "sample_rate": 48000,
        "target_lufs": -14.0,       # 대사 기준 라우드니스
        "normalize": "dialogue",    # dialogue: 대사 버스 기준 / program: 전체 믹스 기준
        "true_peak": -1.5,          # 리미터 천장 (dBTP). AAC 인코딩 여유분 포함
        "bgm_lufs": -28.0,          # BGM 기본 레벨 (덕킹 전, 대사보다 14LU 아래)
        "sfx_peak_db": -8.0,        # 효과음 피크 기준
        "aac_bitrate": "192k",
        "duck": {"threshold": 0.02, "ratio": 8, "attack": 15, "release": 400, "makeup": 1},
        "sfx_duck": {"threshold": 0.05, "ratio": 3, "attack": 5, "release": 150, "makeup": 1},
    },
    "fonts": {
        # 문자열(경로) 하나 또는 후보 리스트. 앞에서부터 존재하는 첫 파일을 쓴다. ttc는 "파일.ttc#번호"
        "main": _font_candidates("Pretendard-Bold.otf", "Pretendard-SemiBold.otf", "NotoSansKR-Bold.ttf",
                                 "NotoSansKR-Bold.otf", "malgunbd.ttf",
                                 "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc#1",
                                 "/System/Library/Fonts/AppleSDGothicNeo.ttc"),
        "regular": _font_candidates("Pretendard-Regular.otf", "Pretendard-Medium.otf", "NotoSansKR-Regular.ttf",
                                    "NotoSansKR-Regular.otf", "malgun.ttf",
                                    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc#1",
                                    "/System/Library/Fonts/AppleSDGothicNeo.ttc"),
        "heavy": _font_candidates("Pretendard-Black.otf", "Pretendard-ExtraBold.otf", "NotoSansKR-Black.ttf",
                                  "NotoSansKR-Black.otf", "malgunbd.ttf",
                                  "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc#1",
                                  "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc#1"),
        "handwriting": _font_candidates("NanumPen.ttf", "NanumPenScript-Regular.ttf", "Gaegu-Bold.ttf",
                                        "GamjaFlower-Regular.ttf", "NanumBrush.ttf"),
    },
    # 효과음 이름 → 파일. 비워두거나 파일이 없으면 코드로 합성한 임시 효과음을 쓴다.
    "sfx": {},
    "timing": {
        "insert_duration": 2.2,   # 대사 없는 컷 기본 길이
        "min_cut": 1.2,
        "lead": 0.12,             # 컷 시작 → 대사 시작
        "tail": 0.25,             # 대사 끝 → 다음 컷
        "max_still_hold": 3.0,    # 정지 이미지가 움직임 없이 버틸 수 있는 최대 시간
        "target_avg_cut": [2.0, 3.0],
    },
    "subtitle": {
        "enabled": True,
        "font": "main",
        "size": 64,               # 1080p 기준 px (세로 영상은 canvas에 맞춰 환산)
        "color": "#FFFFFF",
        "stroke": "#000000",
        "stroke_width": 6,
        "emphasis_color": "#FFE14D",   # *강조*
        "dialect_color": "#FF9A3C",    # [사투리]
        "position": "bottom",          # bottom | lower_third | top
        "margin": 70,
        "max_chars": 22,               # 한 줄 최대 글자 (넘으면 줄바꿈)
        "line_spacing": 1.18,
        "shadow": 0,
        "fade": 0.0,                   # 자막 페이드 인/아웃 (초)
        "box": None,                   # 반투명 배경 띠 색 (예: "#00000080")
        "note_size": 0.62,             # dialect_note 크기 (자막 대비)
        "note_color": "#FFE9B0",
    },
    "speakers": {},
    "effects": {},
    "auto_effects": {"lip": [], "vo": [], "insert": []},
    "transition_default": {"type": "cut"},
    "shorts": {
        "size": [1080, 1920],
        "loop": 0.4,               # 끝→처음 크로스페이드 길이 (0이면 루프 처리 안 함)
        "hook_hold": 1.0,          # 상단 훅 자막 표시 시간
        "hook": {"size": 78, "color": "#FFFFFF", "stroke": "#000000", "stroke_width": 8,
                 "box": "#E8303A", "y": 0.12, "font": "heavy"},
        "subtitle": {"size": 70, "position": "lower_third", "max_chars": 13},
        "max_duration": 60,
    },
}


def load_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def find_preset(name_or_path: str, base_dir: Path | None = None) -> Path:
    p = norm_path(name_or_path, base_dir)
    if p.suffix in (".yaml", ".yml") and p.exists():
        return p
    cand = PRESET_DIR / f"{name_or_path}.yaml"
    if cand.exists():
        return cand
    names = ", ".join(sorted(x.stem for x in PRESET_DIR.glob("*.yaml")))
    raise FileNotFoundError(f"프리셋 '{name_or_path}'을 찾을 수 없습니다. 사용 가능: {names}")


def find_config(manifest_dir: Path, explicit: str | None) -> Path | None:
    if explicit:
        p = norm_path(explicit, Path.cwd())
        if not p.exists():
            raise FileNotFoundError(f"config 파일이 없습니다: {p}")
        return p
    for d in (manifest_dir, manifest_dir.parent, Path.cwd(), PKG_DIR):
        for name in ("config.yaml", "video_engine.yaml"):
            if (d / name).exists():
                return d / name
    return None


def build_settings(preset: str, manifest: dict, manifest_dir: Path, config_path: str | None = None) -> dict:
    s = deep_merge(DEFAULTS, {})
    s = deep_merge(s, load_yaml(find_preset(preset, manifest_dir)))
    cfg = find_config(manifest_dir, config_path)
    if cfg:
        c = load_yaml(cfg)
        if c.get("sfx"):
            c["sfx"] = _abs_sfx(c["sfx"], cfg.parent)
        if c.get("fonts"):
            c["fonts"] = {k: _abs_fonts(v, cfg.parent) for k, v in c["fonts"].items()}
        s = deep_merge(s, c)
        s["_config_path"] = str(cfg)
        s["_config_dir"] = str(cfg.parent)
    meta = manifest.get("meta", {}) or {}
    s = deep_merge(s, meta.get("overrides") or {})
    if manifest.get("speakers"):
        s["speakers"] = deep_merge(s.get("speakers", {}), manifest["speakers"])
    if manifest.get("sfx"):
        s["sfx"] = deep_merge(s.get("sfx", {}), _abs_sfx(manifest["sfx"], manifest_dir))
    if manifest.get("fonts"):
        s["fonts"] = deep_merge(s["fonts"], {k: _abs_fonts(v, manifest_dir) for k, v in manifest["fonts"].items()})
    return s


def _abs_sfx(table: dict, base: Path) -> dict:
    """효과음 표를 {이름: {file: 절대경로, gain_db: 0}} 형태로 정리."""
    out = {}
    for name, v in (table or {}).items():
        item = {"file": v} if isinstance(v, str) else dict(v or {})
        if item.get("file"):
            item["file"] = str(norm_path(item["file"], base))
        out[name] = item
    return out


def _abs_fonts(v, base: Path):
    def one(x: str) -> str:
        path, idx = _split_index(str(x))
        p = str(norm_path(path, base))
        return f"{p}#{idx}" if "#" in str(x) else p
    return one(v) if isinstance(v, str) else [one(x) for x in v]


# ─────────────────────────── 폰트 ───────────────────────────

_font_cache: dict[str, tuple[str, int]] = {}


def _split_index(p: str) -> tuple[str, int]:
    if "#" in p:
        path, _, idx = p.rpartition("#")
        try:
            return path, int(idx)
        except ValueError:
            return p, 0
    return p, 0


def resolve_font(settings: dict, role: str) -> tuple[str, int]:
    """폰트 역할(main/regular/heavy/handwriting) → (파일경로, ttc 인덱스). 못 찾으면 다른 역할로 대체."""
    fonts = settings.get("fonts", {})
    order = [role] + [r for r in ("main", "regular", "heavy") if r != role]
    base = Path(settings.get("_config_dir") or ".")
    for r in order:
        spec = fonts.get(r)
        if not spec:
            continue
        cands = [spec] if isinstance(spec, str) else list(spec)
        for c in cands:
            key = f"{r}:{c}"
            if key in _font_cache:
                return _font_cache[key]
            path, idx = _split_index(str(c))
            p = norm_path(path, base)
            if p.exists():
                _font_cache[key] = (str(p), idx)
                return _font_cache[key]
    # 최후 수단: 시스템 어딘가의 한글 폰트
    for guess in ("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", f"{_WIN_FONTS}/malgunbd.ttf",
                  f"{_WIN_FONTS}/malgun.ttf"):
        if Path(guess).exists():
            return guess, 0
    raise FileNotFoundError(
        "한글 폰트를 찾지 못했습니다. config.yaml의 fonts.main에 폰트 파일 경로를 적어주세요 "
        "(예: C:/Windows/Fonts/malgunbd.ttf)")
