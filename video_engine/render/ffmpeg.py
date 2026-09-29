"""ffmpeg/ffprobe 실행 래퍼.

필터 그래프는 셸을 거치지 않고 인자 리스트로 넘긴다 → 윈도우 따옴표/이스케이프 문제 회피.
파일 경로는 필터 문자열 안에 넣지 않고 전부 -i 입력으로만 쓴다 (C:\\ 콜론 이스케이프 문제 회피).
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from ..util import debug, ff_path

_BIN = {"ffmpeg": "ffmpeg", "ffprobe": "ffprobe"}


class FFmpegError(RuntimeError):
    pass


def configure(ffmpeg: str | None = None, ffprobe: str | None = None) -> None:
    if ffmpeg:
        _BIN["ffmpeg"] = str(ffmpeg)
        if not ffprobe:
            # 같은 폴더의 ffprobe를 우선 사용
            cand = Path(str(ffmpeg)).with_name(Path(str(ffmpeg)).name.replace("ffmpeg", "ffprobe"))
            if cand.exists():
                _BIN["ffprobe"] = str(cand)
    if ffprobe:
        _BIN["ffprobe"] = str(ffprobe)


def available() -> bool:
    return shutil.which(_BIN["ffmpeg"]) is not None or Path(_BIN["ffmpeg"]).exists()


def run(args: list, *, desc: str = "", capture: bool = False) -> subprocess.CompletedProcess:
    cmd = [_BIN["ffmpeg"], "-hide_banner", "-nostdin", "-y", "-loglevel", "error"] + [str(a) for a in args]
    debug(desc or " ".join(cmd)[:300])
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        tail = (proc.stderr or "").strip()[-3000:]
        raise FFmpegError(f"ffmpeg 실패 ({desc}):\n{tail}\n\n명령: {' '.join(cmd)[:4000]}")
    return proc


def run_bytes(args: list, *, desc: str = "") -> bytes:
    """stdout 바이너리를 받아온다 (오디오 디코드용)."""
    cmd = [_BIN["ffmpeg"], "-hide_banner", "-nostdin", "-loglevel", "error"] + [str(a) for a in args]
    debug(desc or " ".join(cmd)[:300])
    proc = subprocess.run(cmd, capture_output=True)
    if proc.returncode != 0:
        raise FFmpegError(f"ffmpeg 실패 ({desc}):\n{proc.stderr.decode('utf-8', 'replace')[-3000:]}")
    return proc.stdout


def run_stderr(args: list, *, desc: str = "") -> str:
    """측정용 필터(loudnorm/ebur128)처럼 결과가 stderr로 나오는 명령."""
    cmd = [_BIN["ffmpeg"], "-hide_banner", "-nostdin", "-y", "-loglevel", "info"] + [str(a) for a in args]
    debug(desc)
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise FFmpegError(f"ffmpeg 실패 ({desc}):\n{proc.stderr[-3000:]}")
    return proc.stderr


@dataclass
class MediaInfo:
    duration: float
    width: int = 0
    height: int = 0
    fps: float = 0.0
    has_video: bool = False
    has_audio: bool = False


_probe_cache: dict[str, MediaInfo] = {}


def probe(path: Path) -> MediaInfo:
    key = ff_path(path)
    if key in _probe_cache:
        return _probe_cache[key]
    cmd = [_BIN["ffprobe"], "-v", "error", "-print_format", "json", "-show_format", "-show_streams", key]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise FFmpegError(f"ffprobe 실패: {path}\n{proc.stderr[-1000:]}")
    data = json.loads(proc.stdout or "{}")
    info = MediaInfo(duration=float(data.get("format", {}).get("duration") or 0.0))
    for st in data.get("streams", []):
        if st.get("codec_type") == "video" and not info.has_video:
            info.has_video = True
            info.width, info.height = int(st.get("width", 0)), int(st.get("height", 0))
            num, _, den = (st.get("avg_frame_rate") or "0/1").partition("/")
            try:
                info.fps = float(num) / float(den or 1)
            except (ValueError, ZeroDivisionError):
                info.fps = 0.0
            if not info.duration and st.get("duration"):
                info.duration = float(st["duration"])
        elif st.get("codec_type") == "audio":
            info.has_audio = True
    _probe_cache[key] = info
    return info


def measure_loudness(path: Path, *, stream_args: list | None = None) -> dict:
    """loudnorm 1패스 측정값(JSON). 무음이면 input_i가 -inf."""
    err = run_stderr(
        (stream_args or []) + ["-i", ff_path(path), "-af", "loudnorm=I=-14:TP=-1.5:LRA=20:print_format=json",
                               "-f", "null", "-"],
        desc=f"loudness 측정 {Path(path).name}",
    )
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", err, re.S)
    if not m:
        raise FFmpegError(f"loudnorm 측정 결과를 찾지 못함: {path}")
    return json.loads(m.group(0))


def measure_output(path: Path) -> dict:
    """완성본의 통합 라우드니스(LUFS)와 true peak(dBTP)."""
    err = run_stderr(["-i", ff_path(path), "-map", "0:a:0", "-af", "ebur128=peak=true", "-f", "null", "-"],
                     desc=f"결과 측정 {Path(path).name}")
    summary = err[err.rfind("Summary:"):] if "Summary:" in err else err
    i = re.search(r"I:\s*(-?[\d.]+|-inf)\s*LUFS", summary)
    tp = re.search(r"True peak:\s*Peak:\s*(-?[\d.]+|-inf)\s*dBFS", summary, re.S)
    return {
        "lufs": float(i.group(1)) if i and i.group(1) != "-inf" else float("-inf"),
        "true_peak": float(tp.group(1)) if tp and tp.group(1) != "-inf" else float("-inf"),
    }
