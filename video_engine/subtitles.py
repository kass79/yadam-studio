"""자막: 화자별 스타일 결정 → PNG 레이어 생성, 그리고 SRT 파일 쓰기."""
from __future__ import annotations

from pathlib import Path

from .config import resolve_font
from .graphics import shapes
from .graphics.text import parse_markup, render_lines, strip_markup, wrap_spans
from .plan import CutPlan
from .util import deep_merge, fnum


def style_for(plan: CutPlan) -> dict:
    """기본 자막 스타일 ← (쇼츠면 shorts.subtitle) ← 화자 스타일 ← 컷의 subtitle_style."""
    s = plan.settings
    st = dict(s.get("subtitle") or {})
    if plan.vertical:
        st = deep_merge(st, (s.get("shorts") or {}).get("subtitle") or {})
    spk = (s.get("speakers") or {}).get(plan.cut.speaker or "", {}) or {}
    st = deep_merge(st, {k: v for k, v in spk.items() if k not in ("keywords", "vo", "wall")})
    if plan.cut.raw.get("subtitle_style"):
        st = deep_merge(st, plan.cut.raw["subtitle_style"])
    return st


def keywords_for(plan: CutPlan) -> dict[str, str]:
    spk = (plan.settings.get("speakers") or {}).get(plan.cut.speaker or "", {}) or {}
    kw = {w: "dialect" for w in (spk.get("keywords") or [])}
    kw.update({w: "em" for w in plan.cut.emphasis})
    return kw


def build_pages(plan: CutPlan) -> None:
    """plan.subtitle을 채운다 (페이지별 시작/끝). 효과 적용 전에 호출된다."""
    sub = plan.cut.subtitle
    if not sub or not (plan.settings.get("subtitle") or {}).get("enabled", True):
        plan.subtitle = None
        return
    pages = [str(x) for x in sub] if isinstance(sub, list) else [str(sub)]
    t0 = plan.lead if plan.audio_dur else min(0.1, plan.duration * 0.1)
    t_end = plan.duration
    speech_end = plan.lead + plan.audio_dur + plan.extra if plan.audio_dur else t_end
    lens = [max(1, len(strip_markup(p))) for p in pages]
    total = sum(lens)
    out = []
    t = t0
    span = max(0.3, speech_end - t0)
    for i, (p, n) in enumerate(zip(pages, lens)):
        e = t + span * n / total
        if i == len(pages) - 1:
            e = t_end
        out.append((p, round(t, 3), round(e, 3)))
        t = e
    plan.subtitle = {"pages": out, "kind": "normal", "notes": [], "style": {}}


def render_layers(plan: CutPlan) -> None:
    """plan.subtitle → PNG 레이어들 (효과 적용 후, 렌더 직전에 호출)."""
    if not plan.subtitle:
        return
    st = deep_merge(style_for(plan), plan.subtitle.get("style") or {})
    kind = plan.subtitle.get("kind", "normal")
    u = plan.unit
    font = resolve_font(plan.settings, st.get("font", "main"))
    size = int(st.get("size", 64) * u)
    colors = {"normal": st.get("color", "#FFFFFF"), "em": st.get("emphasis_color", "#FFE14D"),
              "dialect": st.get("dialect_color", "#FF9A3C")}
    kw = keywords_for(plan)
    note_font = resolve_font(plan.settings, st.get("note_font", "main"))
    notes = [(n, note_font, int(size * float(st.get("note_size", 0.5))), st.get("note_color", "#FFE9B0"))
             for n in plan.subtitle.get("notes", [])]
    fade = float(st.get("fade", 0.0))
    for i, (text, s0, s1) in enumerate(plan.subtitle["pages"]):
        lines = wrap_spans(parse_markup(text, kw), int(st.get("max_chars", 22)))
        img = render_lines(lines, font=font, size=size, colors=colors, stroke=st.get("stroke"),
                           stroke_width=int(st.get("stroke_width", 6) * u),
                           line_spacing=float(st.get("line_spacing", 1.18)), shadow=int(st.get("shadow", 0) * u),
                           box=st.get("box"), box_radius=int(18 * u), pad=int(st.get("box_pad", 0) * u),
                           extra_lines=notes)
        if kind == "cloud":
            img = shapes.cloud_bubble(img, fill=st.get("cloud_fill", "#FFFFFFEE"),
                                      border=st.get("cloud_border", "#4FB3FF"), unit=u,
                                      trail=st.get("trail", "left"))
        path = plan.asset(f"sub_{i}.png")
        img.save(path)
        pos = st.get("position", "bottom")
        margin = int(st.get("margin", 70) * u)
        x = "(W-w)/2"
        if pos == "top":
            y = f"{margin}"
        elif pos == "lower_third":
            y = f"H*{fnum(st.get('y', 0.70))}-h/2"
        elif pos == "center":
            y = "(H-h)/2"
        else:
            y = f"H-h-{margin}"
        if "x" in st:
            x = f"clip(W*{fnum(st['x'])}-w/2,{margin // 2},W-w-{margin // 2})"
        filters = []
        if fade > 0:
            filters.append(f"fade=t=in:st={fnum(s0)}:d={fnum(fade)}:alpha=1")
            filters.append(f"fade=t=out:st={fnum(max(s0, s1 - fade))}:d={fnum(fade)}:alpha=1")
        plan.add_layer(path, x, y, s0, s1, filters=filters, z=60, name=f"sub{i}")


def srt_entries(plan: CutPlan) -> list[tuple[float, float, str]]:
    if not plan.subtitle:
        return []
    out = []
    for text, s0, s1 in plan.subtitle["pages"]:
        body = strip_markup(text)
        if plan.subtitle.get("notes"):
            body += "\n" + " ".join(plan.subtitle["notes"])
        out.append((plan.start + s0, plan.start + s1, body))
    return out


def _ts(t: float) -> str:
    ms = int(round(max(0.0, t) * 1000))
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(entries: list[tuple[float, float, str]], path: Path) -> Path:
    lines = []
    n = 0
    for s0, s1, text in sorted(entries):
        if s1 - s0 < 0.05 or not text.strip():
            continue
        n += 1
        lines += [str(n), f"{_ts(s0)} --> {_ts(s1)}", text.strip(), ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8-sig")   # BOM: 윈도우 메모장/유튜브 모두 한글 안전
    return path
