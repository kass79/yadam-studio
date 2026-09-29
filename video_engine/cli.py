"""명령줄: python -m video_engine <명령> ...

  render   ep.yaml                  본편 mp4 + srt
  shorts   ep.yaml --cuts 8-27      쇼츠(9:16) mp4 + srt
  check    ep.yaml                  렌더 없이 타임라인/경고만 확인 (몇 초)
  snapshot ep.yaml [--cuts 3-5]     컷별 앞·중간·뒤 프레임 확인용 한 장 (초안 화질)
  effects                           사용 가능한 효과/전환 목록
  demo-assets [폴더]                가짜 테스트 소스(단색 그림, 사인파 음성, BGM) 만들기
  clean    ep.yaml                  작업 폴더(_work) 지우기
"""
from __future__ import annotations

import argparse
import sys
import traceback

from . import __version__


def _add_common(sp: argparse.ArgumentParser) -> None:
    sp.add_argument("manifest", help="에피소드 매니페스트 YAML")
    sp.add_argument("--config", help="config.yaml 경로 (없으면 매니페스트 옆/상위 폴더에서 자동 탐색)")
    sp.add_argument("--draft", action="store_true", help="절반 해상도·빠른 인코딩 초안")


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")   # 윈도우 콘솔 한글 깨짐 방지
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(prog="python -m video_engine", description="공용 편집 엔진 " + __version__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("render", help="본편 렌더")
    _add_common(sp)
    sp.add_argument("--out", help="출력 mp4 경로")

    sp = sub.add_parser("shorts", help="쇼츠 렌더 (9:16)")
    _add_common(sp)
    sp.add_argument("--cuts", required=True, help="컷 id 구간, 예: 8-27")
    sp.add_argument("--hook", help="상단 훅 자막 (없으면 매니페스트 shorts.hook_text)")
    sp.add_argument("--out", help="출력 mp4 경로")

    sp = sub.add_parser("check", help="타임라인 점검")
    _add_common(sp)

    sp = sub.add_parser("snapshot", help="컷별 프레임 확인용 이미지")
    _add_common(sp)
    sp.add_argument("--cuts", help="컷 id 구간 (없으면 전체)")
    sp.add_argument("--full", action="store_true", help="초안 대신 원래 해상도로")
    sp.add_argument("--out", help="출력 jpg 경로")

    sub.add_parser("effects", help="효과/전환 목록")
    sp = sub.add_parser("demo-assets", help="가짜 테스트 소스 만들기")
    sp.add_argument("folder", nargs="?", default=None)
    sp = sub.add_parser("clean", help="작업 폴더 삭제")
    sp.add_argument("manifest")

    a = ap.parse_args(argv)
    try:
        if a.cmd == "effects":
            from .effects import EFFECTS, TRANSITIONS
            print("[효과]")
            for n, e in sorted(EFFECTS.items()):
                first = e.doc.splitlines()[0] if e.doc else ""
                print(f"  {n:<15} {first}")
                if e.defaults:
                    print(f"  {'':<15}   기본값: {e.defaults}")
            print("[전환]")
            for n, e in TRANSITIONS.items():
                print(f"  {n:<15} {e.doc.splitlines()[0] if e.doc else ''}")
            return 0
        if a.cmd == "demo-assets":
            from .demo_assets import make_demo_assets
            path = make_demo_assets(a.folder)
            print(f"테스트 소스 생성: {path}")
            return 0
        from . import pipeline
        if a.cmd == "check":
            print(pipeline.check(a.manifest, config=a.config, draft=a.draft))
        elif a.cmd == "render":
            r = pipeline.render(a.manifest, config=a.config, out=a.out, draft=a.draft)
            print(r["video"])
            print(r["srt"])
        elif a.cmd == "shorts":
            r = pipeline.shorts(a.manifest, a.cuts, config=a.config, out=a.out, hook=a.hook, draft=a.draft)
            print(r["video"])
        elif a.cmd == "snapshot":
            print(pipeline.snapshot(a.manifest, cuts=a.cuts, config=a.config, draft=not a.full, out=a.out))
        elif a.cmd == "clean":
            print(f"삭제: {pipeline.clean(a.manifest)}")
        return 0
    except KeyboardInterrupt:
        return 130
    except Exception as e:  # noqa: BLE001 — 비개발자용: 짧은 한국어 메시지 우선
        print(f"\n✖ 오류: {e}", file=sys.stderr)
        if "--debug" in sys.argv or __import__("os").environ.get("VIDEO_ENGINE_VERBOSE"):
            traceback.print_exc()
        return 1
