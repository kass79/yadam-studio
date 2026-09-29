"""글자 효과: dialect_note(사투리 주석), freeze_sticker(정지 화면 + 굵은 스티커)."""
from __future__ import annotations

from ..config import resolve_font
from ..graphics import shapes
from ..util import fnum
from .registry import effect


@effect("dialect_note", defaults={"text": ""}, primary="text")
def dialect_note(plan, p):
    """사투리 대사 아래 작은 주석 자막. '뭇나 = 먹었나' → '(*뭇나 = 먹었나)'"""
    text = str(p["text"]).strip()
    if not text:
        return
    if not text.startswith("("):
        text = f"(*{text.lstrip('*')})"
    if plan.subtitle is None:
        plan.notes.append("dialect_note: 자막이 없는 컷이라 주석을 단독 자막으로 표시")
        plan.subtitle = {"pages": [("", 0.0, plan.duration)], "kind": "normal", "notes": [], "style": {}}
    plan.subtitle["notes"].append(text)


def _freeze_timing(plan, p):
    at = p.get("at", "end")
    if at in (None, "end"):
        at = plan.lead + plan.body
    p["_at"] = float(at)
    plan.add_warp("freeze", float(at), float(p["dur"]))


@effect("freeze_sticker", defaults={"text": "", "at": "end", "dur": 1.3, "pos": [0.3, 0.2], "size": 84,
                                    "fg": "#111111", "bg": "#FFE14D", "border": "#111111", "angle": -4,
                                    "desat": 0.55, "flash": 0.35, "sfx": "freeze"},
        primary="text", timing=_freeze_timing)
def freeze_sticker(plan, p):
    """화면을 멈추고 굵은 자막 스티커를 '쾅' 붙인다. ("배동철, 47세. 오해 중.")"""
    at = float(p.get("_at", plan.lead + plan.body))
    end = min(plan.duration, at + float(p["dur"]))
    en = plan.enable(at, end)
    if float(p.get("desat", 1)) != 1:
        plan.post.append(f"eq=saturation={fnum(p['desat'])}:enable='{en}'")
    if float(p.get("flash") or 0) > 0:
        plan.post.append(f"eq=brightness='{fnum(p['flash'])}*exp(-(t-{fnum(at)})*16)':eval=frame:enable='{en}'")
    if str(p.get("text", "")).strip():
        img = shapes.sticker(str(p["text"]), font=resolve_font(plan.settings, "heavy"), unit=plan.unit,
                             size=float(p["size"]) * (1.0 if not plan.vertical else 0.85),
                             fg=p["fg"], bg=p["bg"], border=p["border"], angle=float(p["angle"]))
        path = plan.asset(f"sticker_{plan.cut.index}.png")
        img.save(path)
        cx, cy = p["pos"]
        drop = plan.px(70)
        y = f"H*{fnum(cy)}-h/2-{drop}*max(0,1-(t-{fnum(at)})/0.12)"
        if plan.vertical:
            cx, cy = 0.5, min(float(cy), 0.22)
        m = plan.px(24)
        plan.add_layer(path, f"clip(W*{fnum(cx)}-w/2,{m},W-w-{m})", y, at, end,
                       filters=[f"fade=t=in:st={fnum(at)}:d=0.06:alpha=1"], z=70, name="sticker")
    if p.get("sfx"):
        plan.add_sfx(p["sfx"], at)
