"""ffmpeg로 실제 렌더해 보는 테스트 (작은 해상도). ffmpeg가 없으면 건너뜀."""
from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from video_engine import pipeline
from video_engine.render import audio, ffmpeg
from video_engine.render.audio import SR, write_wav

from .conftest import needs_ffmpeg

pytestmark = needs_ffmpeg


def _tone(sec: float, f: float, amp: float = 0.3) -> np.ndarray:
    t = np.arange(int(sec * SR)) / SR
    x = (amp * np.sin(2 * np.pi * f * t)).astype(np.float32)
    return np.stack([x, x], axis=1)


@pytest.fixture(scope="module")
def src(tmp_path_factory):
    d = tmp_path_factory.mktemp("src")
    Image.new("RGB", (640, 360), "#3366AA").save(d / "still.png")
    write_wav(d / "line.wav", _tone(1.0, 220))
    write_wav(d / "bgm.wav", _tone(4.0, 110, 0.4))
    ffmpeg.run(["-f", "lavfi", "-i", "testsrc2=s=320x240:r=25:d=1.5", "-f", "lavfi", "-i",
                "sine=f=300:d=1.5", "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "-shortest",
                str(d / "lip.mp4")])
    return d


def _write(tmp_path, src, cuts_yaml: str, preset="buakom", extra="") -> str:
    f = tmp_path / "ep.yaml"
    f.write_text(f"""
meta: {{title: 테스트, fps: 30, size: [320, 180], preset: {preset}}}
bgm: {{main: {{file: '{src.as_posix()}/bgm.wav'}}}}
shorts: {{hook_text: "훅 테스트", size: [180, 320]}}
{extra}
cuts:
{cuts_yaml}
""", encoding="utf-8")
    return str(f)


EFFECT_CUTS = {
    "kenburns": "{type: vo, media: S/still.png, audio: S/line.wav}",
    "punch_zoom": "{type: lip, media: S/lip.mp4, effects: [{punch_zoom: {at: 0.3}}]}",
    "vo_cloud": "{type: vo, media: S/still.png, audio: S/line.wav, speaker: 소율, subtitle: '속마음 *테스트*'}",
    "fantasy": "{type: vo, media: S/still.png, audio: S/line.wav, effects: [fantasy]}",
    "dialect_note": "{type: lip, media: S/lip.mp4, subtitle: '밥은 [뭇나]?', effects: [{dialect_note: '뭇나 = 먹었나'}]}",
    "freeze_sticker": "{type: insert, media: S/still.png, duration: 1.0, effects: [{freeze_sticker: '오해 중.'}]}",
    "freeze_video": "{type: lip, media: S/lip.mp4, effects: [{freeze_sticker: {text: 정지, at: 0.5, dur: 0.5}}]}",
    "orom_sil": "{type: lip, media: S/lip.mp4, effects: [{orom_sil: {at: 0.3}}]}",
    "assa_gaori": "{type: vo, media: S/still.png, audio: S/line.wav, effects: [assa_gaori]}",
    "wall_voice": "{type: vo, media: S/still.png, audio: S/line.wav, effects: [wall_voice]}",
    "brake_scratch": "{type: insert, media: S/still.png, effects: [brake_scratch]}",
    "no_media": "{type: insert, subtitle: 검은 화면}",
}


@pytest.mark.parametrize("name", list(EFFECT_CUTS))
def test_effect_segment_renders(tmp_path, src, name):
    body = "  - " + EFFECT_CUTS[name].replace("S/", src.as_posix() + "/")
    mf = _write(tmp_path, src, body)
    job = pipeline.prepare(mf)
    from video_engine.timeline import build_timeline
    tl = build_timeline(job.manifest, job.settings, work_dir=job.work)
    segs = pipeline.render_segments(job, tl, "t")
    info = ffmpeg.probe(segs[0])
    assert (info.width, info.height) == (320, 180)
    assert info.duration == pytest.approx(tl.plans[0].duration, abs=0.05)


