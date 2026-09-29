"""카메라 효과: 켄번즈(정지 이미지 자동 줌), punch_zoom(얼굴 급줌 + 흔들림)."""
from __future__ import annotations

from ..util import fnum
from .registry import effect


def _u(plan, ease: str) -> str:
    """0→1 진행도 식 (카메라 시간 기준)."""
    T = plan.content_time_expr("t")
    D = fnum(max(plan.duration - plan.extra, 0.1))
    u = f"clip(({T})/{D},0,1)"
    if ease == "smooth":
        return f"({u}*{u}*(3-2*{u}))"
    if ease == "out":
        return f"sin({u}*PI/2)"
    return u


@effect("kenburns", defaults={"zoom": 0.08, "direction": "auto", "ease": "linear", "pan": 0.0,
                              "reframe_every": 0.0, "reframe_zoom": 0.1})
def kenburns(plan, p):
    """정지 이미지를 천천히 줌인/줌아웃. direction: auto(컷마다 번갈아)|in|out.
    reframe_every>0 이면 그 초마다 화각을 한 번씩 바꿔(점프컷) 긴 정지 컷이 멈춰 보이지 않게 한다."""
    z = float(p["zoom"])
    d = p["direction"]
    if d == "auto":
        d = "in" if plan.cut.index % 2 == 0 else "out"
    u = _u(plan, p["ease"])
    if z > 0:
        expr = f"(1+{fnum(z)}*{u})" if d == "in" else f"(1+{fnum(z)}*(1-{u}))"
        plan.add_zoom(expr, 1 + z)
    pan = float(p.get("pan") or 0)
    if pan:
        plan.add_pan(f"{fnum(pan * plan.scene[0])}*({u}-0.5)", "0")
    every = float(p.get("reframe_every") or 0)
    if every > 0 and plan.duration > every + 0.5:
        rz = float(p["reframe_zoom"])
        T = plan.content_time_expr("t")
        plan.add_zoom(f"(1+{fnum(rz)}*mod(floor(({T})/{fnum(every)}),2))", 1 + rz)


@effect("punch_zoom", defaults={"at": 0.0, "scale": 1.3, "ramp": 0.08, "hold": None, "shake": 0.3,
                                "shake_px": 18, "focus": None, "sfx": "punch"}, primary="at")
def punch_zoom(plan, p):
    """얼굴 쪽으로 scale배 급줌(ramp초) + shake초 동안 화면 흔들림."""
    at, s, ramp = float(p["at"]), float(p["scale"]), max(0.01, float(p["ramp"]))
    expr = f"(1+{fnum(s - 1)}*clip((t-{fnum(at)})/{fnum(ramp)},0,1)"
    if p.get("hold") is not None:
        off = at + ramp + float(p["hold"])
        expr += f"*(1-clip((t-{fnum(off)})/{fnum(ramp)},0,1))"
    plan.add_zoom(expr + ")", s)
    if p.get("focus"):
        plan.focus = (float(p["focus"][0]), float(p["focus"][1]))
    dur = float(p.get("shake") or 0)
    if dur > 0:
        a = fnum(float(p["shake_px"]) * plan.scene[1] / 1080)
        env = f"between(t,{fnum(at)},{fnum(at + dur)})*(1-(t-{fnum(at)})/{fnum(dur)})"
        plan.add_pan(f"{a}*sin(2*PI*t*23)*{env}", f"{a}*cos(2*PI*t*17)*{env}")
    if p.get("sfx"):
        plan.add_sfx(p["sfx"], at)
