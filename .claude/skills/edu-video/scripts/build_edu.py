#!/usr/bin/env python3
"""edu_spec.json → HyperFrames 교육영상 HTML 생성기.

사용법:
    python3 build_edu.py edu_spec.json > index.html

티저(build_teaser.py)와 다른 점: 이미지 켄번즈 대신 카드형 슬라이드.
슬라이드 type: title / text / rules / steps / end. 16:9 고정.
"""
import json
import sys

BG = "#0d1522"          # 진한 남색 (안전교육 톤)
FG = "#f2f5f9"
SUB = "#a8b3c2"
EM = "#ffc857"          # 강조 앰버 (주의)
ACCENT_DEFAULT = "#00A84D"  # 2호선 초록


def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def em_span(text, em):
    text = esc(text)
    em = esc(em or "")
    if em and em in text:
        pre, post = (text.split(em, 1) + [""])[:2]
        return f'{pre}<span class="em">{em}</span>{post}'
    return text


def build(spec):
    vertical = spec.get("aspect", "16:9") == "9:16"
    W, H = (1080, 1920) if vertical else (1920, 1080)
    dur = float(spec["duration"])
    accent = spec.get("accent", ACCENT_DEFAULT)
    slides = spec["slides"]
    # 내용 슬라이드 오른쪽 위에 계속 떠 있는 작은 출처 라벨 (공문 느낌)
    docref = esc(spec.get("docref", ""))

    # 소제목에 붙는 일련번호 — 같은 heading이 여러 슬라이드로 이어지면 번호를 공유한다
    sec_no, seen = {}, {}
    for idx, s in enumerate(slides):
        if s["type"] in ("text", "rules", "steps"):
            h = s.get("heading", "")
            if h not in seen:
                seen[h] = len(seen) + 1
            sec_no[idx] = seen[h]

    html, tl = [], []
    for i, s in enumerate(slides, 1):
        t0 = float(s["start"])
        d = float(s["dur"])
        trk = 1 if i % 2 else 2
        typ = s["type"]

        # 내용 슬라이드 공통: 번호 붙은 소제목 + 오른쪽 위 출처 라벨
        if typ in ("text", "rules", "steps"):
            no = f'<span class="no">{sec_no[i-1]:02d}</span>'
            head = (f'<div class="head"><span class="bar"></span>{no}'
                    f'{esc(s.get("heading",""))}</div>')
            tag = f'<div class="docref">{docref}</div>' if docref else ""
        else:
            head = tag = ""

        if typ == "title":
            lines = "".join(f'<div class="t-line">{esc(x)}</div>' for x in s.get("lines", []))
            inner = (f'<div class="t-kicker">{esc(s.get("kicker",""))}</div>'
                     f'<div class="t-title">{lines}</div>'
                     f'<div class="t-sub">{esc(s.get("sub",""))}</div>')
            cls = "sl-title"
        elif typ == "text":
            lines = "".join(
                f'<div class="x-line">{em_span(l.get("t",""), l.get("em"))}</div>'
                for l in s.get("lines", []))
            inner = f'{tag}{head}<div class="x-wrap">{lines}</div>'
            cls = "sl-text"
        elif typ == "rules":
            items = "".join(
                '<div class="r-card">'
                f'<div class="r-main">{em_span(it.get("main",""), it.get("em"))}</div>'
                + (f'<div class="r-sub">{esc(it["sub"])}</div>' if it.get("sub") else "")
                + "</div>"
                for it in s.get("items", []))
            inner = f'{tag}{head}<div class="r-wrap">{items}</div>'
            cls = "sl-rules"
        elif typ == "steps":
            parts = []
            for j, it in enumerate(s.get("items", [])):
                if j:
                    parts.append('<div class="s-arrow">→</div>')
                parts.append('<div class="s-box">'
                             f'<div class="s-main">{esc(it.get("main",""))}</div>'
                             + (f'<div class="s-sub">{esc(it["sub"])}</div>' if it.get("sub") else "")
                             + "</div>")
            inner = f'{tag}{head}<div class="s-wrap">{"".join(parts)}</div>'
            cls = "sl-steps"
        elif typ == "end":
            inner = (f'<div class="e-line1">{esc(s.get("line1",""))}</div>'
                     f'<div class="e-line2">{em_span(s.get("line2",""), s.get("em"))}</div>'
                     f'<div class="e-cta">{esc(s.get("cta",""))}</div>')
            cls = "sl-end"
        else:
            raise SystemExit(f"모르는 슬라이드 type: {typ}")

        html.append(
            f'      <section id="s{i}" class="clip" data-start="{t0}" '
            f'data-duration="{d}" data-track-index="{trk}" data-layout-allow-overflow>\n'
            f'        <div class="fade slide {cls}" id="f{i}">{inner}</div>\n'
            f'      </section>')

        # 슬라이드 크로스페이드 (티저와 같은 방식)
        if i > 1:
            tl.append(f'      tl.fromTo("#f{i}", {{ opacity: 0 }}, '
                      f'{{ opacity: 1, duration: 0.5, ease: "power1.inOut" }}, {t0});')
        if i < len(slides):
            nxt = float(slides[i]["start"])
            tl.append(f'      tl.to("#f{i}", {{ opacity: 0, duration: 0.5, '
                      f'ease: "power1.inOut" }}, {nxt});')
            tl.append(f'      tl.set("#f{i}", {{ opacity: 0 }}, {round(nxt+0.5,2)});')

        # 내용 등장 애니메이션
        a0 = round(t0 + (0.15 if i == 1 else 0.35), 2)
        if typ == "title":
            tl.append(f'      tl.fromTo("#f{i} .t-kicker", {{ y: -18, autoAlpha: 0 }}, '
                      f'{{ y: 0, autoAlpha: 1, duration: 0.5, ease: "power2.out" }}, {a0});')
            tl.append(f'      tl.fromTo("#f{i} .t-line", {{ y: 34, autoAlpha: 0 }}, '
                      f'{{ y: 0, autoAlpha: 1, duration: 0.7, ease: "power3.out", '
                      f'stagger: 0.16 }}, {round(a0+0.2,2)});')
            tl.append(f'      tl.fromTo("#f{i} .t-sub", {{ autoAlpha: 0 }}, '
                      f'{{ autoAlpha: 1, duration: 0.6, ease: "power1.out" }}, {round(a0+0.8,2)});')
        elif typ == "end":
            tl.append(f'      tl.fromTo("#f{i} .e-line1", {{ y: 20, autoAlpha: 0 }}, '
                      f'{{ y: 0, autoAlpha: 1, duration: 0.55, ease: "power2.out" }}, {a0});')
            tl.append(f'      tl.fromTo("#f{i} .e-line2", {{ scale: 1.06, autoAlpha: 0 }}, '
                      f'{{ scale: 1, autoAlpha: 1, duration: 0.8, ease: "power2.out" }}, '
                      f'{round(a0+0.4,2)});')
            tl.append(f'      tl.fromTo("#f{i} .e-cta", {{ autoAlpha: 0, y: 14 }}, '
                      f'{{ autoAlpha: 1, y: 0, duration: 0.6, ease: "power2.out" }}, '
                      f'{round(a0+1.1,2)});')
        else:
            tl.append(f'      tl.fromTo("#f{i} .head", {{ x: -26, autoAlpha: 0 }}, '
                      f'{{ x: 0, autoAlpha: 1, duration: 0.5, ease: "power2.out" }}, {a0});')
            if docref:
                tl.append(f'      tl.fromTo("#f{i} .docref", {{ autoAlpha: 0 }}, '
                          f'{{ autoAlpha: 1, duration: 0.5, ease: "power1.out" }}, '
                          f'{round(a0+0.15,2)});')
            item_sel = {"text": ".x-line", "rules": ".r-card", "steps": ".s-box"}[typ]
            stag = {"text": 0.28, "rules": 0.4, "steps": 0.4}[typ]
            tl.append(f'      tl.fromTo("#f{i} {item_sel}", {{ y: 26, autoAlpha: 0 }}, '
                      f'{{ y: 0, autoAlpha: 1, duration: 0.55, ease: "power2.out", '
                      f'stagger: {stag} }}, {round(a0+0.25,2)});')
            if typ == "steps":
                tl.append(f'      tl.fromTo("#f{i} .s-arrow", {{ autoAlpha: 0 }}, '
                          f'{{ autoAlpha: 1, duration: 0.3, ease: "none", '
                          f'stagger: {stag} }}, {round(a0+0.55,2)});')

    # 하단 진행바
    tl.append(f'      tl.fromTo("#bar-i", {{ width: 0 }}, {{ width: {W}, '
              f'duration: {dur}, ease: "none" }}, 0);')

    # 세로(쇼츠)는 가로 여백을 줄이고 글자를 키운다 — 폰에서 손가락만 한 글씨로 읽힌다
    if vertical:
        PAD, HEAD_FS, BAR_H = 70, 52, 56
        T_LINE, T_KICK, T_SUB = 86, 34, 34
        X_LINE = 62
        R_MAIN, R_SUB, R_PAD = 52, 34, "30px 34px"
        S_DIR, S_MAIN, S_SUB = "column", 46, 30
        E_L1, E_L2, E_CTA = 46, 88, 30
    else:
        PAD, HEAD_FS, BAR_H = 170, 44, 46
        T_LINE, T_KICK, T_SUB = 92, 32, 34
        X_LINE = 58
        R_MAIN, R_SUB, R_PAD = 47, 31, "30px 40px"
        S_DIR, S_MAIN, S_SUB = "row", 44, 26
        E_L1, E_L2, E_CTA = 50, 96, 30

    return f"""<!doctype html>
<html lang="ko">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W}, height={H}" />
    <title>{esc(spec.get('title','교육영상'))}</title>
    <script src="./node_modules/gsap/dist/gsap.min.js"></script>
    <style>
      @font-face {{ font-family: "Noto Sans CJK KR"; src: local("Noto Sans CJK KR"); }}
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ width: {W}px; height: {H}px; overflow: hidden; background: {BG};
        font-family: "Noto Sans CJK KR", sans-serif; }}
      #root {{ position: relative; width: {W}px; height: {H}px; overflow: hidden; }}
      .clip {{ position: absolute; inset: 0; overflow: hidden; }}
      #bg-fill {{ position: absolute; inset: 0;
        background: radial-gradient(ellipse 70% 60% at 22% 18%, rgba(0,168,77,0.10), rgba(0,0,0,0) 60%), {BG}; }}
      #bar {{ z-index: 70; }}
      #bar-i {{ position: absolute; left: 0; bottom: 0; height: 8px; width: 0;
        background: {accent}; }}

      .fade {{ position: absolute; inset: 0; }}
      .slide {{ display: flex; flex-direction: column; justify-content: center;
        padding: 0 {PAD}px; }}

      .head {{ display: flex; align-items: center; gap: 20px; font-size: {HEAD_FS}px;
        font-weight: 800; color: {FG}; letter-spacing: 2px; margin-bottom: 48px; }}
      .head .bar {{ display: inline-block; width: 12px; height: {BAR_H}px;
        background: {accent}; border-radius: 3px; }}
      .head .no {{ font-size: 34px; font-weight: 900; color: {accent};
        letter-spacing: 1px; margin-right: -8px; }}
      .docref {{ position: absolute; top: 62px; right: 90px; font-size: 24px;
        font-weight: 600; color: {SUB}; letter-spacing: 3px; opacity: 0.85;
        border: 1px solid rgba(255,255,255,0.18); border-radius: 999px;
        padding: 9px 24px; }}
      .em {{ color: {EM}; font-weight: 900; }}

      .sl-title {{ align-items: center; text-align: center; }}
      .t-kicker {{ font-size: {T_KICK}px; font-weight: 700; color: {accent};
        letter-spacing: 7px; margin-bottom: 46px; }}
      .t-title {{ margin-bottom: 46px; }}
      .t-line {{ font-size: {T_LINE}px; font-weight: 900; color: {FG}; line-height: 1.32; }}
      .t-sub {{ font-size: {T_SUB}px; color: {SUB}; letter-spacing: 4px; }}

      .x-wrap {{ display: flex; flex-direction: column; gap: 40px; }}
      .x-line {{ font-size: {X_LINE}px; font-weight: 800; color: {FG}; line-height: 1.45; }}

      .r-wrap {{ display: flex; flex-direction: column; gap: 30px; }}
      .r-card {{ background: rgba(255,255,255,0.055); border-left: 8px solid {accent};
        border-radius: 14px; padding: {R_PAD}; }}
      .r-main {{ font-size: {R_MAIN}px; font-weight: 800; color: {FG}; line-height: 1.4; }}
      .r-sub {{ font-size: {R_SUB}px; color: {SUB}; margin-top: 12px; line-height: 1.5; }}

      .s-wrap {{ display: flex; flex-direction: {S_DIR}; align-items: stretch; gap: 18px; }}
      .s-box {{ flex: 1; background: rgba(255,255,255,0.055); border-top: 6px solid {accent};
        border-radius: 14px; padding: 34px 18px; display: flex; flex-direction: column;
        align-items: center; justify-content: center; gap: 14px; text-align: center; }}
      .s-main {{ font-size: {S_MAIN}px; font-weight: 900; color: {FG}; }}
      .s-sub {{ font-size: {S_SUB}px; color: {SUB}; line-height: 1.4; }}
      .s-arrow {{ align-self: center; font-size: 44px; color: {accent}; font-weight: 900; }}

      .sl-end {{ align-items: center; text-align: center; gap: 40px; }}
      .e-line1 {{ font-size: {E_L1}px; font-weight: 700; color: {SUB}; }}
      .e-line2 {{ font-size: {E_L2}px; font-weight: 900; color: {FG}; line-height: 1.35; }}
      .e-line2 .em {{ color: {accent}; }}
      .e-cta {{ font-size: {E_CTA}px; color: {SUB}; letter-spacing: 8px; margin-top: 14px; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0"
         data-width="{W}" data-height="{H}" data-duration="{dur}" data-fps="30">

      <section id="bg" class="clip" data-start="0" data-duration="{dur}" data-track-index="0">
        <div id="bg-fill"></div>
      </section>

      <audio id="bgm" src="bgm.wav" data-start="0" data-duration="{dur}" data-track-index="20" data-volume="1"></audio>
      <audio id="sfx" src="sfx.wav" data-start="0" data-duration="{dur}" data-track-index="21" data-volume="1"></audio>

{chr(10).join(html)}

      <section id="bar" class="clip" data-start="0" data-duration="{dur}" data-track-index="15">
        <div id="bar-i"></div>
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
