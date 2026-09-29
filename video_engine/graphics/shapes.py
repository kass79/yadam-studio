"""효과용 그림을 코드로 그린다 (구름 말풍선, 스티커, 역 표시 카드, 전동차 문, 가오리, 빛살, 반짝이).

모든 함수는 1080p 기준 크기에 unit 배율을 곱해 그리므로 본편/쇼츠/초안 해상도 어디서나 같은 비율.
외부 그림 파일이 있으면(config) 그걸 쓰고, 없을 때만 여기서 만든다.
"""
from __future__ import annotations

import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .text import hex_rgba, load_font


def _save(img: Image.Image, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    return path


# ─────────────────────────── 구름 말풍선 (속마음) ───────────────────────────

def cloud_bubble(text_img: Image.Image, *, fill: str, border: str, unit: float, trail: str = "left",
                 border_width: float = 5) -> Image.Image:
    tw, th = text_img.size
    pad_x, pad_y = int(46 * unit), int(34 * unit)
    bw, bh = tw + pad_x * 2, th + pad_y * 2
    bump = max(int(min(bw, bh) * 0.28), int(26 * unit))
    trail_h = int(70 * unit)
    edge = int(bump * 1.25 + border_width * unit + 2)
    W, H = bw + edge * 2, bh + edge * 2 + trail_h
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ox, oy = edge, edge
    # 테두리를 따라 동그라미(뭉게뭉게)를 놓는다
    circles = []
    perim_pts = []
    n_x = max(3, int(bw / (bump * 1.3)))
    n_y = max(2, int(bh / (bump * 1.3)))
    for i in range(n_x + 1):
        x = ox + bw * i / n_x
        perim_pts += [(x, oy), (x, oy + bh)]
    for j in range(1, n_y):
        y = oy + bh * j / n_y
        perim_pts += [(ox, y), (ox + bw, y)]
    rnd = random.Random(tw * 31 + th)
    for (x, y) in perim_pts:
        circles.append((x, y, bump * (0.85 + 0.3 * rnd.random())))
    bwid = max(2, int(border_width * unit))
    dr = ImageDraw.Draw(img)
    # 꼬리(생각 방울)
    tx = ox + bw * (0.22 if trail == "left" else 0.78)
    trail_c = [(tx, oy + bh + bump * 0.9, 16 * unit), (tx - (1 if trail == "left" else -1) * 26 * unit,
                                                      oy + bh + bump * 0.9 + 38 * unit, 10 * unit)]
    for layer, grow in (("border", bwid), ("fill", 0)):
        col = hex_rgba(border) if layer == "border" else hex_rgba(fill)
        for (x, y, r) in circles:
            rr = r + grow
            dr.ellipse([x - rr, y - rr, x + rr, y + rr], fill=col)
        ins = bump * 0.45
        dr.rectangle([ox + ins - grow, oy + ins - grow, ox + bw - ins + grow, oy + bh - ins + grow], fill=col)
        for (x, y, r) in trail_c:
            rr = r + grow
            dr.ellipse([x - rr, y - rr, x + rr, y + rr], fill=col)
    img.alpha_composite(text_img, (ox + pad_x, oy + pad_y))
    return img


# ─────────────────────────── 굵은 자막 스티커 ───────────────────────────

def sticker(text: str, *, font: tuple[str, int], unit: float, size: float = 84, fg: str = "#111111",
            bg: str = "#FFE14D", border: str = "#111111", angle: float = -4.0, accent: str | None = "#E8303A"
            ) -> Image.Image:
    fs = int(size * unit)
    fnt = load_font(font[0], fs, font[1])
    lines = str(text).split("\n")
    widths = [fnt.getlength(l) for l in lines]
    pad = int(34 * unit)
    lh = int(fs * 1.2)
    bw, bh = int(max(widths)) + pad * 2, lh * len(lines) + pad * 2 - int(fs * 0.1)
    b = max(3, int(7 * unit))
    sh = int(12 * unit)
    img = Image.new("RGBA", (bw + sh + b * 2, bh + sh + b * 2), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    r = int(22 * unit)
    dr.rounded_rectangle([sh + b, sh + b, sh + b + bw, sh + b + bh], radius=r, fill=(0, 0, 0, 150))
    dr.rounded_rectangle([b, b, b + bw, b + bh], radius=r, fill=hex_rgba(bg), outline=hex_rgba(border), width=b)
    if accent:
        dr.rectangle([b + pad // 2, b + bh - int(16 * unit), b + bw - pad // 2, b + bh - int(9 * unit)],
                     fill=hex_rgba(accent))
    y = b + pad - int(fs * 0.12)
    for line, w in zip(lines, widths):
        dr.text((b + (bw - w) / 2, y), line, font=fnt, fill=hex_rgba(fg))
        y += lh
    img = img.rotate(angle, resample=Image.BICUBIC, expand=True)
    return img


# ─────────────────────────── 지하철 역 표시 카드 ───────────────────────────

def station_card(to: str, frm: str | None, *, font: tuple[str, int], unit: float, line_color: str = "#00A84D",
                 header: str = "이번 역은") -> Image.Image:
    W, H = int(1180 * unit), int(360 * unit)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    r = int(40 * unit)
    dr.rounded_rectangle([0, 0, W - 1, H - 1], radius=r, fill=(250, 250, 247, 245),
                         outline=hex_rgba(line_color), width=max(2, int(6 * unit)))
    head_f = load_font(font[0], int(34 * unit), font[1])
    dr.text((int(48 * unit), int(28 * unit)), header, font=head_f, fill=(90, 90, 90, 255))
    ly = int(170 * unit)
    lw = max(4, int(22 * unit))
    x0, x1 = int(80 * unit), W - int(80 * unit)
    lc = hex_rgba(line_color)
    dr.rounded_rectangle([x0, ly - lw // 2, x1, ly + lw // 2], radius=lw // 2, fill=lc)
    # 진행 방향 화살표 (›››)
    ch = int(12 * unit)
    for k in range(3):
        cx = (x0 + x1) // 2 - int(40 * unit) + k * int(34 * unit)
        dr.line([(cx, ly - ch), (cx + ch, ly), (cx, ly + ch)], fill=(255, 255, 255, 255), width=max(2, int(5 * unit)))
    name_f = load_font(font[0], int(58 * unit), font[1])
    small_f = load_font(font[0], int(40 * unit), font[1])
    stations = []
    if frm:
        stations.append((x0 + int(150 * unit), frm, False))
        stations.append((x1 - int(150 * unit), to, True))
    else:
        stations.append(((x0 + x1) // 2, to, True))
    for (cx, name, cur) in stations:
        rr = int((34 if cur else 24) * unit)
        dr.ellipse([cx - rr, ly - rr, cx + rr, ly + rr], fill=(255, 255, 255, 255), outline=lc,
                   width=max(3, int((12 if cur else 8) * unit)))
        if cur:
            ri = int(12 * unit)
            dr.ellipse([cx - ri, ly - ri, cx + ri, ly + ri], fill=lc)
        f = name_f if cur else small_f
        label = name
        w = f.getlength(label)
        col = (20, 20, 20, 255) if cur else (140, 140, 140, 255)
        dr.text((cx - w / 2, ly + rr + int(18 * unit)), label, font=f, fill=col)
    return img


# ─────────────────────────── 전동차 출입문 ───────────────────────────

def door_panel(w: int, h: int, *, unit: float, side: str, body: str = "#C9CED6", glass: str = "#1B2A3AB4",
               edge: str = "#1A1A1A", decal: str = "#F2C200") -> Image.Image:
    """side='left' 이면 오른쪽 가장자리가 닫히는 쪽(고무 패킹)."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    arr = np.zeros((h, w, 4), np.uint8)
    base = np.array(hex_rgba(body), np.float32)
    shade = np.linspace(1.06, 0.86, w, dtype=np.float32)
    if side == "right":
        shade = shade[::-1]
    arr[..., :3] = np.clip(base[:3][None, None, :] * shade[None, :, None], 0, 255).astype(np.uint8)
    arr[..., 3] = 255
    img = Image.fromarray(arr, "RGBA")
    dr = ImageDraw.Draw(img)
    m = int(w * 0.16)
    gx0, gx1 = m, w - m
    gy0, gy1 = int(h * 0.14), int(h * 0.52)
    dr.rounded_rectangle([gx0, gy0, gx1, gy1], radius=int(28 * unit), fill=hex_rgba(glass),
                         outline=(90, 95, 105, 255), width=max(2, int(8 * unit)))
    # 유리 반사
    dr.line([(gx0 + int(30 * unit), gy1 - int(40 * unit)), (gx0 + int(140 * unit), gy0 + int(30 * unit))],
            fill=(255, 255, 255, 70), width=max(2, int(18 * unit)))
    ew = max(3, int(22 * unit))
    ex = w - ew if side == "left" else 0
    dr.rectangle([ex, 0, ex + ew, h], fill=hex_rgba(edge))
    # 노란 안전 스티커
    cy = int(h * 0.68)
    cr = int(30 * unit)
    cx = w // 2
    dr.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=hex_rgba(decal), outline=(40, 40, 40, 255),
               width=max(1, int(4 * unit)))
    dr.rectangle([0, h - int(20 * unit), w, h], fill=(70, 72, 78, 255))
    return img


# ─────────────────────────── 가오리 실루엣 ───────────────────────────

def manta(width: int, *, color: str = "#1E2A44E6", unit: float = 1.0, flap: float = 0.0) -> Image.Image:
    """위에서 본 쥐가오리 실루엣. 머리가 왼쪽(왼쪽으로 헤엄침), 날개는 위아래, 꼬리는 오른쪽.
    flap(-1~1)은 날갯짓 정도 (날개 끝을 앞뒤로 휜다)."""
    s = 4  # 슈퍼샘플링
    W = width * s
    H = int(width * 0.9) * s
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    cy = H * 0.5
    head_x, tail_x = W * 0.10, W * 0.58
    tip_x = W * (0.50 + 0.06 * flap)

    def wing(sign: int) -> list[tuple[float, float]]:
        tip_y = cy + sign * H * 0.47
        pts = []
        # 앞날개: 머리 → 날개끝 (볼록한 곡선)
        for i in range(0, 41):
            u = i / 40
            x = head_x + (tip_x - head_x) * u
            y = cy + sign * (H * 0.10 + (H * 0.37) * (u ** 0.75))
            pts.append((x, y))
        # 뒷날개: 날개끝 → 꼬리 뿌리 (오목한 곡선)
        for i in range(1, 41):
            u = i / 40
            x = tip_x + (tail_x - tip_x) * u
            y = tip_y - sign * (H * 0.47 - H * 0.07) * (1 - (1 - u) ** 2.2)
            pts.append((x, y))
        return pts

    top = wing(-1)
    bot = wing(1)
    outline = [(head_x, cy)] + top + list(reversed(bot))
    dr.polygon(outline, fill=hex_rgba(color))
    # 머리 쪽 두 뿔(두鰭)
    for sgn in (-1, 1):
        dr.polygon([(head_x + W * 0.03, cy + sgn * H * 0.04), (head_x - W * 0.06, cy + sgn * H * 0.09),
                    (head_x + W * 0.02, cy + sgn * H * 0.12)], fill=hex_rgba(color))
    # 꼬리
    dr.polygon([(tail_x - W * 0.02, cy - H * 0.02), (W * 0.98, cy - H * 0.004), (W * 0.98, cy + H * 0.004),
                (tail_x - W * 0.02, cy + H * 0.02)], fill=hex_rgba(color))
    # 등 무늬 (살짝 밝은 선)
    dr.arc([W * 0.18, cy - H * 0.2, W * 0.5, cy + H * 0.2], 120, 240, fill=(255, 255, 255, 55),
           width=max(2, int(H * 0.012)))
    return img.resize((width, H // s), Image.LANCZOS)


# ─────────────────────────── 방사형 빛 ───────────────────────────

def radial_rays(size: int, *, n: int = 18, color: str = "#FFE38A", strength: float = 0.55) -> Image.Image:
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    c = (size - 1) / 2
    dx, dy = xx - c, yy - c
    ang = np.arctan2(dy, dx)
    rad = np.sqrt(dx * dx + dy * dy) / (size / 2)
    wedge = (np.cos(ang * n) > 0.25).astype(np.float32)
    soft = np.clip(1.0 - rad, 0, 1) ** 1.3
    core = np.clip(1.0 - rad * 4, 0, 1)
    alpha = np.clip(wedge * soft * strength + core * 0.8, 0, 1)
    col = np.array(hex_rgba(color)[:3], np.float32)
    arr = np.zeros((size, size, 4), np.uint8)
    arr[..., :3] = col
    arr[..., 3] = (alpha * 255).astype(np.uint8)
    return Image.fromarray(arr, "RGBA").filter(ImageFilter.GaussianBlur(max(1, size // 400)))


# ─────────────────────────── 반짝이 파티클 ───────────────────────────

def sparkle_sequence(out_dir: Path, W: int, H: int, *, frames: int = 24, count: int = 38, seed: int = 7,
                     colors=("#FFFFFF", "#FFD6EC", "#FFF3A6"), unit: float = 1.0) -> str:
    """반짝이 루프 PNG 시퀀스를 만들고 ffmpeg용 패턴 경로를 돌려준다."""
    out_dir.mkdir(parents=True, exist_ok=True)
    pattern = out_dir / "sp_%03d.png"
    if (out_dir / f"sp_{frames - 1:03d}.png").exists():
        return str(pattern)
    rnd = random.Random(seed)
    parts = []
    for _ in range(count):
        parts.append((rnd.uniform(0.03, 0.97) * W, rnd.uniform(0.04, 0.96) * H, rnd.uniform(10, 34) * unit,
                      rnd.random(), rnd.choice(colors), rnd.uniform(-0.6, -0.15) * unit))
    for f in range(frames):
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dr = ImageDraw.Draw(img)
        for (x, y, r, ph, col, vy) in parts:
            k = math.sin(2 * math.pi * (f / frames + ph))
            if k <= 0:
                continue
            rr = r * (0.4 + 0.6 * k)
            y2 = y + vy * f * 3
            c = hex_rgba(col)
            a = int(255 * k)
            glow = (c[0], c[1], c[2], int(a * 0.25))
            dr.ellipse([x - rr * 0.7, y2 - rr * 0.7, x + rr * 0.7, y2 + rr * 0.7], fill=glow)
            thin = rr * 0.16
            dr.polygon([(x - rr, y2), (x - thin, y2 - thin), (x, y2 - rr), (x + thin, y2 - thin), (x + rr, y2),
                        (x + thin, y2 + thin), (x, y2 + rr), (x - thin, y2 + thin)], fill=(c[0], c[1], c[2], a))
        img.save(out_dir / f"sp_{f:03d}.png")
    return str(pattern)


def solid(W: int, H: int, color: str) -> Image.Image:
    return Image.new("RGBA", (W, H), hex_rgba(color))
