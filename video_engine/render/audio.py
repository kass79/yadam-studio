"""오디오: 대사/BGM/효과음 버스를 만들고 최종 믹스(WAV)까지. AAC 인코딩은 여기서 하지 않는다.

예전 문제 2가지 대응:
 (a) AAC 이중 인코딩으로 true peak가 0dBFS 초과
     → 중간 결과는 전부 float WAV. AAC는 최종 mux에서 딱 한 번.
       리미터는 loudnorm "뒤"에, 192kHz로 올려서(true peak 근사) 건다.
 (b) sidechaincompress가 키(대사) 트랙이 끝나는 순간 BGM을 잘라먹음
     → 대사를 asplit 해서 키 쪽에만 apad (무한 무음 연장). BGM 쪽 길이가 출력 길이를 결정.
"""
from __future__ import annotations

import json
import struct
from pathlib import Path

import numpy as np

from .. import sfx_synth
from ..util import ff_path, file_sig, fnum, log
from . import ffmpeg

SR = 48000


def decode(path: Path, filters: list[str] | None = None) -> np.ndarray:
    args = ["-i", ff_path(path), "-vn"]
    if filters:
        args += ["-af", ",".join(filters)]
    args += ["-f", "f32le", "-ac", "2", "-ar", str(SR), "-"]
    raw = ffmpeg.run_bytes(args, desc=f"디코드 {Path(path).name}")
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).copy()


def write_wav(path: Path, x: np.ndarray) -> Path:
    """32bit float WAV (WAVE_FORMAT_IEEE_FLOAT)."""
    x = np.ascontiguousarray(x, dtype=np.float32)
    ch = x.shape[1] if x.ndim == 2 else 1
    data = x.tobytes()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVE")
        f.write(b"fmt " + struct.pack("<IHHIIHH", 16, 3, ch, SR, SR * ch * 4, ch * 4, 32))
        f.write(b"data" + struct.pack("<I", len(data)) + data)
    return path


def place(bus: np.ndarray, clip: np.ndarray, at: float) -> None:
    i = int(round(at * SR))
    if i < 0:
        clip = clip[-i:]
        i = 0
    n = min(len(clip), len(bus) - i)
    if n > 0:
        bus[i:i + n] += clip[:n]


def db(x: float) -> float:
    return float(10 ** (x / 20))


class _Measure:
    """BGM 라우드니스 측정 캐시 (work/_measure.json)."""

    def __init__(self, path: Path):
        self.path = path
        try:
            self.data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.data = {}

    def lufs(self, f: Path) -> float:
        key = file_sig(f)
        if key not in self.data:
            m = ffmpeg.measure_loudness(f)
            v = m.get("input_i", "-inf")
            self.data[key] = float(v) if v not in ("-inf", "inf") else -70.0
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=1), encoding="utf-8")
        return self.data[key]


# ─────────────────────────── 효과음 ───────────────────────────

_sfx_cache: dict[str, np.ndarray] = {}


def load_sfx(name: str, settings: dict) -> np.ndarray:
    if name in _sfx_cache:
        return _sfx_cache[name]
    item = (settings.get("sfx") or {}).get(name) or {}
    f = item.get("file") if isinstance(item, dict) else item
    x = None
    if f and Path(f).exists():
        x = decode(Path(f))
    else:
        if f:
            log(f"  효과음 '{name}' 파일이 없어 임시 합성음 사용: {f}")
        x = sfx_synth.synth(name)
    peak = float(np.max(np.abs(x))) or 1.0
    target = db(float((settings.get("audio") or {}).get("sfx_peak_db", -8.0))
                + float(item.get("gain_db", 0.0) if isinstance(item, dict) else 0.0))
    x = x / peak * target
    _sfx_cache[name] = x
    return x


# ─────────────────────────── BGM ───────────────────────────

def _parse_cue(cue) -> dict | None:
    if cue is None or cue == "same":
        return None
    if isinstance(cue, str):
        if cue in ("stop", "fade_out"):
            return {"kind": "stop", "fade": 0.8 if cue == "fade_out" else 0.25}
        return {"kind": "play", "track": cue}
    if isinstance(cue, dict):
        if cue.get("stop") or cue.get("kind") == "stop":
            return {"kind": "stop", "fade": float(cue.get("fade", 0.8)), "at": float(cue.get("at", 0.0))}
        return {"kind": "play", "track": cue.get("track"), "at": float(cue.get("at", 0.0)),
                "fade_in": float(cue.get("fade_in", 0.3)), "offset": float(cue.get("offset", 0.0)),
                "volume_db": float(cue.get("volume_db", 0.0))}
    raise ValueError(f"bgm_cue 표기 오류: {cue}")


def bgm_events(tl) -> list[dict]:
    ev = []
    if tl.bgm_start:
        ev.append(dict(tl.bgm_start, kind="play", t=0.0))
    for p in tl.plans:
        c = _parse_cue(p.cut.bgm_cue)
        if c:
            c["t"] = p.start + float(c.get("at", 0.0))
            ev.append(c)
        for e in p.bgm_events:
            ev.append(dict(e, t=p.start + float(e["at"])))
    ev.sort(key=lambda e: e["t"])
    return ev


