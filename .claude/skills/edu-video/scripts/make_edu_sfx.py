#!/usr/bin/env python3
"""교육영상용 절제된 효과음 트랙 생성.

edu_spec.json의 슬라이드 타이밍을 읽어, 그 자리에 맞는 효과음을 배치한 한 개의 wav를 만든다.
"과장되지 않게"가 원칙 — 짧고, 낮고, 작다. 나레이션 위에서 튀지 않는 수준.

효과음 3종:
  whoosh  슬라이드 전환 (저역 스윕, 0.35s) — 모든 슬라이드 시작점
  tick    항목 등장 (부드러운 톡, 0.12s) — rules/steps 카드가 뜨는 순간
  chime   마무리 (은은한 5도 차임, 1.6s) — end 슬라이드 강조 문구

사용법:
    python3 make_edu_sfx.py edu_spec.json sfx.wav
"""
import json
import sys
import wave

import numpy as np

SR = 44100


def whoosh(dur=0.35):
    """낮은 곳에서 올라왔다 사라지는 부드러운 스윕. 필터드 노이즈 대신 사인 스윕이라 잡음이 없다."""
    n = int(SR * dur)
    t = np.arange(n) / SR
    f = 90 + 260 * (t / dur) ** 1.6          # 90Hz → 350Hz
    phase = 2 * np.pi * np.cumsum(f) / SR
    env = np.sin(np.pi * (t / dur)) ** 1.4    # 부드럽게 나타났다 사라짐
    return np.sin(phase) * env * 0.22


def tick(dur=0.12):
    """항목이 얹히는 짧은 톡. 딱딱한 클릭이 아니라 나무 두드리는 느낌."""
    n = int(SR * dur)
    t = np.arange(n) / SR
    env = np.exp(-t * 34)
    tone = (np.sin(2 * np.pi * 420 * t) * 0.6
            + np.sin(2 * np.pi * 840 * t) * 0.25
            + np.sin(2 * np.pi * 1260 * t) * 0.1)
    return tone * env * 0.13


def chime(dur=1.6):
    """마무리 차임 — 완전5도(C6+G6), 길게 여운."""
    n = int(SR * dur)
    t = np.arange(n) / SR
    env = np.exp(-t * 2.4)
    tone = (np.sin(2 * np.pi * 1046.5 * t) * 0.55
            + np.sin(2 * np.pi * 1568.0 * t) * 0.35
            + np.sin(2 * np.pi * 2093.0 * t) * 0.12)
    return tone * env * 0.16


def place(buf, sound, at_sec):
    i0 = int(at_sec * SR)
    if i0 < 0:
        return
    i1 = min(len(buf), i0 + len(sound))
    if i1 <= i0:
        return
    buf[i0:i1] += sound[:i1 - i0]


def main():
    spec = json.loads(open(sys.argv[1], encoding="utf-8").read())
    dur = float(spec["duration"])
    buf = np.zeros(int(SR * dur) + SR)
    slides = spec["slides"]

    w, tk, ch = whoosh(), tick(), chime()
    n_tick = 0
    for i, s in enumerate(slides):
        t0 = float(s["start"])
        typ = s["type"]
        # 전환음: 첫 슬라이드 제외 (영상 시작은 조용히 들어간다)
        if i > 0:
            place(buf, w, t0 - 0.12)
        a0 = t0 + (0.15 if i == 0 else 0.35)
        if typ in ("rules", "steps"):
            stag = 0.4
            for j in range(len(s.get("items", []))):
                place(buf, tk, a0 + 0.25 + j * stag)
                n_tick += 1
        elif typ == "text":
            for j in range(len(s.get("lines", []))):
                place(buf, tk, a0 + 0.25 + j * 0.28)
                n_tick += 1
        elif typ == "end":
            place(buf, ch, a0 + 0.4)

    buf = buf[:int(SR * dur)]
    buf = np.clip(buf, -1, 1)
    pcm = (buf * 32767).astype("<i2")
    with wave.open(sys.argv[2], "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes(pcm.tobytes())
    print(f"{sys.argv[2]} 생성 완료 — 전환음 {len(slides)-1}개, 항목음 {n_tick}개, 마무리 차임 1개")


if __name__ == "__main__":
    main()
