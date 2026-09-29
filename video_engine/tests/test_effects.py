"""효과별 단위 테스트 (ffmpeg 없이: 계획서에 무엇이 적히는지 확인)."""
from __future__ import annotations

import re

import pytest

from video_engine import effects as fx
from video_engine.effects.registry import EFFECTS, TRANSITIONS, effect

EXPECTED = {"kenburns", "punch_zoom", "vo_cloud", "fantasy", "dialect_note", "freeze_sticker", "orom_sil",
            "assa_gaori", "wall_voice", "brake_scratch"}


def run(plan, name, given=None):
    eff = fx.get(name)
    p = eff.resolve(plan.settings, given)
    if eff.timing:
        eff.timing(plan, p)
        plan.duration += plan.extra
    eff.apply(plan, p)
    return p


def test_registry_has_all_effects_and_transitions():
    assert EXPECTED <= set(EFFECTS)
    assert {"cut", "fade", "dip", "door_wipe"} <= set(TRANSITIONS)


def test_plugin_registration_is_one_decorator(make_plan):
    @effect("_test_glitch", defaults={"amount": 3}, primary="amount")
    def _g(plan, p):
        plan.post.append(f"noise=alls={p['amount']}")
    try:
        plan = make_plan()
        run(plan, "_test_glitch", 7)
        assert plan.post == ["noise=alls=7"]
    finally:
        EFFECTS.pop("_test_glitch")


def test_params_merge_order(settings):
    eff = fx.get("punch_zoom")
    s = dict(settings, effects={"punch_zoom": {"scale": 1.5, "enabled": True}})
    p = eff.resolve(s, {"at": 0.7})
    assert p["scale"] == 1.5 and p["at"] == 0.7 and "enabled" not in p
    assert eff.resolve(s, 0.9)["at"] == 0.9            # primary 값 하나
    with pytest.raises(ValueError):
        fx.get("wall_voice").resolve(s, 3)             # primary 없는 효과에 값 하나


def test_kenburns_zoom_moves_and_reframes(make_plan):
    plan = make_plan("vo", duration=7.0)
    run(plan, "kenburns")
    assert plan.zoom_terms and plan.zoom_max > 1.0
    # buakom: 3초마다 화각 바꿈 (정지 이미지 3초 이상 멈춤 방지)
    assert any("mod(floor" in z for z in plan.zoom_terms)


def test_kenburns_direction_alternates(make_plan):
    a = make_plan()
    run(a, "kenburns", {"direction": "in", "reframe_every": 0})
    b = make_plan()
    run(b, "kenburns", {"direction": "out", "reframe_every": 0})
    assert "(1-" in b.zoom_terms[0] and "(1-" not in a.zoom_terms[0]


def test_punch_zoom(make_plan):
    plan = make_plan("lip")
    run(plan, "punch_zoom", {"at": 0.5, "focus": [0.4, 0.3]})
    assert plan.zoom_max == pytest.approx(1.3)
    assert "clip((t-0.5)/0.08,0,1)" in plan.zoom_terms[0]
    assert plan.pan_terms and "between(t,0.5,0.8)" in plan.pan_terms[0][0]   # 0.3초 흔들림
    assert plan.focus == (0.4, 0.3)
    assert [s.name for s in plan.sfx] == ["punch"]


def test_vo_cloud(make_plan):
    plan = make_plan("vo", speaker="소율")
    run(plan, "vo_cloud")
    assert any(f.startswith("vignette") for f in plan.post)
    assert plan.subtitle["kind"] == "cloud"
    st = plan.subtitle["style"]
    assert st["font"] == "handwriting" and st["color"].upper() == "#4FB3FF"


def test_fantasy(make_plan):
    plan = make_plan("vo", duration=2.5)
    run(plan, "fantasy")
    assert any(f.startswith("colorchannelmixer") for f in plan.post)
    names = [l.name for l in plan.layers]
    assert "sparkles" in names and "pink_edge" in names
    seq = next(l for l in plan.layers if l.name == "sparkles")
    assert seq.sequence and seq.src.parent.exists()
    assert [s.name for s in plan.sfx].count("heartbeat") == 2


def test_dialect_note(make_plan):
    plan = make_plan()
    run(plan, "dialect_note", "뭇나 = 먹었나")
    assert plan.subtitle["notes"] == ["(*뭇나 = 먹었나)"]
    plan2 = make_plan(subtitle=None)
    run(plan2, "dialect_note", "(*뭇나 = 먹었나)")
    assert plan2.subtitle["notes"] == ["(*뭇나 = 먹었나)"]


