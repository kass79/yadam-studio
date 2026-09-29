from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_engine.config import DEFAULTS, PRESET_DIR, load_yaml  # noqa: E402
from video_engine.manifest import Cut  # noqa: E402
from video_engine.plan import CutPlan  # noqa: E402
from video_engine.render import ffmpeg  # noqa: E402
from video_engine.util import deep_merge  # noqa: E402

HAS_FFMPEG = ffmpeg.available()
needs_ffmpeg = pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg 없음")


def preset_settings(name: str = "buakom") -> dict:
    return deep_merge(DEFAULTS, load_yaml(PRESET_DIR / f"{name}.yaml"))


@pytest.fixture
def settings() -> dict:
    return preset_settings("buakom")


@pytest.fixture
def make_plan(tmp_path, settings):
    """ffmpeg 없이 효과 단위 테스트용 CutPlan을 만든다."""
    def _make(ctype="vo", *, duration=2.0, subtitle="아따 *진짜* [뭇나]?", speaker="동철", media=None,
              canvas=(640, 360), vertical=False, lead=0.1, body=None, tail=0.2, audio_dur=1.5, s=None):
        cut = Cut(id="1", index=0, type=ctype, media=media, speaker=speaker, subtitle=subtitle, raw={})
        scene = canvas if not vertical else (int(round(canvas[1] * 16 / 9 / 2)) * 2, canvas[1])
        p = CutPlan(cut=cut, settings=s or settings, canvas=canvas, scene=scene, fps=30,
                    assets=tmp_path / "assets" / "000_1", vertical=vertical)
        p.lead, p.tail, p.audio_dur = lead, tail, audio_dur
        p.body = body if body is not None else max(0.1, duration - lead - tail)
        p.duration = duration
        from video_engine.subtitles import build_pages
        build_pages(p)
        return p
    return _make
