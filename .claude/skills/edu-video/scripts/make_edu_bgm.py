#!/usr/bin/env python3
"""교육영상용 잔잔한 배경음악 생성 (spec의 duration만 읽는다).

v2 (2026-08): 노이즈 성분 완전 제거 — 잡음처럼 들린다는 피드백 반영.
대신 코드 진행(C → Am → F → G, 8초마다)이 있는 부드러운 패드로 교체.
나레이션을 방해하지 않도록 저역 중심 + 작은 음량 + 느린 크로스페이드.

사용법:
    python3 make_edu_bgm.py edu_spec.json bgm.wav
"""
import json
import sys
import wave

import numpy as np

SR = 44100
CHORD_SEC = 8.0
XFADE = 1.8  # 코드 사이 크로스페이드

# 코드별 구성음 (root, 3rd, 5th, octave) — 낮은 음역
CHORDS = [
    [130.81, 164.81, 196.00, 261.63],  # C
    [110.00, 130.81, 164.81, 220.00],  # Am
    [87.31, 110.00, 130.81, 174.61],   # F
    [98.00, 123.47, 146.83, 196.00],   # G
]
GAINS = [0.5, 0.22, 0.3, 0.14]


def main():
    spec = json.loads(open(sys.argv[1], encoding="utf-8").read())
    dur = float(spec["duration"])
    n = int(SR * dur)
    t = np.arange(n) / SR
    sig = np.zeros(n)

    n_seg = int(np.ceil(dur / CHORD_SEC)) + 1
    for k in range(n_seg):
        t0 = k * CHORD_SEC
        if t0 >= dur:
            break
        freqs = CHORDS[k % len(CHORDS)]
        # 세그먼트 엔벨로프: 크로스페이드 램프 (양끝 겹침)
        seg = np.zeros(n)
        i0 = max(0, int((t0 - XFADE) * SR))
        i1 = min(n, int((t0 + CHORD_SEC) * SR))
        if i1 <= i0:
            continue
        m = i1 - i0
        env = np.ones(m)
        ramp = min(int(XFADE * SR), m // 2)
        if ramp > 0:
            env[:ramp] = np.linspace(0, 1, ramp)
            env[-ramp:] = np.linspace(1, 0, ramp)
        tt = t[i0:i1]
        tone = np.zeros(m)
        for f, g in zip(freqs, GAINS):
            tone += np.sin(2 * np.pi * f * tt) * g
            tone += np.sin(2 * np.pi * (f * 1.003) * tt) * g * 0.35  # 살짝 디튠 (풍성함)
        seg[i0:i1] = tone * env
        sig += seg

    # 아주 느린 호흡감
    sig *= 0.8 + 0.2 * np.sin(2 * np.pi * t / 11.0)

    # 페이드 인 2초 / 아웃 4초
    fi, fo = int(SR * 2), int(SR * 4)
    env = np.ones(n)
    env[:fi] = np.linspace(0, 1, fi)
    env[-fo:] = np.linspace(1, 0, fo)
    sig *= env

    sig = np.clip(sig / (np.abs(sig).max() + 1e-9) * 0.5, -1, 1)
    pcm = (sig * 32767).astype("<i2")
    with wave.open(sys.argv[2], "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(f"{sys.argv[2]} 생성 완료 ({dur}s, 코드 패드 v2 — 노이즈 없음)")


if __name__ == "__main__":
    main()