def bgm_state_at(tl, t: float) -> dict | None:
    """전체 타임라인에서 t초 시점에 흐르던 BGM (쇼츠 시작용)."""
    cur = None
    for e in bgm_events(tl):
        if e["t"] > t + 1e-6:
            break
        if e["kind"] == "play":
            cur = {"track": e["track"], "offset": e.get("offset", 0.0) + 0.0, "_t": e["t"],
                   "volume_db": e.get("volume_db", 0.0), "fade_in": 0.2}
        else:
            cur = None
    if cur:
        cur["offset"] += t - cur.pop("_t")
    return cur


def _track_audio(name: str, bgm: dict, settings: dict, meas: _Measure, cache: dict) -> np.ndarray:
    if name in cache:
        return cache[name]
    item = bgm.get(name)
    if not item or not item.get("file"):
        raise ValueError(f"bgm 트랙 '{name}'이 매니페스트 bgm: 에 없습니다.")
    f = Path(item["file"])
    x = decode(f)
    target = float((settings.get("audio") or {}).get("bgm_lufs", -28.0))
    gain = target - meas.lufs(f) + float(item.get("volume_db", 0.0))
    cache[name] = x * db(gain)
    return cache[name]


def _brake(x: np.ndarray, pos: int, dur: float) -> np.ndarray:
    """턴테이블 멈춤: 재생 속도 1→0 으로 dur초 동안 떨어진다."""
    n = int(dur * SR)
    tau = np.arange(n, dtype=np.float64) / SR
    phase = tau - tau * tau / (2 * dur)
    idx = pos + phase * SR
    src = np.arange(len(x))
    out = np.stack([np.interp(idx, src, x[:, c]) for c in range(2)], axis=1).astype(np.float32)
    return out * np.linspace(1, 0.2, n, dtype=np.float32)[:, None]


def build_bgm_bus(tl, bgm: dict, settings: dict, total: float, meas: _Measure) -> np.ndarray:
    N = int(round(total * SR))
    bus = np.zeros((N, 2), np.float32)
    cache: dict = {}
    end_fade = float((settings.get("audio") or {}).get("bgm_end_fade", 1.0))
    xfade = 0.6
    events = bgm_events(tl)
    active = None     # {"track", "t", "offset", "fade_in", "volume_db"}

    def flush(seg, t_end: float, fade: float, brake: float = 0.0):
        if seg is None:
            return
        src = _track_audio(seg["track"], bgm, settings, meas, cache)
        if len(src) == 0:
            return
        start = int(round(seg["t"] * SR))
        length = int(round((t_end - seg["t"]) * SR)) + (int(fade * SR) if not brake else 0)
        length = max(0, min(length, N - start))
        if length <= 0:
            return
        off = int(seg.get("offset", 0.0) * SR)
        loop = (bgm.get(seg["track"]) or {}).get("loop", True)
        idx = np.arange(off, off + length + int(brake * SR) + 1)
        idx = idx % len(src) if loop else np.clip(idx, 0, len(src) - 1)
        body = src[idx[:length]].copy()
        if not loop and off + length > len(src):
            body[max(0, len(src) - off):] = 0
        fi = int(seg.get("fade_in", 0.3) * SR)
        if fi > 0:
            k = min(fi, length)
            body[:k] *= np.linspace(0, 1, fi, dtype=np.float32)[:k, None]
        body *= db(seg.get("volume_db", 0.0))
        if brake > 0:
            cut_i = int(round((t_end - seg["t"]) * SR))
            cut_i = min(cut_i, length)
            pos = off + cut_i
            ext = np.concatenate([src, src]) if loop else src
            tail = _brake(ext, pos % len(src) if loop else pos, brake)
            tail *= db(seg.get("volume_db", 0.0))
            body = body[:cut_i]
            place(bus, body, seg["t"])
            place(bus, tail, seg["t"] + cut_i / SR)
            return
        fo = int(fade * SR)
        if fo > 0:
            k = min(fo, len(body))
            body[len(body) - k:] *= np.linspace(1, 0, k, dtype=np.float32)[:, None]
        place(bus, body, seg["t"])

    for e in events:
        if e["kind"] == "play":
            flush(active, e["t"], xfade)
            active = {"track": e["track"], "t": e["t"], "offset": e.get("offset", 0.0),
                      "fade_in": e.get("fade_in", 0.3), "volume_db": e.get("volume_db", 0.0)}
        elif e["kind"] == "stop":
            flush(active, e["t"], e.get("fade", 0.8))
            active = None
        elif e["kind"] == "brake":
            flush(active, e["t"], 0.0, brake=float(e.get("brake", 0.35)))
            active = None
    if active:
        flush(active, max(active["t"], total - end_fade), end_fade)
    return bus


# ─────────────────────────── 버스 만들기 + 최종 믹스 ───────────────────────────

