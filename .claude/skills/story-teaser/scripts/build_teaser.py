#!/usr/bin/env python3
"""spec.json → HyperFrames 합성 HTML 생성기.

사용법:
    python3 build_teaser.py spec.json > index.html

spec.json 예시는 SKILL.md 참고. 16:9 / 9:16 자동 대응.
"""
import json
import sys

STYLES = {
    "cinematic": {  # ① 시네마틱 미스터리
        "font": '"Noto Serif CJK KR", serif',
        "cap_color": "#f2ede4",
        "em_color": "#e85555",
        "end_bg": "#060608",
        "cta_color": "#b7ab98",
        "vignette": True,
        "grain": 0.06,
        "cap_weight": 700,
    },
    "scroll": {  # ② 야담 두루마리
        "font": '"Noto Serif CJK KR", serif',
        "cap_color": "#f7f0dd",
        "em_color": "#c0392b",
        "end_bg": "#1a140c",
        "cta_color": "#a89372",
        "vignette": True,
        "grain": 0.11,
        "cap_weight": 700,
    },
    "punchy": {  # ③ 킬러 쇼츠 훅
        "font": '"Noto Sans CJK KR", sans-serif',
        "cap_color": "#ffffff",
        "em_color": "#ffd400",
        "end_bg": "#000000",
        "cta_color": "#dddddd",
        "vignette": False,
        "grain": 0.03,
        "cap_weight": 900,
    },
}


