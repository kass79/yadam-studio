#!/usr/bin/env python3
"""교육영상용 잔잔한 배경음악 생성.

v2 (2026-08): 노이즈 성분 완전 제거 — 잡음처럼 들린다는 피드백 반영.
대신 코드 진행(C → Am → F → G, 8초마다)이 있는 부드러운 패드로 교체.

v3 (2026-08): **음악을 영상 내내 깔지 않는다.** 설명 구간에는 나레이션만 남기고,
도입부와 마무리에만 음악을 넣는 것이 기본(bookend). 카스 피드백:
"음악베이스는 없어도 될 것 같다, 아니면 적절한 일부 구간만".

구간은 spec의 `music` 필드로 정한다:
    없으면          → bookend 자동 (첫 슬라이드 + 마지막 슬라이드)
    "none"          → 음악 없음 (무음 파일 생성, 효과음과 나레이션만)
    "full"          → 처음부터 끝까지 (예전 방식)
    [[0,11],[79,90]] → 구간을 직접 지정 (초 단위)

사용법:
    python3 make_edu_bgm.py edu_spec.json bgm.wav
"""
import json
import sys
import wave

import numpy as np

SR = 44100
XFADE = 1.8  # 코드 사이 크로스페이드

# 분위기(mood)별 코드 진행 + 음색. spec의 "mood" 필드로 고른다.
#   warm    따뜻한 장조 — 일반 안내·수칙 교육용 (예전 기본값)
#   solemn  차분한 단조 — 사고사례 교육에 어울림 (현재 기본값)
#   minimal 지속음 하나 — 브리핑처럼 담백하게, 존재감 최소
#   formal  낮고 두꺼운 화음 — 공식 발표 톤, 무게감
MOODS = {
    "warm": {
        "chords": [
            [130.81, 164.81, 196.00, 261.63],  # C
            [110.00, 130.81, 164.81, 220.00],  # Am
            [87.31, 110.00, 130.81, 174.61],   # F
            [98.00, 123.47, 146.83, 196.00],   # G
        ],
        "gains": [0.5, 0.22, 0.3, 0.14],
        "sec": 8.0, "detune": 0.35, "harm": 0.0,
    },
    "solemn": {
        "chords": [
            [110.00, 130.81, 164.81, 220.00],  # Am
            [87.31, 110.00, 130.81, 174.61],   # F
            [73.42, 87.31, 110.00, 146.83],    # Dm
            [82.41, 98.00, 123.47, 164.81],    # Em
        ],
        "gains": [0.52, 0.24, 0.28, 0.12],
        "sec": 9.0, "detune": 0.30, "harm": 0.0,
    },
    "minimal": {
        "chords": [
            [98.00, 146.83, 196.00, 293.66],   # G 드론 (근음+5도+옥타브)
            [98.00, 146.83, 196.00, 261.63],   # 위 음만 살짝 이동
        ],
        "gains": [0.55, 0.26, 0.14, 0.06],
        "sec": 14.0, "detune": 0.18, "harm": 0.0,
    },
    "formal": {
        "chords": [
            [65.41, 98.00, 130.81, 196.00],    # C 낮게
            [73.42, 110.00, 146.83, 220.00],   # D 낮게
            [87.31, 130.81, 174.61, 261.63],   # F 낮게
            [82.41, 123.47, 164.81, 246.94],   # E 낮게
        ],
        "gains": [0.5, 0.3, 0.2, 0.1],
        "sec": 10.0, "detune": 0.42, "harm": 0.22,  # 배음 → 현악기 같은 두께
    },
}


def music_windows(spec, dur):
    """음악이 흐를 구간 [(시작, 끝), ...] 을 정한다. 기본은 도입부+마무리."""
    m = spec.get("music")
    if m == "none":
        return []
    if m == "full":
        return [(0.0, dur)]
    if isinstance(m, list):
        return [(float(a), float(b)) for a, b in m]
    # 기본 bookend: 첫 슬라이드가 끝날 때까지 + 마지막 슬라이드 조금 전부터
    slides = spec.get("slides", [])
    if not slides:
        return [(0.0, dur)]
    head_end = float(slides[0]["start"]) + float(slides[0]["dur"]) + 1.0
    tail_start = max(head_end, float(slides[-1]["start"]) - 1.5)
    return [(0.0, head_end), (tail_start, dur)]


def main():
    spec = json.loads(open(sys.argv[1], encoding="utf-8").read())
    dur = float(spec["duration"])
    n = int(SR * dur)
    t = np.arange(n) / SR
    sig = np.zeros(n)

    mood_name = spec.get("mood", "solemn")
    if mood_name not in MOODS:
        raise SystemExit(f"모르는 mood: {mood_name} (가능: {', '.join(MOODS)})")
    M = MOODS[mood_name]
    chords, gains = M["chords"], M["gains"]
    chord_sec, detune, harm = M["sec"], M["detune"], M["harm"]

    n_seg = int(np.ceil(dur / chord_sec)) + 1
    for k in range(n_seg):
        t0 = k * chord_sec
        if t0 >= dur:
            break
        freqs = chords[k % len(chords)]
        # 세그먼트 엔벨로프: 크로스페이드 램프 (양끝 겹침)
        seg = np.zeros(n)
        i0 = max(0, int((t0 - XFADE) * SR))
        i1 = min(n, int((t0 + chord_sec) * SR))
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
        for f, g in zip(freqs, gains):
            tone += np.sin(2 * np.pi * f * tt) * g
            tone += np.sin(2 * np.pi * (f * 1.003) * tt) * g * detune  # 살짝 디튠 (풍성함)
            if harm:  # 홀수 배음 — 현악기 같은 두께
                tone += np.sin(2 * np.pi * (f * 3) * tt) * g * harm * 0.5
                tone += np.sin(2 * np.pi * (f * 5) * tt) * g * harm * 0.2
        seg[i0:i1] = tone * env
        sig += seg

    # 아주 느린 호흡감
    sig *= 0.8 + 0.2 * np.sin(2 * np.pi * t / 11.0)
    sig = sig / (np.abs(sig).max() + 1e-9) * 0.5

    # 구간 마스크 — 지정 구간에서만 소리가 나고, 양끝은 부드럽게 드나든다
    wins = music_windows(spec, dur)
    mask = np.zeros(n)
    FADE = 2.5
    for a, b in wins:
        i0, i1 = max(0, int(a * SR)), min(n, int(b * SR))
        if i1 <= i0:
            continue
        seg = np.ones(i1 - i0)
        f = min(int(FADE * SR), (i1 - i0) // 2)
        if f > 0:
            seg[:f] = np.linspace(0, 1, f)
            seg[-f:] = np.linspace(1, 0, f)
        mask[i0:i1] = np.maximum(mask[i0:i1], seg)
    sig *= mask

    pcm = (np.clip(sig, -1, 1) * 32767).astype("<i2")
    with wave.open(sys.argv[2], "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    desc = ", ".join(f"{a:.0f}~{b:.0f}s" for a, b in wins) or "음악 없음"
    print(f"{sys.argv[2]} 생성 완료 ({dur}s) — 분위기: {mood_name}, 음악 구간: {desc}")


if __name__ == "__main__":
    main()