def build_buses(tl, manifest, settings: dict, work: Path) -> dict:
    N = int(round(tl.total * SR))
    dia = np.zeros((N, 2), np.float32)
    sfx = np.zeros((N, 2), np.float32)
    for p in tl.plans:
        if p.audio_src is not None:
            clip = decode(p.audio_src, p.audio_filters or None)
            end = int(round((p.duration - p.lead) * SR))   # 컷 밖으로 넘치는 소리는 자름
            place(dia, clip[:end], p.start + p.lead)
        for ev in p.sfx:
            place(sfx, load_sfx(ev.name, settings) * db(ev.gain_db), p.start + ev.at)
    meas = _Measure(work / "_measure.json")
    bgm = build_bgm_bus(tl, manifest.bgm, settings, tl.total, meas)
    paths = {"dialogue": write_wav(work / "bus_dialogue.wav", dia), "bgm": write_wav(work / "bus_bgm.wav", bgm),
             "sfx": write_wav(work / "bus_sfx.wav", sfx)}
    return paths


def _loudnorm_args(m: dict, target: float) -> str | None:
    try:
        i = float(m["input_i"])
    except (KeyError, ValueError):
        return None
    if i < -60:
        return None
    lra = max(20.0, min(50.0, float(m.get("input_lra", 7)) + 2))
    return (f"loudnorm=I={fnum(target)}:TP=-1:LRA={fnum(lra)}:measured_I={m['input_i']}:"
            f"measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:"
            f"offset={m['target_offset']}:linear=true")


def loop_crossfade(x: np.ndarray, L: float) -> np.ndarray:
    """쇼츠 루프: 앞 L초를 떼어 끝에 크로스페이드로 겹친다 → 끝이 처음으로 자연스럽게 이어짐.
    결과 길이 = 원래 길이 - L. (영상도 같은 방식으로 처리한다)"""
    n = int(round(L * SR))
    if n <= 0 or len(x) <= 2 * n:
        return x
    head, body = x[:n], x[n:].copy()
    k = np.linspace(0, np.pi / 2, n, dtype=np.float32)[:, None]
    body[-n:] = body[-n:] * np.cos(k) + head * np.sin(k)
    return body


def final_mix(buses: dict, settings: dict, total: float, out: Path, *, loop: float = 0.0,
              ceiling_offset: float = 0.0) -> Path:
    """버스 3개 → 대사 loudnorm → 덕킹 → 합치기 → (쇼츠 루프) → 리미터 → float WAV."""
    a = settings.get("audio") or {}
    target = float(a.get("target_lufs", -14.0))
    mode = a.get("normalize", "dialogue")
    duck, sduck = a.get("duck") or {}, a.get("sfx_duck") or {}
    work = out.parent

    def sc(d: dict) -> str:
        return (f"sidechaincompress=threshold={fnum(d.get('threshold', 0.02))}:ratio={fnum(d.get('ratio', 8))}:"
                f"attack={fnum(d.get('attack', 15))}:release={fnum(d.get('release', 400))}:"
                f"makeup={fnum(d.get('makeup', 1))}")

    dnorm = None
    if mode == "dialogue":
        dnorm = _loudnorm_args(ffmpeg.measure_loudness(buses["dialogue"]), target)
    d_chain = (dnorm + f",aresample={SR}," if dnorm else "") + "asplit=3[dm][dk1][dk2]"
    L = float(loop)
    out_len = total - L if L > 0 else total
    graph = (
        f"[0:a]{d_chain};"
        f"[dk1]apad[k1];[dk2]apad[k2];"            # (b) 키 트랙만 무한 연장 → BGM이 잘리지 않음
        f"[1:a][k1]{sc(duck)}[bd];"
        f"[2:a][k2]{sc(sduck)}[sd];"
        f"[dm][bd][sd]amix=inputs=3:normalize=0:duration=longest:dropout_transition=0,"
        f"apad=whole_dur={fnum(total)},atrim=duration={fnum(total)}[pre]"
    )
    pre = work / "mix_pre.wav"
    ffmpeg.run(["-i", ff_path(buses["dialogue"]), "-i", ff_path(buses["bgm"]), "-i", ff_path(buses["sfx"]),
                "-filter_complex", graph, "-map", "[pre]", "-c:a", "pcm_f32le", "-ar", str(SR), ff_path(pre)],
               desc="오디오 믹스(덕킹)")
    if L > 0:
        pre = write_wav(work / "mix_pre_loop.wav", loop_crossfade(decode(pre), L))
    # 2단계: (program 모드면 전체 loudnorm) → 192k 리미터 → 48k
    chain = []
    if mode == "program":
        pn = _loudnorm_args(ffmpeg.measure_loudness(pre), target)
        if pn:
            chain.append(pn)
    ceiling = float(a.get("true_peak", -1.5)) - ceiling_offset
    lim = max(0.0625, min(1.0, db(ceiling)))
    chain += ["aresample=192000", f"alimiter=limit={fnum(lim)}:attack=5:release=60:level=false:latency=true",
              f"aresample={SR}", f"atrim=duration={fnum(out_len)}"]
    ffmpeg.run(["-i", ff_path(pre), "-af", ",".join(chain), "-c:a", "pcm_f32le", "-ar", str(SR), ff_path(out)],
               desc="리미터")
    return out