def build(spec):
    st = STYLES[spec.get("style", "cinematic")]
    vertical = spec.get("aspect", "16:9") == "9:16"
    W, H = (1080, 1920) if vertical else (1920, 1080)
    dur = float(spec["duration"])
    shots = spec["shots"]
    caps = spec["captions"]
    end = spec.get("endcard", {})
    src_w, src_h = spec.get("source_size", [1376, 768])

    cap_fs = 62 if vertical else 52
    cap_bottom = 300 if vertical else 88
    cap_h = 240 if vertical else 190
    end_fs = 66 if vertical else 58
    cta_fs = 40 if vertical else 32
    grad_h = 720 if vertical else 400
    vig = ("radial-gradient(ellipse 90% 70% at 50% 42%," if vertical
           else "radial-gradient(ellipse 72% 88% at 50% 45%,")

    # 이미지: 높이를 캔버스에 맞추고 focus(0~1)로 가로 위치 결정
    fill_w = src_w * H / src_h
    kb_css = []
    for i, s in enumerate(shots, 1):
        # 스케일 1.0에서도 프레임이 항상 채워지도록 클램프 (검은 띠 방지)
        left = round(W / 2 - float(s.get("focus", 0.5)) * fill_w)
        left = min(0, max(round(W - fill_w), left))
        oy = s.get("origin_y", 45)
        kb_css.append(
            f"      #kb{i} {{ left: {left}px; "
            f"transform-origin: {int(float(s.get('focus',0.5))*100)}% {oy}%; }}")
    kb_css = "\n".join(kb_css)

    shot_html, cap_html, tl = [], [], []
    for i, s in enumerate(shots, 1):
        trk = 1 if i % 2 else 2
        shot_html.append(
            f'      <section id="s{i}" class="clip" data-start="{s["start"]}" '
            f'data-duration="{s["dur"]}" data-track-index="{trk}" data-layout-allow-overflow>\n'
            f'        <div class="fade" id="f{i}"><img class="kb" id="kb{i}" '
            f'src="./assets/{s["image"]}" alt="" /></div>\n      </section>')
        a, b = (1.02, 1.16) if s.get("zoom", "in") == "in" else (1.16, 1.02)
        tl.append(f'      tl.fromTo("#kb{i}", {{ scale: {a} }}, '
                  f'{{ scale: {b}, duration: {s["dur"]}, ease: "none" }}, {s["start"]});')
        if i > 1:  # 크로스페이드 진입
            tl.append(f'      tl.fromTo("#f{i}", {{ opacity: 0 }}, '
                      f'{{ opacity: 1, duration: 0.6, ease: "power1.inOut" }}, {s["start"]});')
            if i < len(shots):
                nxt = float(shots[i]["start"])
                tl.append(f'      tl.to("#f{i}", {{ opacity: 0, duration: 0.6, '
                          f'ease: "power1.inOut" }}, {nxt});')
                tl.append(f'      tl.set("#f{i}", {{ opacity: 0 }}, {round(nxt+0.6,2)});')

    end_start = float(end.get("start", dur - 2.6))
    for i, c in enumerate(shots, 1):
        pass
    for i, c in enumerate(caps, 1):
        l2 = c.get("line2", "")
        em = c.get("em", "")
        pre, post = (l2.split(em, 1) + [""])[:2] if em and em in l2 else (l2, "")
        line2 = (f'{pre}<span class="em" id="em{i}">{em}</span>{post}'
                 if em else l2)
        cap_html.append(
            f'      <section id="c{i}" class="clip cap" data-start="{c["start"]}" '
            f'data-duration="{c["dur"]}" data-track-index="10" data-layout-allow-overflow>\n'
            f'        <div class="line">{c.get("line1","")}</div>\n'
            f'        <div class="line">{line2}</div>\n      </section>')
        out = round(float(c["start"]) + float(c["dur"]) - 0.3, 2)
        tl.append(f'      tl.fromTo("#c{i} .line", {{ y: 26, autoAlpha: 0 }}, '
                  f'{{ y: 0, autoAlpha: 1, duration: 0.55, ease: "power2.out", '
                  f'stagger: 0.18 }}, {c["start"]});')
        if em:
            t0 = round(float(c["start"]) + 0.5, 2)
            tl.append(f'      tl.fromTo("#em{i}", {{ scale: 1 }}, {{ scale: 1.07, '
                      f'duration: 0.22, ease: "power2.out" }}, {t0});')
            tl.append(f'      tl.to("#em{i}", {{ scale: 1, duration: 0.25, '
                      f'ease: "power2.inOut" }}, {round(t0+0.22,2)});')
        tl.append(f'      tl.to("#c{i} .line", {{ autoAlpha: 0, duration: 0.3, '
                  f'ease: "power1.in" }}, {out});')
        # 하드 킬: seek이 페이드 뒤에 착지해도 상태가 남지 않도록
        tl.append(f'      tl.set("#c{i} .line", {{ autoAlpha: 0 }}, {round(out+0.3,2)});')

    # 번개
    flash_html = ""
    for at in spec.get("lightning", []):
        pass
    if spec.get("lightning"):
        f0 = min(spec["lightning"])
        flash_html = (f'      <section id="flash" class="clip" data-start="{f0}" '
                      f'data-duration="1.2" data-track-index="6">\n'
                      f'        <div id="flash-i"></div>\n      </section>')
        for j, at in enumerate(spec["lightning"]):
            amp = 0.55 if j == 0 else 0.35
            tl.append(f'      tl.to("#flash-i", {{ opacity: {amp}, duration: 0.07, '
                      f'ease: "none" }}, {at});')
            tl.append(f'      tl.to("#flash-i", {{ opacity: 0, duration: 0.16, '
                      f'ease: "power1.out" }}, {round(at+0.07,2)});')
            tl.append(f'      tl.set("#flash-i", {{ opacity: 0 }}, {round(at+0.23,2)});')

    em_end = end.get("em", "")
    l2e = end.get("line2", "")
    pre_e, post_e = ((l2e.split(em_end, 1) + [""])[:2] if em_end and em_end in l2e
                     else (l2e, ""))
    end_line2 = (f'{pre_e}<span class="em">{em_end}</span>{post_e}' if em_end else l2e)

    tl.append(f'      tl.fromTo("#end-fade", {{ opacity: 0 }}, {{ opacity: 1, '
              f'duration: 0.5, ease: "power1.inOut" }}, {end_start});')
    tl.append(f'      tl.fromTo("#end-q", {{ autoAlpha: 0, scale: 1.08 }}, '
              f'{{ autoAlpha: 1, scale: 1, duration: 0.9, ease: "power2.out" }}, '
              f'{round(end_start+0.4,2)});')
    tl.append(f'      tl.fromTo("#end-cta", {{ autoAlpha: 0, y: 16 }}, '
              f'{{ autoAlpha: 1, y: 0, duration: 0.6, ease: "power2.out" }}, '
              f'{round(end_start+1.2,2)});')
    grain_reps = int(dur / 0.5) - 1
    tl.append(f'      tl.fromTo("#grain-i", {{ opacity: {st["grain"]-0.01:.2f} }}, '
              f'{{ opacity: {st["grain"]+0.03:.2f}, duration: 0.5, ease: "none", '
              f'repeat: {grain_reps}, yoyo: true }}, 0);')

    vig_block = (f'''      <section id="vig" class="clip" data-start="0" data-duration="{dur}" data-track-index="7">
        <div id="vig-i"></div>
      </section>''' if st["vignette"] else "")

    return f"""<!doctype html>
<html lang="ko">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W}, height={H}" />
    <title>{spec.get('title','하이라이트 티저')}</title>
    <script src="./node_modules/gsap/dist/gsap.min.js"></script>
    <style>
      @font-face {{ font-family: "Noto Serif CJK KR"; src: local("Noto Serif CJK KR"); }}
      @font-face {{ font-family: "Noto Sans CJK KR"; src: local("Noto Sans CJK KR"); }}
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ width: {W}px; height: {H}px; overflow: hidden; background: #000;
        font-family: {st['font']}; }}
      #root {{ position: relative; width: {W}px; height: {H}px; overflow: hidden; }}
      .clip {{ position: absolute; inset: 0; overflow: hidden; }}
      #vig {{ z-index: 40; }} #grain {{ z-index: 41; }}
      #flash {{ z-index: 30; }} #grad {{ z-index: 20; }}
      #endcard {{ z-index: 50; }} .cap {{ z-index: 60; }}

      .fade {{ position: absolute; inset: 0; overflow: hidden; }}
      .kb {{ position: absolute; top: 0; height: {H}px; width: auto; will-change: transform; }}
{kb_css}

      .cap {{ position: absolute; left: 0; right: 0; bottom: {cap_bottom}px; top: auto;
        height: {cap_h}px; display: flex; flex-direction: column; align-items: center;
        gap: 14px; overflow: visible; }}
      .cap .line {{ font-size: {cap_fs}px; font-weight: {st['cap_weight']};
        line-height: 1.35; color: {st['cap_color']}; text-align: center;
        text-shadow: 0 2px 8px rgba(0,0,0,.9), 0 0 40px rgba(0,0,0,.7); }}
      .cap .em {{ color: {st['em_color']}; display: inline-block;
        transform-origin: left center; }}  /* 팝 확대가 오른쪽으로만 — 앞 단어와 안 겹침 */

      #vig-i {{ position: absolute; inset: 0; background: {vig}
        rgba(0,0,0,0) 40%, rgba(0,0,0,.38) 74%, rgba(0,0,0,.82) 100%); }}
      #grad-i {{ position: absolute; left: 0; right: 0; bottom: 0; height: {grad_h}px;
        background: linear-gradient(to top, rgba(0,0,0,.78) 0%, rgba(0,0,0,.35) 55%,
        rgba(0,0,0,0) 100%); }}
      #grain-i {{ position: absolute; inset: 0; opacity: {st['grain']};
        background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='240' height='240'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' seed='7' stitchTiles='stitch'/><feColorMatrix type='saturate' values='0'/></filter><rect width='240' height='240' filter='url(%23n)' opacity='0.9'/></svg>");
        background-size: 240px 240px; mix-blend-mode: overlay; }}
      #flash-i {{ position: absolute; inset: 0; background: #eaf2ff; opacity: 0; }}

      #end-fade {{ position: absolute; inset: 0; }}
      #end-bg {{ position: absolute; inset: 0; background: {st['end_bg']}; }}
      #end-wrap {{ position: absolute; inset: 0; display: flex; flex-direction: column;
        align-items: center; justify-content: center; gap: 44px; }}
      #end-q {{ font-size: {end_fs}px; font-weight: 700; color: {st['cap_color']};
        text-align: center; line-height: 1.4; letter-spacing: 2px; }}
      #end-q .em {{ color: {st['em_color']}; display: inline-block; }}
      #end-cta {{ font-size: {cta_fs}px; color: {st['cta_color']}; letter-spacing: 10px; }}
      #bg-fill {{ position: absolute; inset: 0; background: #000; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0"
         data-width="{W}" data-height="{H}" data-duration="{dur}" data-fps="30">

      <section id="bg" class="clip" data-start="0" data-duration="{dur}" data-track-index="0">
        <div id="bg-fill"></div>
      </section>

{chr(10).join(shot_html)}

      <section id="endcard" class="clip" data-start="{end_start}" data-duration="{round(dur-end_start,2)}" data-track-index="9">
        <div id="end-fade">
          <div id="end-bg"></div>
          <div id="end-wrap">
            <div id="end-q">{end.get('line1','')}<div>{end_line2}</div></div>
            <div id="end-cta">{end.get('cta','본편에서 확인하세요')}</div>
          </div>
        </div>
      </section>

      <section id="grad" class="clip" data-start="0" data-duration="{end_start}" data-track-index="4">
        <div id="grad-i"></div>
      </section>

{chr(10).join(cap_html)}

{flash_html}

{vig_block}
      <section id="grain" class="clip" data-start="0" data-duration="{dur}" data-track-index="8">
        <div id="grain-i"></div>
      </section>
    </div>

    <script>
      window.__timelines = window.__timelines || {{}};
      const tl = gsap.timeline({{ paused: true }});
{chr(10).join(tl)}
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
"""


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as f:
        sys.stdout.write(build(json.load(f)))
