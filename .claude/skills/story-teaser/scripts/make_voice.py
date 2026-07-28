#!/usr/bin/env python3
"""spec.json의 자막을 한국어 나레이션 음성으로 일괄 생성 (사용자 PC에서 실행).

이 환경에서는 이그레스 정책으로 edge-tts가 막혀 있다. 카스의 윈도우 PC에서 실행하는 용도.

준비:
    pip install edge-tts

사용법:
    python make_voice.py spec.json              # voice/ 폴더에 문장별 mp3
    python make_voice.py spec.json --voice ko-KR-SunHiNeural
    python make_voice.py spec.json --list       # 한국어 목소리 목록만 보기

목소리 고르기:
    ko-KR-InJoonNeural   남성, 차분하고 낮음  ← 사연/야담 기본 추천
    ko-KR-HyunsuNeural   남성, 젊고 또렷함
    ko-KR-SunHiNeural    여성, 부드럽고 따뜻함
    (--list 로 현재 실제 제공 목록을 확인할 것)
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

try:
    import edge_tts
except ImportError:
    sys.exit("edge-tts가 없습니다. 먼저 실행하세요:  pip install edge-tts")


def lines_from_spec(spec):
    """자막 + 엔드카드를 읽는 순서대로 문장 리스트로."""
    out = []
    for i, c in enumerate(spec.get("captions", []), 1):
        text = " ".join(x for x in (c.get("line1", ""), c.get("line2", "")) if x).strip()
        if text:
            out.append((f"{i:02d}", text))
    end = spec.get("endcard") or {}
    text = " ".join(x for x in (end.get("line1", ""), end.get("line2", "")) if x).strip()
    if text:
        out.append((f"{len(out)+1:02d}_end", text))
    return out


async def list_voices():
    voices = await edge_tts.list_voices()
    ko = [v for v in voices if v["Locale"].startswith("ko")]
    if not ko:
        print("한국어 목소리를 찾지 못했습니다. 네트워크를 확인하세요.")
        return
    print(f"한국어 목소리 {len(ko)}개:")
    for v in ko:
        print(f"  {v['ShortName']:32s} {v.get('Gender','')}")


async def synth(lines, voice, rate, outdir):
    outdir.mkdir(parents=True, exist_ok=True)
    for tag, text in lines:
        path = outdir / f"{tag}.mp3"
        await edge_tts.Communicate(text, voice, rate=rate).save(str(path))
        print(f"  ✓ {path.name}  ({text})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec", nargs="?", help="spec.json 경로")
    ap.add_argument("--voice", default="ko-KR-InJoonNeural")
    ap.add_argument("--rate", default="-8%", help="말 속도. 사연은 느린 쪽이 어울림")
    ap.add_argument("--out", default="voice", help="출력 폴더 (기본 voice/)")
    ap.add_argument("--list", action="store_true", help="한국어 목소리 목록만 출력")
    a = ap.parse_args()

    if a.list:
        asyncio.run(list_voices())
        return
    if not a.spec:
        ap.error("spec.json 경로가 필요합니다 (또는 --list)")

    spec = json.loads(Path(a.spec).read_text(encoding="utf-8"))
    lines = lines_from_spec(spec)
    if not lines:
        sys.exit("spec.json에서 자막을 찾지 못했습니다.")

    print(f"목소리 {a.voice} / 속도 {a.rate} / 문장 {len(lines)}개\n")
    asyncio.run(synth(lines, a.voice, a.rate, Path(a.out)))
    print(f"\n완료! '{a.out}' 폴더의 mp3 파일들을 Claude에게 보내세요.")


if __name__ == "__main__":
    main()
