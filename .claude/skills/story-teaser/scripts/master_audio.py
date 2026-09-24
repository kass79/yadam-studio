#!/usr/bin/env python3
"""티저 소리 마감: 나레이션 + BGM → 방송 품질 믹스 → 영상에 입혀 최종 mp4.

예전 방식(amix에 BGM 볼륨 고정 0.32)과 다른 점:
  1. 더킹 — 목소리가 나오는 동안만 BGM을 일정하게 -9dB 내리고, 말이 끝나면 되돌린다.
     그래서 BGM을 쉬는 구간에서 더 크게 깔 수 있다 (분위기↑, 대사 가림↓).
     ※ ffmpeg 자동 감지(sidechaincompress)는 실측에서 문장마다 -7~-20dB로 들쭉날쭉했다.
       나레이션 위치를 이미 알고 있으므로 시각 기반 곡선으로 일정하게 내린다.
  2. 목소리 다듬기 — 저역 웅웅거림 제거, 발음 대역 살짝 보강, 컴프레서로 크기 고르게,
     아주 짧은 잔향으로 '예배당·방송실' 같은 공간감.
  3. 유튜브 표준 음량 — 2패스 loudnorm으로 -14 LUFS / 최대 -1.5 dBTP.
     (유튜브는 -14로 맞춰 재생하므로, 이보다 작으면 다른 영상보다 작게 들린다.)

사용법:
    python3 master_audio.py renders/x.mp4 delays.json voice/ bgm.wav 최종.mp4 [--reverb=church|none]

delays.json = {"01": 200, "02": 2490, ...}  (각 voice/<키>.mp3 를 몇 ms에 놓을지)
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import wave

TARGET_I, TARGET_TP, TARGET_LRA = -14.0, -1.5, 11.0
TP_HEADROOM = 0.5   # AAC 인코딩이 봉우리를 0.1~0.3dB 올린다 (실측 -1.5 → -1.4) — 미리 여유
DUCK_DB = -9.0      # 목소리 밑 BGM 감쇠 (방송 표준 8~12dB)
ATTACK, RELEASE = 0.15, 0.45   # 내려가기 시작(말 시작 전) / 돌아오는 시간(말 끝난 뒤)


def speech_len(p):
    """꼬리 무음만 뺀 실제 발화 길이 (문장 중간 쉼은 무시)."""
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                "-of", "csv=p=0", p], capture_output=True, text=True).stdout)
    o = subprocess.run(["ffmpeg", "-i", p, "-af", "silencedetect=noise=-35dB:d=0.25", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    st = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", o)]
    en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", o)]
    return st[-1] if st and (len(en) < len(st) or abs(en[-1] - dur) < 0.05) else dur


def duck_bgm(bgm, spans, out):
    """spans=[(시작,끝)] 동안 BGM을 DUCK_DB만큼 부드럽게 내린 wav를 만든다."""
    with wave.open(bgm) as w:
        sr, ch, sw = w.getframerate(), w.getnchannels(), w.getsampwidth()
        a = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32)
    a = a.reshape(-1, ch)
    t = np.arange(len(a)) / sr
    floor = 10 ** (DUCK_DB / 20)
    depth = np.zeros(len(a), np.float32)          # 0=원래, 1=최대로 내림
    for s0, s1 in spans:
        up = np.clip((t - (s0 - ATTACK)) / ATTACK, 0, 1)      # 말 직전 서서히 내려감
        down = np.clip(((s1 + RELEASE) - t) / RELEASE, 0, 1)  # 말 끝나고 서서히 복귀
        depth = np.maximum(depth, np.minimum(up, down))
    depth = 0.5 - 0.5 * np.cos(np.pi * depth)                 # 모서리를 둥글게
    gain = 1 - depth * (1 - floor)
    a = np.clip(a * gain[:, None], -32768, 32767).astype("<i2")
    with wave.open(out, "wb") as w:
        w.setnchannels(ch); w.setsampwidth(sw); w.setframerate(sr); w.writeframes(a.tobytes())


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("ffmpeg 실패:\n" + r.stderr[-2000:])
    return r.stderr


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
    if len(args) != 5:
        sys.exit(__doc__)
    video, delays_p, voice_dir, bgm, out = args
    reverb = opts.get("reverb", "church")
    delays = json.loads(Path(delays_p).read_text())
    keys = sorted(delays, key=lambda k: delays[k])
    spans = [(delays[k] / 1000, delays[k] / 1000 + speech_len(str(Path(voice_dir) / f"{k}.mp3")))
             for k in keys]
    ducked = str(Path(out).with_suffix("")) + "_bgm_ducked.wav"
    duck_bgm(bgm, spans, ducked)
    bgm = ducked

    ins = ["-i", video]
    for k in keys:
        ins += ["-i", str(Path(voice_dir) / f"{k}.mp3")]
    ins += ["-i", bgm]
    n = len(keys)
    bgm_idx = n + 1

    f = []
    # ① 나레이션 버스: 배치 → 합치기 → 다듬기
    for i, k in enumerate(keys, 1):
        f.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo,"
                 f"adelay={delays[k]}|{delays[k]}[v{i}]")
    f.append("".join(f"[v{i}]" for i in range(1, n + 1)) +
             f"amix=inputs={n}:duration=longest:normalize=0,"
             "highpass=f=75,"                                   # 저역 웅웅거림 제거
             "equalizer=f=3200:t=q:w=1.1:g=2.5,"                # 발음 또렷하게
             "acompressor=threshold=-22dB:ratio=3:attack=6:release=160:makeup=3,"
             + ("aecho=0.85:0.5:38|71:0.12|0.07," if reverb == "church" else "") +
             "anull[vo]")
    # ② BGM: 쉬는 구간은 크게, 목소리 밑에서는 자동으로 내려감
    f.append(f"[{bgm_idx}:a]aresample=48000,aformat=channel_layouts=stereo,volume=0.62[b]")   # 쉬는 구간 기준 크기 (더킹은 위에서 이미 적용)
    # ③ 합치기
    f.append("[vo][b]amix=inputs=2:duration=longest:normalize=0[mix]")
    graph = ";".join(f)

    # 1패스: 음량 측정
    meas = run(["ffmpeg", "-y", *ins, "-filter_complex",
                graph + f";[mix]loudnorm=I={TARGET_I}:TP={TARGET_TP - TP_HEADROOM}:LRA={TARGET_LRA}:print_format=json[o]",
                "-map", "[o]", "-f", "null", "-"])
    js = json.loads(meas[meas.rindex("{"):meas.rindex("}") + 1])
    # 2패스: 측정값으로 정확히 맞춤 (linear=true → 음악적 다이내믹 보존)
    ln = (f"loudnorm=I={TARGET_I}:TP={TARGET_TP - TP_HEADROOM}:LRA={TARGET_LRA}"
          f":measured_I={js['input_i']}:measured_TP={js['input_tp']}"
          f":measured_LRA={js['input_lra']}:measured_thresh={js['input_thresh']}"
          f":offset={js['target_offset']}:linear=true")
    run(["ffmpeg", "-y", *ins, "-filter_complex", graph + f";[mix]{ln},aresample=48000[o]",
         "-map", "0:v", "-map", "[o]", "-c:v", "libx264", "-crf", "20", "-preset", "medium",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", out])

    # 검증: 최종 파일의 실제 음량
    chk = run(["ffmpeg", "-i", out, "-af", "ebur128=peak=true", "-f", "null", "-"])
    I = re.findall(r"I:\s+(-?[\d.]+) LUFS", chk)[-1]
    TP = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", chk)[-1]
    print(f"완료: {out}")
    print(f"  통합 음량 {I} LUFS (목표 {TARGET_I}) / 최대 {TP} dBTP (목표 ≤ {TARGET_TP})")


if __name__ == "__main__":
    main()
