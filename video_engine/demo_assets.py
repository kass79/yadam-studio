"""가짜 테스트 소스 생성: 단색 배경 인물 그림, 입 벌림/다묾 립싱크 mp4, 사인파 '말소리' wav, BGM wav.

python -m video_engine demo-assets  →  video_engine/examples/assets/ 에 만든다.
진짜 그림/영상/음성이 준비되면 매니페스트의 경로만 바꾸면 된다.
"""
from __future__ import annotations

import zlib
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from .config import DEFAULTS, resolve_font
from .graphics.text import load_font
from .render import ffmpeg
from .render.audio import SR, write_wav
from .util import ff_path

EXAMPLES = Path(__file__).resolve().parent / "examples"

CHARS = {
    "dongcheol": {"bg": "#E39B4B", "face": "#F6D2A8", "shirt": "#2F5D8C", "label": "동철", "hair": "#2A2A2A"},
    "soyul": {"bg": "#7FB8E6", "face": "#FBE0CC", "shirt": "#F07CA5", "label": "소율", "hair": "#5B3A29"},
    "mom": {"bg": "#8CC084", "face": "#F2D0B0", "shirt": "#8E5BA8", "label": "엄마", "hair": "#6E6E6E"},
}


def _person(key: str, mouth: str, *, note: str, W=1920, H=1080, bg: str | None = None) -> Image.Image:
    c = CHARS[key]
    img = Image.new("RGB", (W, H), bg or c["bg"])
    dr = ImageDraw.Draw(img)
    cx, cy = W // 2, int(H * 0.42)   # 얼굴은 화면 중앙 (쇼츠 중앙 크롭 대비)
    r = int(H * 0.2)
    dr.rounded_rectangle([cx - int(r * 1.5), cy + int(r * 1.05), cx + int(r * 1.5), H + 40], radius=r // 2,
                         fill=c["shirt"])
    dr.ellipse([cx - r, cy - r, cx + r, cy + r], fill=c["face"])
    dr.pieslice([cx - r, cy - r - 10, cx + r, cy + r - 40], 180, 360, fill=c["hair"])
    for ex in (-1, 1):
        dr.ellipse([cx + ex * r * 0.4 - 16, cy - 10, cx + ex * r * 0.4 + 16, cy + 22], fill="#222222")
    if mouth == "open":
        dr.ellipse([cx - 44, cy + r * 0.42, cx + 44, cy + r * 0.42 + 60], fill="#7A1F2B")
    elif mouth == "smile":
        dr.arc([cx - 60, cy + r * 0.2, cx + 60, cy + r * 0.6], 20, 160, fill="#7A1F2B", width=10)
    else:
        dr.line([cx - 40, cy + r * 0.5, cx + 40, cy + r * 0.5], fill="#7A1F2B", width=10)
    fp, fi = resolve_font(DEFAULTS, "main")
    f = load_font(fp, 54, fi)
    dr.text((60, 50), f"{c['label']} — {note}", font=f, fill="#FFFFFF", stroke_width=4, stroke_fill="#000000")
    # 줌/흔들림이 눈에 보이도록 격자
    for x in range(0, W, 160):
        dr.line([x, 0, x, 18], fill="#FFFFFF", width=3)
        dr.line([x, H - 18, x, H], fill="#FFFFFF", width=3)
    return img


def _speech(dur: float, f0: float, seed: int) -> np.ndarray:
    """사인파로 만든 가짜 말소리 (음절처럼 크기가 오르내림)."""
    rng = np.random.default_rng(seed)
    t = np.arange(int(dur * SR)) / SR
    pitch = f0 * (1 + 0.06 * np.sin(2 * np.pi * 1.3 * t) + 0.02 * rng.standard_normal(len(t)).cumsum() / SR)
    ph = 2 * np.pi * np.cumsum(pitch) / SR
    x = sum((0.6 / k) * np.sin(k * ph) for k in range(1, 6))
    syl = np.clip(np.sin(2 * np.pi * 5.5 * t + rng.uniform(0, 6)), 0, None) ** 0.6
    syl *= 0.6 + 0.4 * rng.random(len(t)).reshape(-1, 1).mean(axis=1)
    env = np.minimum(1, t * 20) * np.minimum(1, (dur - t) * 20)
    y = (x * syl * env).astype(np.float32)
    y = y / (np.max(np.abs(y)) or 1) * 0.35   # 일부러 작게 (loudnorm이 -14 LUFS로 올리는지 확인용)
    return np.stack([y, y], axis=1)


