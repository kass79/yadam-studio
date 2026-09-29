"""매니페스트 + 설정 → 컷별 렌더 계획(CutPlan) 목록과 전체 타임라인.

순서:
  1) 소스 길이 조사(ffprobe) → 컷 내용 길이(body), lead/tail 기본값
  2) 전환 timing → 효과 timing(정지/슬로모션으로 늘어나는 길이)
  3) 길이를 프레임 단위로 맞추고 시작 시각 계산 (크로스페이드는 겹침만큼 당김)
  4) 자막 페이지 → 효과 apply → 전환 apply → 매니페스트 sfx
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from . import effects as fx
from .manifest import Cut, Manifest
from .plan import CutPlan
from .render import ffmpeg
from .subtitles import build_pages
from .util import deep_merge, safe_name


@dataclass
class Timeline:
    plans: list[CutPlan]
    total: float
    fps: int
    canvas: tuple[int, int]
    vertical: bool
    warnings: list[str] = field(default_factory=list)
    bgm_start: dict | None = None     # 쇼츠: 구간 시작 시점에 이미 흐르던 BGM


def _q(t: float, fps: int) -> float:
    return round(t * fps) / fps


def _effect_list(cut: Cut, settings: dict) -> list[tuple[str, object]]:
    auto = settings.get("auto_effects") or {}
    names: list[tuple[str, object]] = []
    for key in ("all", cut.type) + (("still",) if cut.is_still else ("video",)):
        for n in auto.get(key) or []:
            names.append((n, {}) if isinstance(n, str) else next(iter(n.items())))
    explicit = {n for n, _ in cut.effects}
    names = [(n, v) for n, v in names if n not in explicit]
    skip = set(cut.raw.get("no_auto") or [])
    return [(n, v) for n, v in names if n not in skip] + list(cut.effects)


def build_timeline(m: Manifest, settings: dict, *, cuts: list[Cut] | None = None, canvas: tuple[int, int] | None = None,
                   vertical: bool = False, work_dir: Path, head_pad: float = 0.0) -> Timeline:
    fps = m.fps
    canvas = canvas or m.size
    W, H = canvas
    scene = canvas if not vertical else (int(round(H * 16 / 9 / 2)) * 2, H)
    tim = settings.get("timing") or {}
    cam = settings.get("camera") or {}
    cuts = cuts if cuts is not None else m.cuts
    warnings: list[str] = []
    plans: list[CutPlan] = []

    for cut in cuts:
        p = CutPlan(cut=cut, settings=settings, canvas=canvas, scene=scene, fps=fps, vertical=vertical,
                    assets=work_dir / "assets" / f"{cut.index:03d}_{safe_name(cut.id)}")
        p.focus = tuple(cut.focus or cam.get("focus") or (0.5, 0.42))  # type: ignore[assignment]
        # 소스 길이
        if cut.media is not None and not cut.is_still and cut.media.exists():
            info = ffmpeg.probe(cut.media)
            p.media_dur = info.duration
            if cut.audio is None and info.has_audio:
                p.audio_src = cut.media
        if cut.audio is not None and cut.audio.exists():
            p.audio_src = cut.audio
        if p.audio_src is not None:
            p.audio_dur = ffmpeg.probe(p.audio_src).duration
        # 내용 길이
        has_audio = p.audio_dur > 0
        if cut.is_still:
            p.lead = float(cut.raw.get("lead", tim.get("lead", 0.12) if has_audio else 0.0))
            p.tail = float(cut.raw.get("tail", tim.get("tail", 0.25) if has_audio else 0.0))
            p.body = p.audio_dur if has_audio else float(tim.get("insert_duration", 2.2))
        else:
            p.lead = float(cut.raw.get("lead", 0.0))   # 립싱크 영상은 음성과 0초에 맞물려 있음
            p.tail = float(cut.raw.get("tail", tim.get("tail", 0.25) if has_audio else 0.0))
            p.body = max(p.media_dur or 0.0, p.audio_dur)
        if cut.duration is not None:
            p.body = max(0.1, cut.duration - p.lead - p.tail)
        mn = float(tim.get("min_cut", 1.2))
        if p.lead + p.body + p.tail < mn:
            p.tail += mn - (p.lead + p.body + p.tail)
        # 효과 목록 확정 (프리셋에서 꺼진 효과는 건너뜀)
        for name, given in _effect_list(cut, settings):
            eff = fx.get(name)
            if not fx.is_enabled(settings, name):
                p.notes.append(f"효과 '{name}'는 이 프리셋에서 꺼져 있어 건너뜀")
                continue
            p.effects.append((name, eff.resolve(settings, given)))
        plans.append(p)

    # 전환 결정
    trans: list[tuple[str, dict] | None] = []
    last_station = None
    for i, p in enumerate(plans):
        t = p.cut.transition
        if t is None and i > 0:
            t = settings.get("transition_default") or {"type": "cut"}
        if t is None or (i == 0 and t.get("type") in ("fade",)):
            trans.append(None if t is None else (t["type"], deep_merge(fx.TRANSITIONS[t["type"]].defaults, t)))
            continue
        if t.get("type") not in fx.TRANSITIONS:
            raise KeyError(f"컷 {p.cut.id}: 모르는 전환 '{t.get('type')}'. 사용 가능: {', '.join(fx.TRANSITIONS)}")
        name = t["type"]
        tp = deep_merge(fx.TRANSITIONS[name].defaults, (settings.get("transitions") or {}).get(name) or {})
        tp = deep_merge(tp, {k: v for k, v in t.items() if k != "type"})
        if name == "door_wipe":
            if tp.get("from") is None and last_station and last_station != tp.get("to"):
                tp["from"] = last_station
            last_station = tp.get("to") or last_station
        trans.append((name, tp))

    # timing 단계
    if plans and head_pad:
        plans[0].lead += head_pad
    for i, p in enumerate(plans):
        if trans[i] and fx.TRANSITIONS[trans[i][0]].timing:
            fx.TRANSITIONS[trans[i][0]].timing(plans[i - 1] if i > 0 else None, p, trans[i][1])
    for p in plans:
        p.duration = p.lead + p.body + p.tail       # 효과 timing이 참고할 임시 값
        for name, params in p.effects:
            eff = fx.get(name)
            if eff.timing:
                eff.timing(p, params)

    # 길이 확정 + 시작 시각
    t = 0.0
    for i, p in enumerate(plans):
        p.duration = _q(p.lead + p.body + p.tail + p.extra, fps)
        p.overlap_in = _q(min(p.overlap_in, p.duration * 0.45, plans[i - 1].duration * 0.45), fps) if i else 0.0
        if p.overlap_in <= 0:
            p.overlap_in = 0.0
        t -= p.overlap_in
        p.start = round(t, 6)
        t += p.duration
    total = _q(t, fps)

    # apply 단계
    for p in plans:
        build_pages(p)
        for name, params in p.effects:
            fx.get(name).apply(p, params)
    for i, p in enumerate(plans):
        if trans[i]:
            fx.TRANSITIONS[trans[i][0]].apply(plans[i - 1] if i > 0 else None, p, trans[i][1])
    for p in plans:
        for s in p.cut.sfx:
            p.add_sfx(s["name"], s["at"], s.get("gain_db", 0.0))

    # 점검
    max_hold = float(tim.get("max_still_hold", 3.0))
    for p in plans:
        if p.is_still and not p.zoom_terms and p.duration > max_hold:
            warnings.append(f"컷 {p.cut.id}: 정지 이미지가 {p.duration:.1f}초 동안 움직임 없음 (켄번즈 꺼짐?)")
        for n in p.notes:
            warnings.append(f"컷 {p.cut.id}: {n}")
    return Timeline(plans=plans, total=total, fps=fps, canvas=canvas, vertical=vertical, warnings=warnings)


def summary(tl: Timeline, settings: dict) -> str:
    rows = [f"{'컷':>5} {'종류':<6} {'시작':>7} {'길이':>5}  효과"]
    for p in tl.plans:
        names = ", ".join(n for n, _ in p.effects) or "-"
        tr = p.cut.transition["type"] if p.cut.transition else ""
        rows.append(f"{p.cut.id:>5} {p.cut.type:<6} {p.start:7.2f} {p.duration:5.2f}  {names}"
                    + (f"  [전환:{tr}]" if tr else ""))
    n = len(tl.plans)
    avg = sum(p.duration for p in tl.plans) / max(1, n)
    rows.append(f"총 {n}컷, {tl.total:.2f}초, 평균 컷 길이 {avg:.2f}초")
    lo, hi = (settings.get("timing") or {}).get("target_avg_cut", [0, 999])
    if not (lo <= avg <= hi):
        rows.append(f"  ⚠ 평균 컷 길이가 프리셋 목표({lo}~{hi}초)를 벗어남")
    return "\n".join(rows)
