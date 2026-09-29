"""자막 표기, SRT, 매니페스트, 설정, 오디오(numpy) 테스트 — ffmpeg 불필요."""
from __future__ import annotations

import numpy as np
import pytest

from video_engine import sfx_synth
from video_engine.config import build_settings
from video_engine.graphics.text import parse_markup, strip_markup, wrap_spans
from video_engine.manifest import ManifestError, load_manifest, select_range
from video_engine.render.audio import SR, _brake, loop_crossfade, place
from video_engine.subtitles import write_srt
from video_engine.util import norm_path


def test_markup_colors():
    lines = parse_markup("아따 *진짜* [뭇나]? 시끄럽노", {"시끄럽노": "dialect"})
    roles = {t: r for t, r in lines[0]}
    assert roles["진짜"] == "em" and roles["뭇나"] == "dialect" and roles["시끄럽노"] == "dialect"
    assert strip_markup("아따 *진짜* [뭇나]?") == "아따 진짜 뭇나?"


def test_wrap_balances_lines():
    lines = wrap_spans(parse_markup("동철아 니 또 옆집 아가씨 괴롭히나 진짜로"), 12)
    assert len(lines) == 2
    lens = [sum(len(t) for t, _ in l) for l in lines]
    assert abs(lens[0] - lens[1]) <= 6


def test_srt(tmp_path):
    p = write_srt([(1.5, 3.25, "둘째"), (0.0, 1.0, "첫째")], tmp_path / "a.srt")
    txt = p.read_text(encoding="utf-8-sig")
    assert txt.startswith("1\n00:00:00,000 --> 00:00:01,000\n첫째")
    assert "00:00:01,500 --> 00:00:03,250" in txt


def _manifest(tmp_path, body: str):
    f = tmp_path / "ep.yaml"
    f.write_text(body, encoding="utf-8")
    return f


def test_manifest_effect_notations(tmp_path):
    f = _manifest(tmp_path, """
meta: {title: t, preset: buakom}
cuts:
  - {id: 8, type: insert, effects: [punch_zoom, {dialect_note: "뭇나 = 먹었나"}, {name: fantasy, at: 0.2}]}
  - {id: 9, type: insert, transition: door_wipe, sfx: [{name: pop, at: 0.3}]}
  - {id: 27, type: insert}
""")
    m = load_manifest(f)
    assert m.cuts[0].effects == [("punch_zoom", {}), ("dialect_note", "뭇나 = 먹었나"), ("fantasy", {"at": 0.2})]
    assert m.cuts[1].transition == {"type": "door_wipe"}
    assert [c.id for c in select_range(m, "8-27")] == ["8", "9", "27"]
    assert [c.id for c in select_range(m, "c09-c27")] == ["9", "27"]
    with pytest.raises(ManifestError):
        select_range(m, "5-6")


def test_manifest_rejects_bad_type(tmp_path):
    with pytest.raises(ManifestError):
        load_manifest(_manifest(tmp_path, "cuts:\n  - {id: 1, type: talk}\n"))


def test_windows_paths():
    p = norm_path(r"assets\c01.png", None)
    assert str(p).replace("\\", "/") == "assets/c01.png"


def test_settings_merge_order(tmp_path):
    (tmp_path / "config.yaml").write_text("video: {encoder: h264_nvenc}\nsfx: {pop: sfx/pop.wav}\n",
                                          encoding="utf-8")
    m = {"meta": {"overrides": {"subtitle": {"size": 99}}}, "speakers": {"동철": {"color": "#FF0000"}}}
    s = build_settings("buakom", m, tmp_path)
    assert s["video"]["encoder"] == "h264_nvenc"
    assert s["subtitle"]["size"] == 99
    assert s["speakers"]["동철"]["color"] == "#FF0000"
    assert "아따" in s["speakers"]["동철"]["keywords"]         # 프리셋 값은 유지
    assert s["sfx"]["pop"]["file"].replace("\\", "/").endswith("sfx/pop.wav")


def test_sfx_synth_all():
    for name in sfx_synth.SYNTHS:
        x = sfx_synth.synth(name)
        assert x.ndim == 2 and x.shape[1] == 2 and len(x) > SR * 0.1
        assert 0.5 < np.max(np.abs(x)) <= 1.0


def test_place_clips_at_edges():
    bus = np.zeros((SR, 2), np.float32)
    place(bus, np.ones((SR // 2, 2), np.float32), 0.75)
    assert bus[-1, 0] == 1 and bus[int(0.74 * SR), 0] == 0
    place(bus, np.ones((SR // 2, 2), np.float32), -0.25)
    assert bus[0, 0] == 1


def test_loop_crossfade_makes_seamless_end():
    x = np.stack([np.arange(SR * 2, dtype=np.float32)] * 2, axis=1)
    y = loop_crossfade(x, 0.5)
    assert len(y) == SR * 2 - SR // 2
    assert y[0, 0] == x[SR // 2, 0]                 # 처음 = 원래 0.5초 지점
    assert y[-1, 0] == pytest.approx(x[SR // 2 - 1, 0], abs=1)   # 끝 = 그 바로 앞 → 이어짐


def test_brake_slows_down():
    x = np.stack([np.sin(np.arange(SR) / SR * 2 * np.pi * 440)] * 2, axis=1).astype(np.float32)
    y = _brake(x, 0, 0.35)
    assert len(y) == int(0.35 * SR)
    # 끝으로 갈수록 파형이 느려진다(부호 바뀜 횟수 감소)
    zc = lambda a: int(np.sum(np.diff(np.sign(a)) != 0))
    q = len(y) // 4
    assert zc(y[:q, 0]) > zc(y[-q:, 0]) * 2
