"""실제 악기 음색 합성 — 클래식 기타(발현)와 피아노(타현).

패드(사인파 지속음)와 달리 '한 음씩 뜯거나 치는' 소리를 만든다.
교육영상 도입부/마무리에 아르페지오로 깔면 훨씬 사람 손 같은 느낌이 난다.
"""
import numpy as np

SR = 44100


def guitar_note(freq, dur, sr=SR, damping=0.9962, seed=0):
    """클래식 기타 — Karplus-Strong 발현 합성.

    잡음으로 채운 현을 튕긴 뒤, 한 주기마다 이웃 샘플과 평균 내며 감쇠시킨다.
    실제 현의 물리를 그대로 흉내내는 방식이라 고음이 먼저 사라지는 것까지 자연스럽다.
    """
    N = max(8, int(round(sr / freq)))
    rng = np.random.default_rng(seed)
    buf = rng.uniform(-1, 1, N)
    for _ in range(4):                      # 손가락 살로 뜯는 부드러운 어택
        buf = 0.5 * (buf + np.roll(buf, 1))
    total = int(sr * dur)
    n_per = int(np.ceil(total / N))
    out = np.empty(n_per * N)
    for k in range(n_per):
        out[k * N:(k + 1) * N] = buf
        buf = damping * 0.5 * (buf + np.roll(buf, 1))
    out = out[:total]
    t = np.arange(total) / sr
    out *= np.exp(-t * 0.55)                # 전체 여운
    tail = min(int(0.06 * sr), total)       # 끝단 클릭 방지
    if tail:
        out[-tail:] *= np.linspace(1, 0, tail)
    return out * 0.5


def piano_note(freq, dur, sr=SR, **_):
    """피아노 — 배음 가산 합성.

    배음마다 감쇠 속도를 다르게 주고(고음일수록 빨리 사라짐), 약간의 비조화를 넣어
    피아노 특유의 울림을 만든다. 해머 타격감은 짧은 어택으로.
    """
    n = int(sr * dur)
    t = np.arange(n) / sr
    out = np.zeros(n)
    for h in range(1, 13):
        f = freq * h * (1 + 0.0004 * h * h)          # 비조화 (현의 강성)
        if f > sr / 2.2:
            break
        amp = 1.0 / (h ** 1.35)
        out += np.sin(2 * np.pi * f * t) * amp * np.exp(-t * (1.1 + 0.5 * h))
    out *= 1 - np.exp(-t * 420)                       # 해머 어택
    tail = min(int(0.08 * sr), n)
    if tail:
        out[-tail:] *= np.linspace(1, 0, tail)
    return out * 0.62


def arpeggio(chords, pattern, note_sec, chord_sec, total_sec, synth,
             ring=2.6, sr=SR, humanize=0.012):
    """코드 진행을 아르페지오로 연주해 한 트랙으로 만든다.

    chords    : 코드별 음 높이 목록 (낮은음 → 높은음)
    pattern   : 각 코드 안에서 짚을 음의 순서 (chords 원소의 인덱스)
    note_sec  : 음 사이 간격 / chord_sec : 코드가 바뀌는 주기
    ring      : 한 음이 울리는 길이 (겹쳐 울려야 자연스럽다)
    humanize  : 사람이 친 듯 타이밍을 미세하게 흔드는 폭 (초)
    """
    n = int(sr * total_sec) + int(sr * ring) + 1
    buf = np.zeros(n)
    rng = np.random.default_rng(11)
    k = 0
    t = 0.0
    while t < total_sec:
        chord = chords[int(t // chord_sec) % len(chords)]
        idx = pattern[k % len(pattern)]
        freq = chord[idx % len(chord)]
        note = synth(freq, ring, seed=k)
        at = t + float(rng.normal(0, humanize))
        i0 = max(0, int(at * sr))
        i1 = min(n, i0 + len(note))
        if i1 > i0:
            # 낮은 음(베이스)은 조금 크게, 높은 음은 여리게 — 손가락 세기 흉내
            vel = 1.0 if idx == 0 else 0.72 - 0.05 * idx
            buf[i0:i1] += note[:i1 - i0] * max(0.45, vel)
        k += 1
        t += note_sec
    return buf[:int(sr * total_sec)]
