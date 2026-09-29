"""컷 전환 플러그인. 매니페스트의 transition은 "이전 컷 → 이 컷"으로 들어오는 방식이다.

    @transition("이름", defaults={...}, timing=길이조정함수)
    def 이름(prev, cur, p): ...     # prev는 첫 컷이면 None

- cut      : 그냥 붙이기
- fade     : 크로스페이드 (앞 컷과 겹침 → 전체 길이가 줄어듦)
- dip      : 검정으로 페이드아웃 → 페이드인
- door_wipe: 전동차 출입문이 양쪽에서 닫히며 "딩동" → 역 표시 카드(●새벽 4시역 → ●오후 2시역) → 문 열림
"""
from __future__ import annotations

from .config import resolve_font
from .effects.registry import transition
from .graphics import shapes
from .util import fnum


@transition("cut")
def cut(prev, cur, p):
    """그냥 붙이기."""


def _fade_timing(prev, cur, p):
    if prev is None:
        return
    cur.overlap_in = float(p["duration"])


@transition("fade", defaults={"duration": 0.5, "kind": "fade"}, timing=_fade_timing)
def fade(prev, cur, p):
    """크로스페이드 (xfade). kind는 ffmpeg xfade 종류: fade, dissolve, fadeblack, smoothleft ..."""
    if prev is None:
        cur.post.append(f"fade=t=in:st=0:d={fnum(p['duration'])}")
        return
    cur.xfade_in = {"transition": p.get("kind", "fade"), "duration": cur.overlap_in}


@transition("dip", defaults={"duration": 0.6, "color": "black"})
def dip(prev, cur, p):
    """앞 컷은 어둡게 사라지고 이 컷이 밝아진다 (겹침 없음)."""
    half = float(p["duration"]) / 2
    if prev is not None:
        prev.post.append(f"fade=t=out:st={fnum(prev.duration - half)}:d={fnum(half)}:color={p['color']}")
    cur.post.append(f"fade=t=in:st=0:d={fnum(half)}:color={p['color']}")


def _door_timing(prev, cur, p):
    close, hold, opn = float(p["close"]), float(p["hold"]), float(p["open"])
    if prev is not None:
        prev.tail += close + hold / 2
        cur.lead += hold / 2 + opn
    else:
        cur.lead += hold + opn


def _smooth(u: str) -> str:
    return f"({u})*({u})*(3-2*({u}))"


@transition("door_wipe", defaults={"close": 0.35, "hold": 0.7, "open": 0.35, "to": None, "from": None,
                                   "header": "이번 역은", "line_color": "#00A84D", "sfx": "dingdong",
                                   "card": True}, timing=_door_timing)
def door_wipe(prev, cur, p):
    """전동차 출입문 와이프 + 딩동 + 지하철 노선도식 역 표시 카드."""
    W, H = cur.canvas
    close, hold, opn = float(p["close"]), float(p["hold"]), float(p["open"])
    cache = cur.assets.parent / "_shared"
    cache.mkdir(parents=True, exist_ok=True)
    pw = W // 2 + 2
    left = cache / f"door_L_{W}x{H}.png"
    right = cache / f"door_R_{W}x{H}.png"
    if not left.exists():
        shapes.door_panel(pw, H, unit=cur.unit, side="left").save(left)
        shapes.door_panel(pw, H, unit=cur.unit, side="right").save(right)
    card = None
    if p.get("card", True) and p.get("to"):
        img = shapes.station_card(str(p["to"]), p.get("from"), font=resolve_font(cur.settings, "main"),
                                  unit=cur.unit * (0.8 if cur.vertical else 1.0), line_color=p["line_color"],
                                  header=p["header"])
        card = cur.asset("station_card.png")
        img.save(card)

    if prev is not None:
        c0 = prev.duration - hold / 2 - close
        u = _smooth(f"clip((t-{fnum(c0)})/{fnum(close)},0,1)")
        prev.add_layer(left, f"-w+w*{u}", "0", c0, prev.duration, z=90, name="doorL")
        prev.add_layer(right, f"W-w*{u}", "0", c0, prev.duration, z=90, name="doorR")
        if card:
            s = prev.duration - hold / 2
            prev.add_layer(card, "(W-w)/2", "(H-h)/2", s - 0.05, prev.duration,
                           filters=[f"fade=t=in:st={fnum(s - 0.05)}:d=0.12:alpha=1"], z=95, name="card")
        if p.get("sfx"):
            prev.add_sfx(p["sfx"], max(0.0, c0 - 0.25))
        closed = hold / 2
    else:
        closed = hold
        if p.get("sfx"):
            cur.add_sfx(p["sfx"], 0.0)
    u = _smooth(f"clip((t-{fnum(closed)})/{fnum(opn)},0,1)")
    cur.add_layer(left, f"-w*{u}", "0", 0.0, closed + opn, z=90, name="doorL")
    cur.add_layer(right, f"W-w+w*{u}", "0", 0.0, closed + opn, z=90, name="doorR")
    if card:
        cur.add_layer(card, "(W-w)/2", "(H-h)/2", 0.0, closed + 0.1,
                      filters=[f"fade=t=out:st={fnum(max(0.0, closed - 0.05))}:d=0.15:alpha=1"], z=95, name="card")
