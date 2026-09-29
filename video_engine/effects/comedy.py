"""부아콤 개그 효과: orom_sil(한 팔 번쩍), assa_gaori(가오리 헤엄), brake_scratch(BGM 뚝)."""
from __future__ import annotations

from pathlib import Path

from ..graphics import shapes
from ..util import fnum, norm_path
from .registry import effect


def _orom_timing(plan, p):
    plan.add_warp("slow", float(p["at"]), float(p["dur"]), float(p["factor"]))


@effect("orom_sil", defaults={"at": 0.4, "dur": 0.5, "factor": 2.5, "flash": 0.8, "rays": True,
                              "center": [0.5, 0.38], "ray_color": "#FFE38A", "push": 0.12, "sfx": "jingle"},
        primary="at", timing=_orom_timing)
def orom_sil(plan, p):
    """한 팔 번쩍! 순간: 슬로모션(factor배) + 번쩍 플래시 + 방사형 빛 + 징글."""
    at, span = float(p["at"]), float(p["dur"]) * float(p["factor"])
    end = min(plan.duration, at + span + 0.5)
    if float(p.get("flash") or 0) > 0:
        plan.post.append(f"eq=brightness='{fnum(p['flash'])}*exp(-(t-{fnum(at)})*11)':eval=frame:"
                         f"enable='{plan.enable(at, at + 0.6)}'")
    if float(p.get("push") or 0) > 0:
        pz = float(p["push"])
        plan.add_zoom(f"(1+{fnum(pz)}*clip((t-{fnum(at)})/{fnum(span)},0,1))", 1 + pz)
    if p.get("rays"):
        W, H = plan.canvas
        size = int(max(W, H) * 1.25)
        cache = plan.assets.parent / "_shared"
        path = cache / f"rays_{size}_{p['ray_color'].lstrip('#')}.png"
        if not path.exists():
            cache.mkdir(parents=True, exist_ok=True)
            shapes.radial_rays(size, color=p["ray_color"]).save(path)
        cx, cy = p["center"]
        filt = ["rotate=a='t*0.9':c=none",
                f"fade=t=in:st={fnum(at)}:d=0.12:alpha=1",
                f"fade=t=out:st={fnum(max(at, end - 0.3))}:d=0.3:alpha=1"]
        plan.add_layer(path, f"W*{fnum(cx)}-w/2", f"H*{fnum(cy)}-h/2", at, end, filters=filt, z=35, name="rays")
    if p.get("sfx"):
        plan.add_sfx(p["sfx"], at)


@effect("assa_gaori", defaults={"at": 0.2, "dur": 1.6, "sprite": None, "width": 0.34, "y": 0.34,
                                "wave": 36, "sfx": "pop"}, primary="at")
def assa_gaori(plan, p):
    """"뽁" + 가오리 실루엣 스티커가 화면을 오른쪽→왼쪽으로 휙 헤엄쳐 지나간다.
    sprite에 PNG 경로를 주면 그 그림을, 없으면 코드로 그린 임시 실루엣을 쓴다."""
    at, dur = float(p["at"]), float(p["dur"])
    W, H = plan.canvas
    width = int(W * float(p["width"]))
    sprite = p.get("sprite") or (plan.settings.get("assets") or {}).get("manta")
    path: Path | None = None
    if sprite:
        cand = norm_path(sprite, Path(plan.settings.get("_config_dir") or "."))
        if cand.exists():
            path = cand
        else:
            plan.notes.append(f"assa_gaori: 스티커 파일이 없어 임시 실루엣 사용 ({cand})")
    if path is None:
        cache = plan.assets.parent / "_shared"
        path = cache / f"manta_{width}.png"
        if not path.exists():
            cache.mkdir(parents=True, exist_ok=True)
            shapes.manta(width, unit=plan.unit).save(path)
    prog = f"clip((t-{fnum(at)})/{fnum(dur)},0,1)"
    x = f"W-(W+w)*{prog}"
    y = f"H*{fnum(p['y'])}-h/2+{plan.px(float(p['wave']))}*sin((t-{fnum(at)})*7)"
    filt = ["rotate=a='0.10*sin(t*11)':c=none:ow=rotw(0.12):oh=roth(0.12)"]
    plan.add_layer(path, x, y, at, at + dur, filters=filt, z=65, name="manta")
    if p.get("sfx"):
        plan.add_sfx(p["sfx"], at)


@effect("brake_scratch", defaults={"at": 0.0, "brake": 0.35, "sfx": "scratch", "jolt": True}, primary="at")
def brake_scratch(plan, p):
    """레코드 스크래치 + BGM이 턴테이블 멈추듯 느려지다 뚝 끊긴다 (다음 bgm_cue까지 무음)."""
    at = float(p["at"])
    plan.bgm_events.append({"kind": "brake", "at": at, "brake": float(p["brake"])})
    if p.get("sfx"):
        plan.add_sfx(p["sfx"], at)
    if p.get("jolt"):
        a = fnum(10 * plan.scene[1] / 1080)
        env = f"between(t,{fnum(at)},{fnum(at + 0.15)})"
        plan.add_zoom(f"(1+0.04*{env})", 1.04)
        plan.add_pan(f"{a}*sin(2*PI*t*31)*{env}", "0")
