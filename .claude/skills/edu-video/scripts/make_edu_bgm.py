#!/usr/bin/env python3
"""교육영상용 잔잔한 배경음 생성 (spec의 duration만 읽는다).

티저 BGM과 달리 극적인 요소 없이, 낮고 부드러운 패드만 깐다.
나레이션을 방해하지 않도록 저역 중심 + 아주 작은 음량.

사용법:
    python3 make_edu_bgm.py edu_spec.json bgm.wav
"""
import json
import struct
import sys
import wave

import numpy as np

SR = 44100


def main():
    spec = json.loads(open(sys.argv[1], encoding="utf-8").read())
    dur = float(spec["duration"])
    n = int(SR * dur)
    t = np.arange(n) / SR

    # 낮은 패드: 완전5도 + 옥타브, 살짝 디튠해서 느리게 울렁이게
    pad = (np.sin(2*np.pi*110.0*t) * 0.5
           + np.sin(2*np.pi*164.8*t) * 0.3
           + np.sin(2*np.pi*220.6*t) * 0.22
           + np.sin(2*np.pi*329.9*t) * 0.10)
    # 아주 느린 볼륨 물결 (호흡감)
    lfo = 0.78 + 0.22 * np.sin(2*np.pi*t/13.0)
    # 공기감: 저역 필터 흉내낸 노이즈 (누적합으로 갈색 노이즈화)
    rng = np.random.default_rng(7)
    air = np.cumsum(rng.standard_normal(n)).astype(np.float64)
    air /= (np.abs(air).max() + 1e-9)
    sig = pad * lfo * 0.16 + air * 0.015

    # 페이드 인 2초 / 아웃 3초
    fi, fo = int(SR*2), int(SR*3)
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
    print(f"{sys.argv[2]} 생성 완료 ({dur}s, 잔잔한 패드)")


if __name__ == "__main__":
    main()