def test_freeze_sticker_extends_cut(make_plan):
    plan = make_plan("insert", duration=1.0, lead=0.0, tail=0.0, body=1.0, audio_dur=0)
    run(plan, "freeze_sticker", "배동철, 47세.\n오해 중.")
    assert plan.warps[0].kind == "freeze" and plan.warps[0].at == pytest.approx(1.0)
    assert plan.duration == pytest.approx(2.3)
    lay = next(l for l in plan.layers if l.name == "sticker")
    assert lay.src.exists() and lay.start == pytest.approx(1.0)
    # 켄번즈 카메라 시간이 정지 구간에서 멈춤
    assert "clip(t-1,0,1.3)" in plan.content_time_expr()


def test_orom_sil_slowmo(make_plan):
    plan = make_plan("lip", duration=2.0, lead=0.0)
    run(plan, "orom_sil", {"at": 0.4, "dur": 0.5, "factor": 2.5})
    assert plan.extra == pytest.approx(0.75)
    remap = plan.source_remap_expr()
    assert "*2.5" in remap and remap.count("if(") == 2
    assert any("brightness" in f for f in plan.post)
    assert any(l.name == "rays" and any("rotate" in f for f in l.filters) for l in plan.layers)
    assert [s.name for s in plan.sfx] == ["jingle"]


def test_assa_gaori_generates_placeholder_manta(make_plan):
    plan = make_plan()
    run(plan, "assa_gaori", {"at": 0.2})
    lay = next(l for l in plan.layers if l.name == "manta")
    assert lay.src.exists() and "W-(W+w)*" in lay.x
    assert [s.name for s in plan.sfx] == ["pop"]


def test_assa_gaori_missing_sprite_falls_back(make_plan):
    plan = make_plan()
    run(plan, "assa_gaori", {"sprite": "없는파일.png"})
    assert any("임시 실루엣" in n for n in plan.notes)


def test_wall_voice(make_plan):
    plan = make_plan()
    run(plan, "wall_voice")
    assert any(f.startswith("lowpass=f=850") for f in plan.audio_filters)
    assert any(f.startswith("highpass") for f in plan.audio_filters)


def test_brake_scratch(make_plan):
    plan = make_plan()
    run(plan, "brake_scratch", 0.3)
    assert plan.bgm_events == [{"kind": "brake", "at": 0.3, "brake": 0.35}]
    assert [s.name for s in plan.sfx] == ["scratch"]


def test_disabled_in_calm_preset():
    from video_engine.tests.conftest import preset_settings
    calm = preset_settings("calm")
    for name in ("punch_zoom", "vo_cloud", "fantasy", "freeze_sticker", "orom_sil", "assa_gaori", "brake_scratch"):
        assert not fx.is_enabled(calm, name), name
    assert fx.is_enabled(calm, "kenburns")


def test_door_wipe_transition(make_plan):
    prev, cur = make_plan(duration=2.0), make_plan(duration=2.0)
    t = TRANSITIONS["door_wipe"]
    p = dict(t.defaults, to="오후 2시역", **{"from": "새벽 4시역"})
    t.timing(prev, cur, p)
    assert prev.tail == pytest.approx(0.2 + 0.35 + 0.35) and cur.lead == pytest.approx(0.1 + 0.35 + 0.35)
    t.apply(prev, cur, p)
    assert {l.name for l in prev.layers} == {"doorL", "doorR", "card"}
    assert {l.name for l in cur.layers} == {"doorL", "doorR", "card"}
    assert [s.name for s in prev.sfx] == ["dingdong"]


def test_fade_transition_overlap(make_plan):
    prev, cur = make_plan(), make_plan()
    t = TRANSITIONS["fade"]
    p = dict(t.defaults, duration=0.5)
    t.timing(prev, cur, p)
    t.apply(prev, cur, p)
    assert cur.overlap_in == 0.5 and cur.xfade_in["duration"] == 0.5


def test_camera_expressions_are_ffmpeg_safe(make_plan):
    """식 안에 작은따옴표/세미콜론이 들어가면 필터 그래프가 깨진다."""
    plan = make_plan(duration=3)
    for n in ("kenburns", "punch_zoom", "brake_scratch"):
        run(plan, n)
    for e in plan.zoom_terms + [x for xy in plan.pan_terms for x in xy]:
        assert not re.search(r"[';\[\]]", e), e
