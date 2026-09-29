"""CutPlan → ffmpeg 명령 (컷 하나 = 영상 파일 하나, 소리 없음).

필터 순서:
  소스 준비(커버 맞춤) → 시간 왜곡(정지/슬로모션) → 카메라(줌·흔들림) → [쇼츠면 가운데 9:16 크롭]
  → 색/화면 필터(post) → 오버레이 레이어(z 순서) → 길이 자르기
"""
from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path

from .. import __version__
from ..plan import CutPlan
from ..util import ff_path, file_sig, fnum, stable_hash
from . import ffmpeg


def encoder_args(settings: dict, *, final: bool, draft: bool = False) -> list[str]:
    v = settings.get("video") or {}
    if not final:
        preset = "ultrafast" if draft else v.get("intermediate_preset", "veryfast")
        crf = 23 if draft else v.get("intermediate_crf", 12)
        return ["-c:v", "libx264", "-preset", str(preset), "-crf", str(crf), "-bf", "0", "-pix_fmt", "yuv420p"]
    enc = v.get("encoder", "libx264")
    if draft:
        return ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p"]
    if "nvenc" in enc:
        return ["-c:v", enc, "-preset", str(v.get("nvenc_preset", "p5")), "-rc", "vbr", "-cq",
                str(v.get("nvenc_cq", 19)), "-b:v", "0", "-profile:v", "high", "-pix_fmt", "yuv420p"]
    return ["-c:v", enc, "-preset", str(v.get("preset", "medium")), "-crf", str(v.get("crf", 18)),
            "-profile:v", "high", "-pix_fmt", "yuv420p"]


def _tvar(expr: str) -> str:
    """효과가 쓴 시간 변수 t → zoompan의 입력 시각 it."""
    return re.sub(r"\bt\b", "it", expr)


def _even(x: float) -> int:
    return max(2, int(math.ceil(x / 2.0)) * 2)


def build_filter(plan: CutPlan) -> tuple[list[str], str]:
    """(입력 인자, filter_complex 문자열). 출력 라벨은 [vout]."""
    D = plan.duration
    fps = plan.fps
    Ws, Hs = plan.scene
    W, H = plan.canvas
    fx, fy = plan.focus
    has_cam = bool(plan.zoom_terms or plan.pan_terms)
    zmax = plan.zoom_max if plan.zoom_terms else (1.04 if has_cam else 1.0)
    # 정지 이미지는 2배 크게 준비해 줌 이동이 1px씩 떨리지 않게 (camera.supersample)
    ss = 1.0
    if plan.cut.is_still and has_cam:
        ss = float((plan.settings.get("camera") or {}).get("supersample", 2.0))
    Wp, Hp = _even(Ws * zmax * ss), _even(Hs * zmax * ss)
    args: list[str] = []
    chains: list[str] = []
    cut = plan.cut

    # 0번 입력: 소스
    if cut.media is None:
        args += ["-f", "lavfi", "-i", f"color=c=0x202020:s={Wp}x{Hp}:r={fps}:d={fnum(D + 0.5)}"]
        src = "[0:v]"
    elif cut.is_still:
        args += ["-loop", "1", "-framerate", str(fps), "-t", fnum(D + 0.5), "-i", ff_path(cut.media)]
        src = "[0:v]"
    else:
        args += ["-i", ff_path(cut.media)]
        src = "[0:v]"
    steps: list[str] = ["setsar=1"] if cut.media is None else []
    if cut.media is not None:
        steps.append(f"scale={Wp}:{Hp}:force_original_aspect_ratio=increase:flags=lanczos")
        steps.append(f"crop={Wp}:{Hp}:(iw-{Wp})*{fnum(fx)}:(ih-{Hp})*{fnum(fy)}")
        steps.append("setsar=1")
    if not cut.is_still:
        remap = plan.source_remap_expr()
        if remap:
            steps.insert(0, f"setpts='({remap})/TB'")
            steps.insert(1, f"fps={fps}")
        else:
            steps.insert(0, f"fps={fps}")
        steps.append(f"tpad=start_mode=clone:start_duration={fnum(plan.lead)}:stop_mode=clone:"
                     f"stop_duration={fnum(D + 1)}")
    steps.append(f"trim=duration={fnum(D)}")
    steps.append("setpts=PTS-STARTPTS")

    # 카메라: zoompan (프레임마다 줌/위치, 출력 크기 고정). scale+crop 방식은 crop이 바뀐 프레임 크기를
    # 다시 읽지 않아 줌이 왼쪽 위로 쏠리는 문제가 있어 쓰지 않는다.
    if has_cam:
        Z = "*".join(f"({z})" for z in plan.zoom_terms) or "1.04"
        px = "+".join(f"({x})" for x, _ in plan.pan_terms) or "0"
        py = "+".join(f"({y})" for _, y in plan.pan_terms) or "0"
        Z, px, py = (_tvar(e) for e in (Z, px, py))
        steps.append(f"zoompan=z='min(max({Z},1),{fnum(zmax * 1.001)})':"
                     f"x='clip((iw-iw/zoom)*{fnum(fx)}+({px})*iw/zoom/{Ws},0,iw-iw/zoom)':"
                     f"y='clip((ih-ih/zoom)*{fnum(fy)}+({py})*ih/zoom/{Hs},0,ih-ih/zoom)':"
                     f"d=1:s={Ws}x{Hs}:fps={fps}")
        steps.append("setsar=1")
    elif (Wp, Hp) != (Ws, Hs):
        steps.append(f"scale={Ws}:{Hs}")
    if (Ws, Hs) != (W, H):   # 쇼츠: 가운데 세로 크롭
        steps.append(f"crop={W}:{H}:(iw-{W})/2:(ih-{H})/2")
    steps.extend(plan.post)
    steps.append("format=yuv420p")
    chains.append(src + ",".join(steps) + "[base]")
    cur = "base"

    # 오버레이 레이어
    layers = sorted(plan.layers, key=lambda l: l.z)
    for j, lay in enumerate(layers, start=1):
        if lay.sequence:
            args += ["-framerate", str(fps), "-loop", "1", "-t", fnum(D + 0.5), "-i", ff_path(lay.src)]
        else:
            args += ["-loop", "1", "-framerate", str(fps), "-t", fnum(D + 0.5), "-i", ff_path(lay.src)]
        pre = ",".join(["format=rgba"] + lay.filters)
        chains.append(f"[{j}:v]{pre}[L{j}]")
        nxt = f"o{j}"
        chains.append(f"[{cur}][L{j}]overlay=x='{lay.x}':y='{lay.y}':"
                      f"enable='between(t,{fnum(lay.start)},{fnum(lay.end)})':eof_action=pass[{nxt}]")
        cur = nxt
    chains.append(f"[{cur}]trim=duration={fnum(D)},setpts=PTS-STARTPTS,setsar=1,format=yuv420p[vout]")
    return args, ";\n".join(chains)


