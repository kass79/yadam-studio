"""render / shorts / check / snapshot 의 전체 흐름."""
from __future__ import annotations

import os
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from .config import build_settings, resolve_font
from .graphics.text import render_lines
from .manifest import Manifest, load_manifest, select_range, validate_files
from .render import audio, ffmpeg
from .render.segment import cache_key, encoder_args, render_segment, render_xfade
from .subtitles import render_layers, srt_entries, write_srt
from .timeline import Timeline, build_timeline, summary
from .util import deep_merge, ff_path, fnum, log, safe_name


@dataclass
class Job:
    manifest: Manifest
    settings: dict
    work: Path
    draft: bool


def prepare(manifest_path: str, *, config: str | None = None, draft: bool = False,
            preset: str | None = None) -> Job:
    m = load_manifest(manifest_path)
    s = build_settings(preset or m.preset, m.raw, m.dir, config)
    eng = s.get("engine") or {}
    ffmpeg.configure(eng.get("ffmpeg"), eng.get("ffprobe"))
    if not ffmpeg.available():
        raise RuntimeError("ffmpeg를 찾을 수 없습니다. config.yaml의 engine.ffmpeg에 ffmpeg.exe 경로를 적어주세요.")
    missing = validate_files(m)
    if missing:
        raise FileNotFoundError("없는 파일이 있습니다:\n  " + "\n  ".join(missing))
    work = Path(eng["work_dir"]) if eng.get("work_dir") else m.dir / "_work" / safe_name(m.path.stem)
    if draft:
        work = work.with_name(work.name + "_draft")
    work.mkdir(parents=True, exist_ok=True)
    resolve_font(s, "main")   # 폰트 없으면 여기서 바로 알려줌
    return Job(m, s, work, draft)


def _canvas(job: Job, size) -> tuple[int, int]:
    w, h = size
    if job.draft:
        w, h = int(w / 2) // 2 * 2, int(h / 2) // 2 * 2
    return w, h


