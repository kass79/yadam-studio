"""자막/스티커용 글자 그리기 (Pillow).

자막을 ffmpeg subtitles(libass) 대신 PNG로 그려 올리는 이유:
  - 윈도우에서 subtitles 필터의 폰트 폴더/경로(C\\:) 이스케이프 문제를 원천 차단
  - 단어별 색(강조 노랑, 사투리 주황), 구름 말풍선, 스티커를 한 가지 방식으로 처리
표기법:  *강조*  → 강조색 / [사투리] → 사투리색 / 줄바꿈은 실제 줄바꿈(\\n)
"""
from __future__ import annotations

import re
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFilter, ImageFont

Span = tuple[str, str]   # (글자, 색 역할: normal | em | dialect | 직접 색 "#RRGGBB")

_MARK = re.compile(r"(\*[^*]+\*|\[[^\]]+\])")


def parse_markup(text: str, keywords: dict[str, str] | None = None) -> list[list[Span]]:
    """'아따 *진짜* [뭇나]?' → 줄별 span 리스트. keywords={단어: 역할} 은 자동 색칠."""
    lines: list[list[Span]] = []
    for raw_line in str(text).split("\n"):
        spans: list[Span] = []
        for part in _MARK.split(raw_line):
            if not part:
                continue
            if part.startswith("*") and part.endswith("*") and len(part) > 2:
                spans.append((part[1:-1], "em"))
            elif part.startswith("[") and part.endswith("]") and len(part) > 2:
                spans.append((part[1:-1], "dialect"))
            else:
                spans.extend(_auto_keywords(part, keywords or {}))
        lines.append(spans)
    return lines


def _auto_keywords(text: str, keywords: dict[str, str]) -> list[Span]:
    if not keywords:
        return [(text, "normal")]
    pat = re.compile("(" + "|".join(re.escape(k) for k in sorted(keywords, key=len, reverse=True)) + ")")
    out = []
    for part in pat.split(text):
        if part:
            out.append((part, keywords.get(part, "normal")))
    return out


def strip_markup(text: str) -> str:
    return re.sub(r"\*([^*]+)\*", r"\1", re.sub(r"\[([^\]]+)\]", r"\1", str(text)))


@lru_cache(maxsize=64)
def load_font(path: str, size: int, index: int = 0) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size, index=index)
    except OSError:
        return ImageFont.truetype(path, size)


def wrap_spans(lines: list[list[Span]], max_chars: int) -> list[list[Span]]:
    """띄어쓰기 단위로 줄바꿈. 두 줄이 되면 길이를 비슷하게 맞춘다."""
    out: list[list[Span]] = []
    for spans in lines:
        words: list[list[Span]] = [[]]
        for txt, role in spans:
            parts = re.split(r"( )", txt)
            for part in parts:
                if part == " ":
                    words.append([])
                elif part:
                    words[-1].append((part, role))
        words = [w for w in words if w]
        total = sum(len(t) for w in words for t, _ in w) + max(0, len(words) - 1)
        if total <= max_chars or len(words) <= 1:
            out.append(_join_words(words))
            continue
        n_lines = -(-total // max_chars)
        target = total / n_lines
        cur: list[list[Span]] = []
        cur_len = 0
        for w in words:
            wl = sum(len(t) for t, _ in w)
            if cur and cur_len + 1 + wl > target + 2:
                out.append(_join_words(cur))
                cur, cur_len = [], 0
            cur.append(w)
            cur_len += wl + (1 if cur_len else 0)
        if cur:
            out.append(_join_words(cur))
    return out


def _join_words(words: list[list[Span]]) -> list[Span]:
    line: list[Span] = []
    for i, w in enumerate(words):
        if i:
            line.append((" ", "normal"))
        line.extend(w)
    return line


def hex_rgba(c: str | None, default=(255, 255, 255, 255)) -> tuple[int, int, int, int]:
    if not c:
        return default
    c = str(c).lstrip("#")
    if len(c) in (3, 4):
        c = "".join(ch * 2 for ch in c)
    if len(c) == 6:
        c += "FF"
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4, 6))  # type: ignore[return-value]


def render_lines(lines: list[list[Span]], *, font: tuple[str, int], size: int, colors: dict[str, str],
                 stroke: str | None = "#000000", stroke_width: int = 0, line_spacing: float = 1.2,
                 align: str = "center", shadow: int = 0, pad: int = 0,
                 box: str | None = None, box_radius: int = 0, extra_lines: list[tuple] | None = None
                 ) -> Image.Image:
    """span 줄들을 투명 PNG로. extra_lines=[(글자, 폰트, 크기, 색)] 는 아래에 작게 붙는 주석 줄."""
    fnt = load_font(font[0], size, font[1])
    sw = int(stroke_width)
    rows = []   # (items, width, height, font, stroke)
    for line in lines:
        w = sum(fnt.getlength(t) for t, _ in line)
        rows.append(([(t, colors.get(r, r)) for t, r in line], w, size, fnt, sw))
    for txt, f2, s2, col in extra_lines or []:
        ff = load_font(f2[0], s2, f2[1])
        rows.append(([(txt, col)], ff.getlength(txt), s2, ff, max(1, int(sw * s2 / max(size, 1)))))
    gap = [int(r[2] * (line_spacing - 1.0)) for r in rows]
    margin = sw + shadow + pad + 4
    W = int(max(r[1] for r in rows)) + margin * 2
    H = int(sum(r[2] for r in rows) + sum(gap[:-1])) + margin * 2 + int(size * 0.25)
    img = Image.new("RGBA", (max(W, 2), max(H, 2)), (0, 0, 0, 0))
    if box:
        ImageDraw.Draw(img).rounded_rectangle([0, 0, W - 1, H - 1], radius=box_radius, fill=hex_rgba(box))

    def draw_pass(dr: ImageDraw.ImageDraw, mode: str, dx: int = 0, dy: int = 0):
        y = margin
        for i, (items, w, h, f, rsw) in enumerate(rows):
            if align == "center":
                x = (W - w) / 2
            elif align == "right":
                x = W - margin - w
            else:
                x = margin
            for t, col in items:
                if mode == "stroke" and rsw > 0 and stroke:
                    dr.text((x + dx, y + dy), t, font=f, fill=hex_rgba(stroke), stroke_width=rsw,
                            stroke_fill=hex_rgba(stroke))
                elif mode == "shadow":
                    dr.text((x + dx, y + dy), t, font=f, fill=(0, 0, 0, 170), stroke_width=rsw,
                            stroke_fill=(0, 0, 0, 170))
                elif mode == "fill":
                    dr.text((x, y), t, font=f, fill=hex_rgba(col))
                x += f.getlength(t)
            y += h + gap[i]

    if shadow:
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw_pass(ImageDraw.Draw(sh), "shadow", shadow, shadow)
        sh = sh.filter(ImageFilter.GaussianBlur(max(1, shadow)))
        img.alpha_composite(sh)
    dr = ImageDraw.Draw(img)
    draw_pass(dr, "stroke")
    draw_pass(dr, "fill")
    return img
