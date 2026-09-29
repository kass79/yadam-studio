"""분위기 효과: vo_cloud(속마음), fantasy(핑크 망상), wall_voice(벽 너머 목소리)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from ..graphics import shapes
from ..graphics.text import hex_rgba
from ..util import fnum
from .registry import effect


@effect("vo_cloud", defaults={
    "vignette": 0.75,             # 0~1.2, 클수록 가장자리 어둡게
    "desat": 0.9,                 # 채도 배율
    "font": "handwriting",
    "color": "#4FB3FF", "stroke": "#0B2540", "stroke_width": 4,
    "cloud_fill": "#FFFFFFF0", "cloud_border": "#4FB3FF",
    "position": "top", "x": 0.74, "size": 60, "margin": 40, "trail": "left",
})
def vo_cloud(plan, p):
    """속마음 컷: 가장자리 비네팅 + 구름 말풍선 자막(손글씨체, 하늘색)."""
    v = float(p["vignette"])
    if v > 0:
        plan.post.append(f"vignette=angle={fnum(v)}")
    if float(p.get("desat", 1.0)) != 1.0:
        plan.post.append(f"eq=saturation={fnum(p['desat'])}")
    if plan.subtitle is not None:
        plan.subtitle["kind"] = "cloud"
        plan.subtitle["style"].update({
            "font": p["font"], "color": p["color"], "emphasis_color": p["color"], "dialect_color": p["color"],
            "stroke": p["stroke"], "stroke_width": p["stroke_width"], "cloud_fill": p["cloud_fill"],
            "cloud_border": p["cloud_border"], "position": p["position"], "size": p["size"],
            "margin": p["margin"], "trail": p["trail"], "box": None, "shadow": 0,
            "max_chars": 14 if not plan.vertical else 12,
        })
        if not plan.vertical and p.get("x") is not None:
            plan.subtitle["style"]["x"] = p["x"]      # 16:9: 얼굴 옆(오른쪽 위)에 구름
        # 화자별 속마음 스타일 (예: speakers.소율.vo.color)
        spk = (plan.settings.get("speakers") or {}).get(plan.cut.speaker or "", {}) or {}
        vo = dict(spk.get("vo") or {})
        if "color" in vo:
            vo.setdefault("emphasis_color", vo["color"])
            vo.setdefault("dialect_color", vo["color"])
        plan.subtitle["style"].update(vo)


def _edge_glow(W: int, H: int, color: str, strength: float) -> Image.Image:
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dx = (xx - W / 2) / (W / 2)
    dy = (yy - H / 2) / (H / 2)
    r = np.sqrt(dx * dx * 0.8 + dy * dy)
    a = np.clip((r - 0.55) / 0.6, 0, 1) ** 1.4 * strength
    arr = np.zeros((H, W, 4), np.uint8)
    arr[..., :3] = hex_rgba(color)[:3]
    arr[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


@effect("fantasy", defaults={"at": 0.0, "dur": None, "pink": 0.6, "edge": "#FF8FC8", "edge_strength": 0.75,
                             "sparkles": 38, "sfx": "heartbeat", "sfx_repeat": 2})
def fantasy(plan, p):
    """망상/설렘: 핑크 필터 + 가장자리 분홍 빛 + 반짝이 파티클 + 심장박동 효과음."""
    at = float(p["at"])
    end = plan.duration if p.get("dur") is None else min(plan.duration, at + float(p["dur"]))
    en = plan.enable(at, end)
    k = float(p["pink"])
    # 빨강·파랑을 올리고 초록을 눌러 분홍 톤
    plan.post.append(
        f"colorchannelmixer=rr={fnum(1 + 0.08 * k)}:rg={fnum(0.10 * k)}:rb={fnum(0.10 * k)}:"
        f"gr={fnum(0.02 * k)}:gg={fnum(1 - 0.16 * k)}:gb={fnum(0.06 * k)}:"
        f"br={fnum(0.10 * k)}:bg={fnum(0.04 * k)}:bb={fnum(1 + 0.02 * k)}:enable='{en}'")
    plan.post.append(f"eq=brightness={fnum(0.04 * k)}:saturation={fnum(1 + 0.15 * k)}:enable='{en}'")
    W, H = plan.canvas
    cache = plan.assets.parent / "_shared"
    edge_path = cache / f"edge_{W}x{H}_{p['edge'].lstrip('#')}_{fnum(p['edge_strength'])}.png"
    if not edge_path.exists():
        cache.mkdir(parents=True, exist_ok=True)
        _edge_glow(W, H, p["edge"], float(p["edge_strength"])).save(edge_path)
    fade = [f"fade=t=in:st={fnum(at)}:d=0.25:alpha=1"]
    plan.add_layer(edge_path, "0", "0", at, end, filters=fade, z=40, name="pink_edge")
    if int(p["sparkles"]) > 0:
        seq_dir = cache / f"sparkle_{W}x{H}_{int(p['sparkles'])}"
        pattern = shapes.sparkle_sequence(seq_dir, W, H, count=int(p["sparkles"]), unit=plan.unit)
        plan.add_layer(Path(pattern), "0", "0", at, end, sequence=True, filters=fade, z=45, name="sparkles")
    if p.get("sfx"):
        for i in range(max(1, int(p.get("sfx_repeat", 1)))):
            t = at + 0.05 + i * 0.85
            if t < end:
                plan.add_sfx(p["sfx"], t)


@effect("wall_voice", defaults={"lowpass": 850, "highpass": 160, "echo": True, "gain_db": -3.0,
                                "subtitle_color": "#CFCFCF"})
def wall_voice(plan, p):
    """벽 너머 대사: 로우패스/하이패스로 먹먹하게 + 짧은 울림. 자막은 살짝 회색."""
    f = [f"highpass=f={int(p['highpass'])}", f"lowpass=f={int(p['lowpass'])}", f"lowpass=f={int(p['lowpass'])}"]
    if p.get("echo"):
        f.append("aecho=0.8:0.55:32:0.25")
    f.append(f"volume={fnum(p['gain_db'])}dB")
    plan.audio_filters.extend(f)
    if plan.subtitle is not None and p.get("subtitle_color"):
        plan.subtitle["style"]["color"] = p["subtitle_color"]