def _jobs(job: Job) -> int:
    n = int((job.settings.get("engine") or {}).get("jobs") or 0)
    if n <= 0:
        n = max(1, min(6, (os.cpu_count() or 2) // 2))
    return n


def render_segments(job: Job, tl: Timeline, tag: str) -> list[Path]:
    """컷별 영상 파일을 (캐시 확인 후) 병렬로 만든다. 크로스페이드 컷은 한 번 더 이어 붙인다."""
    for p in tl.plans:
        render_layers(p)
    seg_dir = job.work / f"seg_{tag}"
    seg_dir.mkdir(parents=True, exist_ok=True)
    use_cache = bool((job.settings.get("engine") or {}).get("cache", True))
    raw: list[Path] = []
    todo = []
    for p in tl.plans:
        key = cache_key(p, job.settings, job.draft)
        out = seg_dir / f"{p.cut.index:03d}_{safe_name(p.cut.id)}_{key}.mp4"
        raw.append(out)
        if not (use_cache and out.exists()):
            todo.append((p, out))
    t0 = time.time()
    log(f"▶ 컷 렌더: {len(todo)}개 새로, {len(raw) - len(todo)}개 캐시 재사용 (동시 {_jobs(job)}개)")

    def work(item):
        p, out = item
        render_segment(p, out, job.settings, draft=job.draft)
        log(f"  ✓ 컷 {p.cut.id} ({p.duration:.2f}s)")

    with ThreadPoolExecutor(max_workers=_jobs(job)) as ex:
        list(ex.map(work, todo))
    final: list[Path] = []
    for i, p in enumerate(tl.plans):
        if p.xfade_in and i > 0:
            out = raw[i].with_name(raw[i].stem + f"_x{safe_name(raw[i - 1].stem[-12:])}.mp4")
            if not (use_cache and out.exists()):
                render_xfade(raw[i - 1], tl.plans[i - 1].duration, raw[i], p, out, job.settings, draft=job.draft)
            final.append(out)
        else:
            final.append(raw[i])
    log(f"  컷 렌더 {time.time() - t0:.1f}초")
    return final


def _concat_list(tl: Timeline, segs: list[Path], path: Path) -> Path:
    lines = ["ffconcat version 1.0"]
    for i, (p, seg) in enumerate(zip(tl.plans, segs)):
        lines.append("file '" + ff_path(seg.resolve()).replace("'", r"'\''") + "'")
        nxt = tl.plans[i + 1] if i + 1 < len(tl.plans) else None
        if nxt is not None and nxt.overlap_in > 0:
            # 다음 컷이 이 컷 꼬리를 크로스페이드로 가져감 → 반 프레임 여유를 둔 outpoint
            frames = round((p.duration - nxt.overlap_in) * tl.fps)
            lines.append(f"outpoint {fnum((frames - 0.5) / tl.fps)}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _mux(job: Job, tl: Timeline, segs: list[Path], mix: Path, out: Path, *, loop: float = 0.0,
         hook: Path | None = None, hook_hold: float = 1.0) -> Path:
    lst = _concat_list(tl, segs, job.work / f"concat_{out.stem}.txt")
    a = job.settings.get("audio") or {}
    length = tl.total - loop
    args = ["-f", "concat", "-safe", "0", "-i", ff_path(lst), "-i", ff_path(mix)]
    vf = []
    if loop > 0:
        vf.append(f"[0:v]split=2[va][vb];[va]trim=start={fnum(loop)},setpts=PTS-STARTPTS[vm];"
                  f"[vb]trim=duration={fnum(loop)},setpts=PTS-STARTPTS[vh];"
                  f"[vm][vh]xfade=transition=fade:duration={fnum(loop)}:offset={fnum(tl.total - 2 * loop)}[v0]")
    else:
        vf.append("[0:v]null[v0]")
    if hook is not None:
        args += ["-loop", "1", "-framerate", str(tl.fps), "-t", fnum(length), "-i", ff_path(hook)]
        y = float(((job.settings.get("shorts") or {}).get("hook") or {}).get("y", 0.12))
        vf.append(f"[2:v]format=rgba,fade=t=in:st=0:d=0.08:alpha=1,"
                  f"fade=t=out:st={fnum(max(0.1, hook_hold - 0.2))}:d=0.2:alpha=1[hk];"
                  f"[v0][hk]overlay=x=(W-w)/2:y=H*{fnum(y)}-h/2:enable='between(t,0,{fnum(hook_hold)})':"
                  f"eof_action=pass[v1]")
    else:
        vf.append("[v0]null[v1]")
    vf.append("[v1]setsar=1,format=yuv420p[vout]")
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.stem + ".part.mp4")
    ffmpeg.run(args + ["-filter_complex", ";".join(vf), "-map", "[vout]", "-map", "1:a",
                       "-r", str(tl.fps)] + encoder_args(job.settings, final=True, draft=job.draft)
               + ["-c:a", "aac", "-b:a", str(a.get("aac_bitrate", "192k")), "-ar", "48000",
                  "-t", fnum(length), "-movflags", "+faststart", ff_path(tmp)],
               desc="최종 합치기 (AAC 인코딩은 여기서 한 번만)")
    tmp.replace(out)
    return out


def _finish_audio(job: Job, tl: Timeline, segs: list[Path], buses: dict, out: Path, *, loop: float = 0.0,
                  hook: Path | None = None, hook_hold: float = 1.0) -> dict:
    """믹스 → mux → true peak 확인. 넘으면 리미터 천장을 낮춰 오디오만 다시(영상은 복사)."""
    mix = audio.final_mix(buses, job.settings, tl.total, job.work / f"mix_{out.stem}.wav", loop=loop)
    _mux(job, tl, segs, mix, out, loop=loop, hook=hook, hook_hold=hook_hold)
    meas = ffmpeg.measure_output(out)
    limit = float((job.settings.get("audio") or {}).get("true_peak", -1.5))
    if meas["true_peak"] > -0.5:
        over = meas["true_peak"] - limit
        log(f"  true peak {meas['true_peak']:.2f} dBTP → 리미터 천장을 {over:.1f}dB 더 낮춰 오디오만 재인코딩")
        mix = audio.final_mix(buses, job.settings, tl.total, job.work / f"mix_{out.stem}.wav", loop=loop,
                              ceiling_offset=over)
        tmp = out.with_name(out.stem + ".fix.mp4")
        a = job.settings.get("audio") or {}
        ffmpeg.run(["-i", ff_path(out), "-i", ff_path(mix), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", str(a.get("aac_bitrate", "192k")), "-ar", "48000",
                    "-t", fnum(tl.total - loop), "-movflags", "+faststart", ff_path(tmp)], desc="오디오 재인코딩")
        tmp.replace(out)
        meas = ffmpeg.measure_output(out)
    return meas


def _out_path(job: Job, out: str | None, suffix: str = "") -> Path:
    if out:
        return Path(out).resolve()
    meta_out = job.manifest.meta.get("output")
    if meta_out and not suffix:
        from .util import norm_path
        return norm_path(meta_out, job.manifest.dir)
    return job.manifest.dir / "out" / f"{job.manifest.path.stem}{suffix}{'_draft' if job.draft else ''}.mp4"


# ─────────────────────────── 명령들 ───────────────────────────

def check(manifest_path: str, *, config: str | None = None, draft: bool = False) -> str:
    job = prepare(manifest_path, config=config, draft=draft)
    tl = build_timeline(job.manifest, job.settings, canvas=_canvas(job, job.manifest.size), work_dir=job.work)
    lines = [f"■ {job.manifest.title}  (프리셋: {job.manifest.preset}, {tl.canvas[0]}x{tl.canvas[1]} "
             f"{tl.fps}fps)", summary(tl, job.settings)]
    if tl.warnings:
        lines += ["", "주의:"] + [f"  - {w}" for w in tl.warnings]
    return "\n".join(lines)


def render(manifest_path: str, *, config: str | None = None, out: str | None = None, draft: bool = False) -> dict:
    t0 = time.time()
    job = prepare(manifest_path, config=config, draft=draft)
    tl = build_timeline(job.manifest, job.settings, canvas=_canvas(job, job.manifest.size), work_dir=job.work)
    log(f"■ {job.manifest.title}: {len(tl.plans)}컷, {tl.total:.2f}초")
    for w in tl.warnings:
        log(f"  ⚠ {w}")
    segs = render_segments(job, tl, "main")
    log("▶ 오디오 버스")
    buses = audio.build_buses(tl, job.manifest, job.settings, job.work)
    out_path = _out_path(job, out)
    meas = _finish_audio(job, tl, segs, buses, out_path)
    srt = write_srt([e for p in tl.plans for e in srt_entries(p)], out_path.with_suffix(".srt"))
    info = ffmpeg.probe(out_path)
    log(f"✔ 완성: {out_path}  ({info.duration:.2f}초, {meas['lufs']:.1f} LUFS, true peak {meas['true_peak']:.2f} dBTP, "
        f"{time.time() - t0:.0f}초 걸림)")
    return {"video": out_path, "srt": srt, "duration": info.duration, "timeline": tl, **meas}


def shorts(manifest_path: str, cuts: str, *, config: str | None = None, out: str | None = None,
           hook: str | None = None, draft: bool = False) -> dict:
    t0 = time.time()
    job = prepare(manifest_path, config=config, draft=draft)
    m, s = job.manifest, job.settings
    sh = s.get("shorts") or {}
    sel = select_range(m, cuts)
    # 쇼츠 설정: 프리셋 shorts ← 매니페스트 shorts
    sh = deep_merge(sh, {k: v for k, v in (m.shorts or {}).items() if k not in ("hook_text",)})
    s = deep_merge(s, {"shorts": sh})
    job.settings = s
    loop = float(sh.get("loop", 0.4))
    # 구간 시작 시점의 BGM 상태 (전체 타임라인 기준)
    full = build_timeline(m, s, canvas=_canvas(job, m.size), work_dir=job.work)
    first = next(p for p in full.plans if p.cut.id == sel[0].id)
    canvas = _canvas(job, tuple(sh.get("size", [1080, 1920])))
    tl = build_timeline(m, s, cuts=sel, canvas=canvas, vertical=True, work_dir=job.work / "shorts",
                        head_pad=loop)
    if sel[0].bgm_cue is None:
        tl.bgm_start = audio.bgm_state_at(full, first.start)
    log(f"■ 쇼츠 {cuts}: {len(tl.plans)}컷, {tl.total - loop:.2f}초 ({canvas[0]}x{canvas[1]})")
    if tl.total - loop > float(sh.get("max_duration", 60)):
        log(f"  ⚠ 쇼츠 길이가 {sh.get('max_duration', 60)}초를 넘습니다")
    for w in tl.warnings:
        log(f"  ⚠ {w}")
    segs = render_segments(job, tl, f"shorts_{safe_name(cuts)}")
    buses = audio.build_buses(tl, m, s, job.work / "shorts")
    hook_text = hook or (m.shorts or {}).get("hook_text") or (m.shorts or {}).get("hook")
    if isinstance(hook_text, dict):
        hook_text = hook_text.get("text")
    hook_png = None
    if hook_text:
        hook_png = _hook_png(job, str(hook_text), canvas)
    hold = sh.get("hook_hold", 1.0)
    hold = (tl.total - loop) if hold in ("all", None) else float(hold)
    out_path = Path(out).resolve() if out else _out_path(job, None, f"_shorts_{safe_name(cuts)}")
    meas = _finish_audio(job, tl, segs, buses, out_path, loop=loop, hook=hook_png, hook_hold=hold)
    entries = [(max(0.0, a - loop), b - loop, t) for p in tl.plans for (a, b, t) in srt_entries(p)
               if b - loop > 0]
    srt = write_srt(entries, out_path.with_suffix(".srt"))
    info = ffmpeg.probe(out_path)
    log(f"✔ 쇼츠 완성: {out_path}  ({info.duration:.2f}초, true peak {meas['true_peak']:.2f} dBTP, "
        f"{time.time() - t0:.0f}초)")
    return {"video": out_path, "srt": srt, "duration": info.duration, "timeline": tl, **meas}


def _hook_png(job: Job, text: str, canvas: tuple[int, int]) -> Path:
    st = ((job.settings.get("shorts") or {}).get("hook") or {})
    u = min(canvas) / 1080
    lines = [[(ln, "normal")] for ln in text.split("\n")]
    img = render_lines(lines, font=resolve_font(job.settings, st.get("font", "heavy")), size=int(st.get("size", 78) * u),
                       colors={"normal": st.get("color", "#FFFFFF")}, stroke=st.get("stroke", "#000000"),
                       stroke_width=int(st.get("stroke_width", 8) * u), box=st.get("box"), box_radius=int(20 * u),
                       pad=int(18 * u))
    if img.width > canvas[0] * 0.94:
        r = canvas[0] * 0.94 / img.width
        img = img.resize((int(img.width * r), int(img.height * r)), Image.LANCZOS)
    p = job.work / "shorts" / "hook.png"
    p.parent.mkdir(parents=True, exist_ok=True)
    img.save(p)
    return p


def snapshot(manifest_path: str, *, cuts: str | None = None, config: str | None = None, draft: bool = True,
             out: str | None = None, per_cut: int = 3) -> Path:
    """컷별 영상을 만들고 앞·중간·뒤 프레임을 모은 확인용 한 장(contact sheet)."""
    job = prepare(manifest_path, config=config, draft=draft)
    tl = build_timeline(job.manifest, job.settings, canvas=_canvas(job, job.manifest.size), work_dir=job.work)
    if cuts:
        ids = {c.id for c in select_range(job.manifest, cuts)}
        tl.plans = [p for p in tl.plans if p.cut.id in ids]
    segs = render_segments(job, tl, "main")
    thumbs = []
    tw = 480
    for p, seg in zip(tl.plans, segs):
        row = []
        for k in range(per_cut):
            t = p.duration * (k + 0.5) / per_cut
            f = job.work / "snap" / f"{p.cut.index:03d}_{k}.png"
            f.parent.mkdir(parents=True, exist_ok=True)
            ffmpeg.run(["-ss", fnum(t), "-i", ff_path(seg), "-frames:v", "1", "-vf", f"scale={tw}:-2", ff_path(f)],
                       desc="스냅샷")
            row.append(Image.open(f).convert("RGB"))
        thumbs.append((p, row))
    th = thumbs[0][1][0].height
    label_w = 150
    sheet = Image.new("RGB", (label_w + tw * per_cut, th * len(thumbs)), (18, 18, 18))
    from PIL import ImageDraw
    dr = ImageDraw.Draw(sheet)
    from .graphics.text import load_font
    fp, fi = resolve_font(job.settings, "main")
    fnt = load_font(fp, 22, fi)
    for r, (p, row) in enumerate(thumbs):
        dr.text((10, r * th + 10), f"컷 {p.cut.id}\n{p.cut.type}\n{p.duration:.1f}s", font=fnt, fill=(230, 230, 230))
        for c, im in enumerate(row):
            sheet.paste(im, (label_w + c * tw, r * th))
    dest = Path(out).resolve() if out else job.manifest.dir / "out" / f"{job.manifest.path.stem}_snapshot.jpg"
    dest.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(dest, quality=88)
    return dest


def clean(manifest_path: str) -> Path:
    m = load_manifest(manifest_path)
    work = m.dir / "_work" / safe_name(m.path.stem)
    for w in (work, work.with_name(work.name + "_draft")):
        if w.exists():
            shutil.rmtree(w)
    return work