def _bgm(kind: str, seconds: float = 16.0) -> np.ndarray:
    t = np.arange(int(seconds * SR)) / SR
    out = np.zeros_like(t)
    if kind == "main":      # 통통 튀는 코미디 루프 (120bpm)
        beat = 0.5
        bass = [110.0, 110.0, 146.8, 164.8, 110.0, 130.8, 146.8, 98.0]
        for i in range(int(seconds / beat)):
            s = i * beat
            f = bass[i % len(bass)]
            tt = t - s
            m = (tt >= 0) & (tt < beat)
            out[m] += 0.5 * np.sin(2 * np.pi * f * tt[m]) * np.exp(-tt[m] * 6)
            if i % 2 == 1:
                for ff in (f * 2, f * 2.52, f * 3):
                    out[m] += 0.12 * np.sin(2 * np.pi * ff * tt[m]) * np.exp(-tt[m] * 10)
    else:                   # 몽글몽글 패드
        for f in (261.6, 329.6, 392.0, 493.9):
            out += 0.15 * np.sin(2 * np.pi * f * t + np.sin(2 * np.pi * 0.25 * t))
        out *= 0.7 + 0.3 * np.sin(2 * np.pi * 0.5 * t)
    out = out / np.max(np.abs(out)) * 0.5
    return np.stack([out, out * 0.95], axis=1).astype(np.float32)


# (파일명, 인물, 입, 설명, 대사 글자수 → 길이, 목소리 높이)
LINES = {
    "line_02": ("dongcheol", 13, 115), "vo_03": ("soyul", 16, 230), "line_04": ("dongcheol", 6, 115),
    "vo_05": ("soyul", 12, 230), "vo_06": ("soyul", 18, 230), "line_08": ("mom", 18, 195),
    "line_09": ("dongcheol", 9, 115), "vo_10": ("soyul", 13, 230),
}


def make_demo_assets(folder: str | None = None) -> Path:
    out = Path(folder).resolve() if folder else EXAMPLES / "assets"
    out.mkdir(parents=True, exist_ok=True)
    # 정지 그림
    hall = Image.new("RGB", (1920, 1080), "#3B4252")
    d = ImageDraw.Draw(hall)
    for i in range(7):
        x = 160 + i * 260
        d.rectangle([x, 300, x + 150, 900], fill="#4C566A", outline="#D8DEE9", width=6)
    fp, fi = resolve_font(DEFAULTS, "main")
    d.text((60, 50), "아파트 복도 (인서트)", font=load_font(fp, 54, fi), fill="#FFFFFF")
    hall.save(out / "hallway.png")
    _person("soyul", "closed", note="속마음(입 다묾)").save(out / "soyul_closed.png")
    _person("soyul", "closed", note="망상 중", bg="#F2A7C6").save(out / "soyul_dream.png")
    _person("soyul", "smile", note="안도").save(out / "soyul_happy.png")
    _person("soyul", "closed", note="벽에 귀 대는 중", bg="#9AA5B1").save(out / "soyul_wall.png")
    _person("dongcheol", "closed", note="정지 컷").save(out / "dongcheol_still.png")
    # 립싱크 mp4 (입 닫힘/열림 그림을 0.12초마다 번갈아)
    for key, note in (("dongcheol", "립싱크"), ("mom", "립싱크")):
        a, b = out / f"_{key}_closed.png", out / f"_{key}_open.png"
        _person(key, "closed", note=note).save(a)
        _person(key, "open", note=note).save(b)
    # 음성 wav
    for name, (who, chars, f0) in LINES.items():
        write_wav(out / f"{name}.wav", _speech(0.35 + chars * 0.11, f0, zlib.crc32(name.encode())))
    write_wav(out / "bgm_main.wav", _bgm("main"))
    write_wav(out / "bgm_dream.wav", _bgm("dream", 12.0))

    def lip(key: str, seconds: float, dst: Path, audio: Path | None):
        a, b = out / f"_{key}_closed.png", out / f"_{key}_open.png"
        args = ["-loop", "1", "-framerate", "25", "-t", f"{seconds}", "-i", ff_path(a),
                "-loop", "1", "-framerate", "25", "-t", f"{seconds}", "-i", ff_path(b)]
        if audio:
            args += ["-i", ff_path(audio)]
        args += ["-filter_complex",
                 "[1:v]format=rgba[m];[0:v][m]overlay=enable='lt(mod(t,0.24),0.12)',scale=1280:720,format=yuv420p[v]",
                 "-map", "[v]"]
        if audio:
            args += ["-map", "2:a", "-c:a", "aac", "-b:a", "160k", "-shortest"]
        # 일부러 1280x720 25fps로: 엔진이 해상도/프레임레이트를 맞추는지 확인
        ffmpeg.run(args + ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-t", f"{seconds}", ff_path(dst)],
                   desc=f"데모 립싱크 {dst.name}")

    # 컷 2: 음성이 mp4 안에 들어있는 경우 / 나머지: 영상만 (음성은 wav로 따로)
    lip("dongcheol", 0.35 + 13 * 0.11, out / "dongcheol_talk_02.mp4", out / "line_02.wav")
    lip("dongcheol", 3.0, out / "dongcheol_talk.mp4", None)
    lip("mom", 3.0, out / "mom_talk.mp4", None)
    for f in out.glob("_*.png"):
        f.unlink()
    return out


if __name__ == "__main__":
    print(make_demo_assets())
