"""컷 하나의 렌더 계획(CutPlan).

효과 플러그인은 ffmpeg를 직접 부르지 않고 이 계획서에 "무엇을 할지"만 적는다:
  - 카메라(줌/이동/흔들림) 식      → add_zoom / add_pan
  - 시간 왜곡(정지/슬로모션)        → add_warp (컷 길이가 늘어남, timing 단계에서만)
  - 색/화면 필터                   → post
  - 오버레이 이미지 레이어          → add_layer
  - 대사 오디오 필터               → audio_filters
  - 효과음 / BGM 이벤트            → add_sfx / bgm_events
실제 ffmpeg 명령 조립은 render/segment.py 가 한다. 그래서 효과 단위 테스트는 ffmpeg 없이도 된다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .manifest import Cut
from .util import fnum


@dataclass
class Layer:
    src: Path                      # PNG 한 장 또는 시퀀스 패턴(frame_%03d.png)
    x: str                         # overlay x 식 (W,H=화면, w,h=레이어, t=컷 안 시간)
    y: str
    start: float
    end: float
    sequence: bool = False
    filters: list[str] = field(default_factory=list)   # 레이어에 먼저 거는 필터 (회전, 알파 페이드 등)
    z: int = 50                    # 쌓는 순서 (자막 60, 스티커 70, 전환 90)
    name: str = ""


@dataclass
class Warp:
    kind: str        # "freeze" | "slow"
    at: float        # 컷 안 출력 시각
    dur: float       # freeze: 멈춘 시간 / slow: 느리게 재생할 원본 구간 길이
    factor: float = 1.0   # slow 배율 (2.0 = 2배 느리게)

    @property
    def added(self) -> float:
        return self.dur if self.kind == "freeze" else self.dur * (self.factor - 1.0)


@dataclass
class SfxEvent:
    name: str
    at: float                # 컷 안 시각 (음수면 이전 컷 끝부분)
    gain_db: float = 0.0


@dataclass
class CutPlan:
    cut: Cut
    settings: dict
    canvas: tuple[int, int]          # 최종 화면 (본편 1920x1080 / 쇼츠 1080x1920)
    scene: tuple[int, int]           # 카메라가 찍는 16:9 장면 크기
    fps: int
    assets: Path                     # 이 컷 전용 임시 그림 폴더
    media_dur: float | None = None   # 영상 소스 길이
    audio_src: Path | None = None    # 대사 오디오 (wav 또는 lip mp4의 음성)
    audio_dur: float = 0.0
    lead: float = 0.0                # 컷 시작 → 대사/영상 내용 시작
    tail: float = 0.0
    body: float = 0.0                # 내용 길이 (대사/영상 길이, lead·tail·효과 연장 제외)
    duration: float = 0.0            # 최종 길이 (프레임 단위로 맞춤)
    start: float = 0.0               # 전체 타임라인에서 시작 시각
    overlap_in: float = 0.0          # 이전 컷과 겹치는 길이 (크로스페이드)
    xfade_in: dict | None = None     # {"transition": "fade", "duration": 0.5}
    zoom_terms: list[str] = field(default_factory=list)
    zoom_max: float = 1.0
    pan_terms: list[tuple[str, str]] = field(default_factory=list)   # (x식, y식) 장면 픽셀
    focus: tuple[float, float] = (0.5, 0.5)
    warps: list[Warp] = field(default_factory=list)
    post: list[str] = field(default_factory=list)
    layers: list[Layer] = field(default_factory=list)
    subtitle: dict | None = None     # {"pages":[(text,s,e)], "style": {...}, "kind": "normal|cloud", "notes": []}
    audio_filters: list[str] = field(default_factory=list)
    sfx: list[SfxEvent] = field(default_factory=list)
    bgm_events: list[dict] = field(default_factory=list)   # {"kind": "brake", "at": 1.2}
    effects: list[tuple[str, dict]] = field(default_factory=list)   # 적용된 효과 (이름, 확정 파라미터)
    notes: list[str] = field(default_factory=list)
    vertical: bool = False

    # ── 편의 속성 ──
    @property
    def W(self) -> int:
        return self.canvas[0]

    @property
    def H(self) -> int:
        return self.canvas[1]

    @property
    def unit(self) -> float:
        """1080p 기준 px 값을 현재 화면에 맞추는 배율."""
        return min(self.canvas) / 1080.0

    @property
    def is_still(self) -> bool:
        return self.cut.is_still

    @property
    def extra(self) -> float:
        return sum(w.added for w in self.warps)

    @property
    def speech_end(self) -> float:
        """대사가 끝나는 컷 안 시각 (시간 왜곡 반영)."""
        if not self.audio_dur:
            return self.duration - self.tail
        return self.lead + self.audio_dur

    # ── 효과가 쓰는 API ──
    def px(self, v: float) -> int:
        return max(1, int(round(v * self.unit)))

    def add_zoom(self, expr: str, max_value: float) -> None:
        """줌 배율 식(≥1)을 곱해 넣는다. 카메라 시간은 {T}, 실제 시간은 t."""
        self.zoom_terms.append(expr)
        self.zoom_max *= max(1.0, float(max_value))

    def add_pan(self, x_expr: str, y_expr: str = "0") -> None:
        """장면 픽셀 단위 이동(흔들림 등). 여유 공간 밖으로는 자동으로 잘린다."""
        self.pan_terms.append((x_expr, y_expr))

    def add_warp(self, kind: str, at: float, dur: float, factor: float = 1.0) -> Warp:
        w = Warp(kind, float(at), float(dur), float(factor))
        self.warps.append(w)
        self.warps.sort(key=lambda x: x.at)
        return w

    def add_layer(self, src: Path, x: str, y: str, start: float = 0.0, end: float | None = None, **kw) -> Layer:
        lay = Layer(Path(src), x, y, float(start), float(self.duration if end is None else end), **kw)
        self.layers.append(lay)
        return lay

    def add_sfx(self, name: str, at: float, gain_db: float = 0.0) -> None:
        self.sfx.append(SfxEvent(name, float(at), float(gain_db)))

    def asset(self, name: str) -> Path:
        self.assets.mkdir(parents=True, exist_ok=True)
        return self.assets / name

    def enable(self, start: float, end: float) -> str:
        return f"between(t,{fnum(start)},{fnum(end)})"

    # ── 시간 왜곡 ──
    def content_time_expr(self, var: str = "t") -> str:
        """출력 시각 → 내용 시각(정지 중엔 멈추고 슬로모션 중엔 느리게). 켄번즈가 쓴다."""
        expr = var
        for w in sorted(self.warps, key=lambda x: -x.at):
            a, d = fnum(w.at), fnum(w.dur)
            if w.kind == "freeze":
                expr = f"({expr}-clip({var}-{a},0,{d}))"
            else:
                k = fnum(w.factor)
                span = fnum(w.dur * w.factor)
                expr = f"({expr}-clip({var}-{a},0,{span})*(1-1/{k}))"
        return expr

    def source_remap_expr(self) -> str | None:
        """영상 소스용 setpts 식: 원본 시각 S → 출력 시각. 정지/슬로모션 구간을 만든다."""
        if not self.warps:
            return None
        # (원본 시작, 출력 시작, 기울기) 조각들
        pieces: list[tuple[float, float, float]] = []
        s = o = 0.0
        offset = self.lead   # tpad로 앞에 붙는 부분은 제외하고 계산
        for w in sorted(self.warps, key=lambda x: x.at):
            at = max(0.0, w.at - offset)
            s_w = s + (at - o)
            pieces.append((s, o, 1.0))
            if w.kind == "freeze":
                s, o = s_w, at + w.dur
            else:
                pieces.append((s_w, at, w.factor))
                s, o = s_w + w.dur, at + w.dur * w.factor
        pieces.append((s, o, 1.0))
        S = "((PTS-STARTPTS)*TB)"
        s_last, o_last, k_last = pieces[-1]
        expr = f"({fnum(o_last)}+({S}-{fnum(s_last)})*{fnum(k_last)})"
        for i in range(len(pieces) - 2, -1, -1):
            s0, o0, k = pieces[i]
            nxt_s = pieces[i + 1][0]
            expr = f"if(lt({S},{fnum(nxt_s)}),({fnum(o0)}+({S}-{fnum(s0)})*{fnum(k)}),{expr})"
        return expr


def params_for(plan: CutPlan, name: str) -> dict[str, Any]:
    for n, p in plan.effects:
        if n == name:
            return p
    return {}
