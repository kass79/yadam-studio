"""효과 플러그인 등록부.

새 효과 추가 = 함수 하나 + 데코레이터 한 줄:

    from video_engine.effects.registry import effect

    @effect("my_glitch", defaults={"at": 0.0, "dur": 0.2}, primary="dur")
    def my_glitch(plan, p):
        plan.post.append(f"noise=alls=40:allf=t:enable='{plan.enable(p['at'], p['at'] + p['dur'])}'")

- plan: video_engine.plan.CutPlan (컷 렌더 계획서)
- p: 기본값 ← 프리셋(effects.<이름>) ← 매니페스트에 적힌 값 순으로 병합된 파라미터
- primary: 매니페스트에서 `- my_glitch: 0.5` 처럼 값 하나만 줄 때 들어갈 파라미터 이름
- timing: 컷 길이를 바꾸는 효과(정지·슬로모션)는 timing=함수 로 길이 계산 단계에 참여
효과 모듈 파일을 video_engine/effects/ 에 두면 자동으로 불러온다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from ..util import deep_merge


@dataclass
class Effect:
    name: str
    apply: Callable
    defaults: dict = field(default_factory=dict)
    primary: str | None = None
    timing: Callable | None = None
    doc: str = ""
    kind: str = "effect"      # effect | transition

    def resolve(self, settings: dict, given: Any) -> dict:
        """기본값 ← 프리셋 ← 매니페스트 값."""
        preset = dict((settings.get("effects") or {}).get(self.name) or {})
        preset.pop("enabled", None)
        p = deep_merge(self.defaults, preset)
        if isinstance(given, dict):
            p = deep_merge(p, given)
        elif given is not None and given != {}:
            if not self.primary:
                raise ValueError(f"효과 '{self.name}'는 값 하나만 받을 수 없습니다. {{키: 값}} 형태로 적어주세요.")
            p[self.primary] = given
        return p


EFFECTS: dict[str, Effect] = {}
TRANSITIONS: dict[str, Effect] = {}


def effect(name: str, *, defaults: dict | None = None, primary: str | None = None,
           timing: Callable | None = None):
    def deco(fn: Callable) -> Callable:
        if name in EFFECTS:
            raise ValueError(f"효과 이름 중복: {name}")
        EFFECTS[name] = Effect(name, fn, dict(defaults or {}), primary, timing,
                               (fn.__doc__ or "").strip())
        return fn
    return deco


def transition(name: str, *, defaults: dict | None = None, timing: Callable | None = None):
    """전환 플러그인: apply(prev_plan, cur_plan, p), timing(prev_plan, cur_plan, p)."""
    def deco(fn: Callable) -> Callable:
        if name in TRANSITIONS:
            raise ValueError(f"전환 이름 중복: {name}")
        TRANSITIONS[name] = Effect(name, fn, dict(defaults or {}), None, timing,
                                   (fn.__doc__ or "").strip(), kind="transition")
        return fn
    return deco


def is_enabled(settings: dict, name: str) -> bool:
    cfg = (settings.get("effects") or {}).get(name)
    if cfg is None:
        return True
    if isinstance(cfg, bool):
        return cfg
    return bool(cfg.get("enabled", True))


def get(name: str) -> Effect:
    if name not in EFFECTS:
        raise KeyError(f"모르는 효과 '{name}'. 사용 가능: {', '.join(sorted(EFFECTS))}")
    return EFFECTS[name]