def _content_sig(p: Path) -> str:
    try:
        if p.is_file():
            return hashlib.sha1(p.read_bytes()).hexdigest()[:16]
    except OSError:
        pass
    return file_sig(p)


def cache_key(plan: CutPlan, settings: dict, draft: bool) -> str:
    args, graph = build_filter(plan)
    return stable_hash(__version__, graph, [a for a in args], file_sig(plan.cut.media),
                       [_content_sig(l.src) for l in plan.layers if not l.sequence],
                       encoder_args(settings, final=False, draft=draft), plan.fps, plan.duration)


def render_segment(plan: CutPlan, out: Path, settings: dict, *, draft: bool = False) -> Path:
    args, graph = build_filter(plan)
    frames = int(round(plan.duration * plan.fps))
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".part.mp4")
    ffmpeg.run(args + ["-filter_complex", graph, "-map", "[vout]", "-an", "-frames:v", str(frames),
                       "-r", str(plan.fps)] + encoder_args(settings, final=False, draft=draft)
               + ["-g", str(plan.fps), ff_path(tmp)],
               desc=f"컷 {plan.cut.id} 렌더")
    tmp.replace(out)
    return out


def render_xfade(prev_seg: Path, prev_dur: float, cur_seg: Path, plan: CutPlan, out: Path, settings: dict,
                 *, draft: bool = False) -> Path:
    """앞 컷 꼬리(d초)와 이 컷을 크로스페이드한 새 컷 파일. 길이는 이 컷과 같다."""
    d = plan.xfade_in["duration"]
    kind = plan.xfade_in.get("transition", "fade")
    frames = int(round(plan.duration * plan.fps))
    tmp = out.with_suffix(".part.mp4")
    graph = (f"[0:v]trim=duration={fnum(d)},setpts=PTS-STARTPTS[a];[1:v]setpts=PTS-STARTPTS[b];"
             f"[a][b]xfade=transition={kind}:duration={fnum(d)}:offset=0,format=yuv420p[v]")
    ffmpeg.run(["-ss", fnum(prev_dur - d), "-i", ff_path(prev_seg), "-i", ff_path(cur_seg),
                "-filter_complex", graph, "-map", "[v]", "-frames:v", str(frames), "-r", str(plan.fps)]
               + encoder_args(settings, final=False, draft=draft) + ["-g", str(plan.fps), ff_path(tmp)],
               desc=f"컷 {plan.cut.id} 크로스페이드")
    tmp.replace(out)
    return out
