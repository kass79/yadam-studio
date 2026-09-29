"""효과음 파일이 없을 때 쓰는 코드 합성 임시 효과음 (48kHz 스테레오 float32).

진짜 효과음 파일이 생기면 config.yaml 의 sfx: 에 이름→파일로 적으면 자동으로 그걸 쓴다.
"""
from __future__ import annotations

import numpy as np

SR = 48000


def _t(dur: float) -> np.ndarray:
    return np.arange(int(dur * SR), dtype=np.float32) / SR


def _st(x: np.ndarray) -> np.ndarray:
    x = x.astype(np.float32)
    peak = float(np.max(np.abs(x))) or 1.0
    x = x / peak * 0.9
    return np.stack([x, x], axis=1)


def _lowpass(x: np.ndarray, cutoff: float, taps: int = 129) -> np.ndarray:
    n = np.arange(taps) - (taps - 1) / 2
    h = np.sinc(2 * cutoff / SR * n) * np.hamming(taps)
    h /= h.sum()
    return np.convolve(x, h, mode="same").astype(np.float32)


def _bell(freq: float, dur: float, decay: float = 3.0) -> np.ndarray:
    t = _t(dur)
    env = np.exp(-t * decay) * np.minimum(1, t * 400)
    return (np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(2 * np.pi * freq * 2.01 * t)
            + 0.12 * np.sin(2 * np.pi * freq * 3.02 * t)) * env


def dingdong() -> np.ndarray:
    """지하철 안내 차임 '딩-동' (미 → 도)."""
    a = _bell(659.3, 1.2, 2.2)
    b = _bell(523.3, 1.4, 2.0)
    out = np.zeros(int(1.9 * SR), np.float32)
    out[:len(a)] += a
    off = int(0.45 * SR)
    out[off:off + len(b)] += b[:len(out) - off]
    return _st(out)


def scratch() -> np.ndarray:
    """레코드 스크래치 (앞뒤로 긁는 소리)."""
    t = _t(0.55)
    rng = np.random.default_rng(3)
    speed = np.sin(2 * np.pi * 3.2 * t) * np.exp(-t * 2)       # 앞뒤 왕복
    phase = np.cumsum(np.abs(speed) * 900 + 60) / SR
    tone = np.sign(np.sin(2 * np.pi * phase)) * 0.4 + np.sin(2 * np.pi * phase * 2.3) * 0.3
    noise = rng.standard_normal(len(t)).astype(np.float32) * (np.abs(speed) ** 1.5) * 0.9
    x = tone + _lowpass(noise, 5000)
    env = np.minimum(1, t * 200) * np.exp(-t * 3.0)
    return _st(x * env)


def heartbeat() -> np.ndarray:
    """심장박동 '두-근' 한 번."""
    t = _t(0.75)
    out = np.zeros_like(t)
    for start, amp in ((0.0, 1.0), (0.2, 0.75)):
        tt = np.clip(t - start, 0, None)
        env = np.where(t >= start, np.exp(-tt * 18) * np.minimum(1, tt * 300), 0)
        f = 58 + 25 * np.exp(-tt * 30)
        out += amp * np.sin(2 * np.pi * np.cumsum(f) / SR) * env
    return _st(_lowpass(out, 400))


def pop() -> np.ndarray:
    """'뽁'."""
    t = _t(0.16)
    f = 900 * np.exp(-t * 28) + 220
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 32) * np.minimum(1, t * 2000)
    return _st(x)


def jingle() -> np.ndarray:
    """반짝 징글 (도-미-솔-도 아르페지오)."""
    notes = [1046.5, 1318.5, 1568.0, 2093.0]
    out = np.zeros(int(1.4 * SR), np.float32)
    for i, f in enumerate(notes):
        b = _bell(f, 1.0, 4.5) * (0.8 if i < 3 else 1.0)
        off = int(i * 0.08 * SR)
        out[off:off + len(b)] += b[:len(out) - off]
    rng = np.random.default_rng(5)
    t = _t(1.4)
    shimmer = _lowpass(rng.standard_normal(len(t)).astype(np.float32), 9000) * np.exp(-t * 3) * 0.08
    shimmer = shimmer - _lowpass(shimmer, 4000)
    return _st(out + shimmer)


def punch() -> np.ndarray:
    """급줌 '휙-쿵'."""
    t = _t(0.35)
    rng = np.random.default_rng(1)
    whoosh = _lowpass(rng.standard_normal(len(t)).astype(np.float32), 2500) * np.exp(-((t - 0.06) / 0.05) ** 2)
    thump = np.sin(2 * np.pi * np.cumsum(90 * np.exp(-t * 10) + 45) / SR) * np.exp(-t * 14) * (t > 0.07)
    return _st(whoosh * 0.6 + thump)


def freeze() -> np.ndarray:
    """정지 화면 '찰칵'."""
    t = _t(0.25)
    rng = np.random.default_rng(2)
    n = rng.standard_normal(len(t)).astype(np.float32)
    env = np.exp(-t * 90) + 0.7 * np.exp(-np.clip(t - 0.09, 0, None) * 90) * (t > 0.09)
    return _st(n * env)


def whoosh() -> np.ndarray:
    t = _t(0.5)
    rng = np.random.default_rng(4)
    n = _lowpass(rng.standard_normal(len(t)).astype(np.float32), 1800)
    return _st(n * np.sin(np.pi * t / 0.5) ** 2)


SYNTHS = {
    "dingdong": dingdong, "scratch": scratch, "heartbeat": heartbeat, "pop": pop, "jingle": jingle,
    "punch": punch, "freeze": freeze, "whoosh": whoosh,
}


def synth(name: str) -> np.ndarray:
    return SYNTHS.get(name, pop)()