def test_sidechain_does_not_cut_bgm_after_dialogue(tmp_path):
    """(b) 대사가 1초에 끝나도 BGM은 4초까지 계속 나와야 한다."""
    total = 4.0
    dia = np.zeros((int(total * SR), 2), np.float32)
    dia[:SR] = _tone(1.0, 300, 0.3)
    buses = {"dialogue": write_wav(tmp_path / "d.wav", dia),
             "bgm": write_wav(tmp_path / "b.wav", _tone(total, 110, 0.1)),
             "sfx": write_wav(tmp_path / "s.wav", np.zeros_like(dia))}
    out = audio.final_mix(buses, {"audio": {"target_lufs": -14, "true_peak": -1.5}}, total, tmp_path / "mix.wav")
    y = audio.decode(out)
    assert len(y) == pytest.approx(total * SR, abs=SR * 0.02)
    last = y[int(3.0 * SR):]
    rms = float(np.sqrt(np.mean(last ** 2)))
    assert rms > 0.03, f"마지막 1초 BGM이 사라짐 (rms={rms})"
    assert float(np.max(np.abs(y))) <= 10 ** (-1.4 / 20)        # 리미터 천장


def test_render_and_shorts_end_to_end(tmp_path, src):
    S = src.as_posix()
    cuts = f"""
  - {{id: 1, type: insert, media: {S}/still.png, duration: 1.0, bgm_cue: main,
      transition: {{type: door_wipe, to: 새벽 4시역}}}}
  - {{id: 2, type: lip, media: {S}/lip.mp4, speaker: 동철, subtitle: "아따 [뭇나]?", effects: [punch_zoom]}}
  - {{id: 3, type: vo, media: {S}/still.png, audio: {S}/line.wav, speaker: 소율, subtitle: 속마음}}
  - {{id: 4, type: insert, media: {S}/still.png, duration: 1.0, transition: {{type: door_wipe, to: 오후 2시역}},
      effects: [brake_scratch]}}
"""
    mf = _write(tmp_path, src, cuts, extra="overrides: {}")
    r = pipeline.render(mf)
    info = ffmpeg.probe(r["video"])
    assert info.has_audio and info.has_video and (info.width, info.height) == (320, 180)
    assert info.duration == pytest.approx(r["timeline"].total, abs=0.1)
    assert r["true_peak"] < -0.5, "AAC 인코딩 후 true peak가 너무 높음"
    assert -17 < r["lufs"] < -11
    assert r["srt"].exists() and "뭇나" in r["srt"].read_text(encoding="utf-8-sig")
    # 두 번째 렌더는 캐시로 빨라야 함 (컷 파일 재사용)
    seg_count = len(list((tmp_path / "_work" / "ep" / "seg_main").glob("*.mp4")))
    pipeline.render(mf)
    assert len(list((tmp_path / "_work" / "ep" / "seg_main").glob("*.mp4"))) == seg_count

    s = pipeline.shorts(mf, "2-3", out=str(tmp_path / "s.mp4"))
    si = ffmpeg.probe(s["video"])
    assert si.width < si.height and si.has_audio
    assert si.duration == pytest.approx(s["timeline"].total - 0.4, abs=0.1)   # 루프 0.4초만큼 짧아짐


def test_calm_preset_fade_transition(tmp_path, src):
    S = src.as_posix()
    cuts = f"""
  - {{id: 1, type: insert, media: {S}/still.png, duration: 2.0, bgm_cue: main}}
  - {{id: 2, type: vo, media: {S}/still.png, audio: {S}/line.wav, subtitle: 조용한 자막, effects: [punch_zoom]}}
  - {{id: 3, type: insert, media: {S}/still.png, duration: 2.0}}
"""
    mf = _write(tmp_path, src, cuts, preset="calm")
    r = pipeline.render(mf)
    tl = r["timeline"]
    assert tl.plans[1].overlap_in > 0 and tl.plans[1].xfade_in       # 크로스페이드
    assert not any(n == "punch_zoom" for n, _ in tl.plans[1].effects)  # calm에서 꺼짐
    assert ffmpeg.probe(r["video"]).duration == pytest.approx(tl.total, abs=0.1)
