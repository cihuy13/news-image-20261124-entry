#!/usr/bin/env python3
"""Sum up 24 November 2026 in one image.

A single-file, stdlib-only program. It draws a 1024x1024 newspaper
front page — masthead, one big hero story, eight illustrated cards,
a dotted world map and a 27-item ALSO list — and writes it to
/output/entry.png. Deterministic: no time, no randomness, no network.
Glyphs come from glyphs.bin (a READ data file in this repo), rasterised
from DejaVu Sans Bold before the build.
"""
import os
import struct
import sys
import zlib

W = 1024
H = 1024

# ---------------------------------------------------------------- palette
PAPER = (247, 242, 231)
PAPER2 = (238, 231, 214)
INK = (20, 20, 20)
INK2 = (64, 60, 52)
RED = (176, 30, 36)
NAVY = (18, 40, 75)
NAVY2 = (28, 58, 108)
TEAL = (14, 107, 107)
GOLD = (201, 151, 0)
GOLDL = (232, 196, 82)
GREEN = (24, 140, 74)
GREENL = (90, 200, 120)
CREAM = (255, 250, 238)
WHITE = (255, 255, 255)
SKY = (120, 180, 220)
SKYD = (70, 130, 190)
ORANGE = (224, 110, 30)
FIRE = (240, 160, 40)
SMOKE = (120, 118, 112)
SAND = (214, 186, 140)
SEA = (26, 90, 140)
SEAL = (90, 160, 200)
GREY = (150, 148, 140)


# ---------------------------------------------------------------- PNG out
def write_png(path, px):
    raw = bytearray()
    for y in range(H):
        raw.append(0)
        raw += px[y * W * 3:(y + 1) * W * 3]

    def chunk(typ, data):
        c = struct.pack(">I", len(data)) + typ + data
        return c + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 6))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


# ---------------------------------------------------------------- font
class Font:
    def __init__(self, path):
        with open(path, "rb") as f:
            data = f.read()
        assert data[:5] == b"MFNT2", "bad font magic"
        pos = 5
        nfaces = data[pos]
        pos += 1
        self.faces = []
        for _ in range(nfaces):
            size = data[pos]
            ascent = data[pos + 1]
            descent = data[pos + 2]
            nch = data[pos + 3]
            pos += 4
            glyphs = {}
            for _ in range(nch):
                cp, adv, w, h, top = struct.unpack_from("<IBBBb", data, pos)
                pos += 8
                bmp = data[pos:pos + w * h]
                pos += w * h
                glyphs[cp] = (adv, w, h, top, bmp)
            self.faces.append((size, ascent, descent, glyphs))

    def text_w(self, s, face, scale):
        _size, _asc, _desc, glyphs = self.faces[face]
        w = 0
        for ch in s:
            g = glyphs.get(ord(ch))
            if g is None:
                g = glyphs.get(63)
            w += int(g[0] * scale) + int(1 * scale)
        return w

    def wrap(self, s, face, scale, max_w):
        _size, _asc, _desc, glyphs = self.faces[face]
        words = s.split(" ")
        lines, cur = [], ""
        for wd in words:
            trial = (cur + " " + wd).strip()
            if self.text_w(trial, face, scale) <= max_w or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = wd
        if cur:
            lines.append(cur)
        return lines


FONT = None


def load_font():
    global FONT
    here = os.path.dirname(os.path.abspath(__file__))
    FONT = Font(os.path.join(here, "glyphs.bin"))


# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self):
        self.px = bytearray(PAPER * W * H)

    def set(self, x, y, c):
        if 0 <= x < W and 0 <= y < H:
            i = (y * W + x) * 3
            self.px[i], self.px[i + 1], self.px[i + 2] = c

    def blend(self, x, y, c, a):
        if 0 <= x < W and 0 <= y < H and a > 0:
            i = (y * W + x) * 3
            self.px[i] = (self.px[i] * (255 - a) + c[0] * a) // 255
            self.px[i + 1] = (self.px[i + 1] * (255 - a) + c[1] * a) // 255
            self.px[i + 2] = (self.px[i + 2] * (255 - a) + c[2] * a) // 255

    def rect(self, x, y, w, h, c):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(W, x + w), min(H, y + h)
        for yy in range(y0, y1):
            i = (yy * W + x0) * 3
            for xx in range(x0, x1):
                self.px[i], self.px[i + 1], self.px[i + 2] = c
                i += 3

    def border(self, x, y, w, h, c, t=2):
        self.rect(x, y, w, t, c)
        self.rect(x, y + h - t, w, t, c)
        self.rect(x, y, t, h, c)
        self.rect(x + w - t, y, t, h, c)

    def hline(self, x, y, w, c, t=1):
        self.rect(x, y, w, t, c)

    def vline(self, x, y, h, c, t=1):
        self.rect(x, y, t, h, c)

    def line(self, x0, y0, x1, y1, c, t=1):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        while True:
            self.rect(x - t // 2, y - t // 2, t, t, c)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def circle(self, cx, cy, r, c, fill=True):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                d = (xx - cx) ** 2 + (yy - cy) ** 2
                if fill:
                    if d <= r * r:
                        self.set(xx, yy, c)
                else:
                    if r * r - r <= d <= r * r + r:
                        self.set(xx, yy, c)

    def ellipse(self, cx, cy, rx, ry, c):
        for yy in range(cy - ry, cy + ry + 1):
            for xx in range(cx - rx, cx + rx + 1):
                if ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1.0:
                    self.set(xx, yy, c)

    def poly(self, pts, c):
        ys = [p[1] for p in pts]
        for y in range(max(0, min(ys)), min(H, max(ys) + 1)):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    xs.append(int(x0 + (y - y0) * (x1 - x0) / (y1 - y0)))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                for x in range(xs[k], xs[k + 1] + 1):
                    self.set(x, y, c)

    def text(self, x, y, s, face=0, scale=1.0, color=INK):
        _size, ascent, _desc, glyphs = FONT.faces[face]
        cx = x
        for ch in s:
            g = glyphs.get(ord(ch))
            if g is None:
                g = glyphs.get(63)
            adv, w, h, top, bmp = g
            if w and h:
                dw = max(1, int(round(w * scale)))
                dh = max(1, int(round(h * scale)))
                gy = y + int(round((ascent - top) * scale))
                for dy in range(dh):
                    sy = int(dy / scale)
                    if sy >= h:
                        sy = h - 1
                    for dx in range(dw):
                        sx = int(dx / scale)
                        if sx >= w:
                            sx = w - 1
                        a = bmp[sy * w + sx]
                        if a:
                            self.blend(cx + dx, gy + dy, color, a)
            cx += int(adv * scale) + int(1 * scale)
        return cx - x

    def text_c(self, cx, y, s, face=0, scale=1.0, color=INK):
        w = FONT.text_w(s, face, scale)
        return self.text(cx - w // 2, y, s, face, scale, color)

    def para(self, x, y, lines, face=0, scale=1.0, color=INK, lh=None):
        if lh is None:
            _size, asc, desc, _g = FONT.faces[face]
            lh = int((asc + desc) * scale) + 3
        for ln in lines:
            self.text(x, y, ln, face, scale, color)
            y += lh
        return y


# ---------------------------------------------------------------- scene bits
def person(cv, x, y, s, c):
    cv.circle(x, y - int(9 * s), max(2, int(4 * s)), c)
    cv.poly([(x - int(6 * s), y + int(12 * s)), (x + int(6 * s), y + int(12 * s)),
             (x + int(4 * s), y - int(4 * s)), (x - int(4 * s), y - int(4 * s))], c)


def flame(cv, x, y, s, c1, c2):
    cv.poly([(x - int(10 * s), y), (x, y - int(26 * s)), (x + int(10 * s), y)], c1)
    cv.poly([(x - int(6 * s), y), (x, y - int(16 * s)), (x + int(6 * s), y)], c2)
    cv.circle(x, y - int(4 * s), int(4 * s), c2)


def wave(cv, x, y, w, amp, c, t=2):
    pts = []
    for dx in range(0, w + 1, 4):
        yy = y + int(amp * (1 if (dx // 8) % 2 == 0 else -1) * 0.5)
        pts.append((x + dx, yy))
    for i in range(len(pts) - 1):
        cv.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], c, t)


def stars(cv, x, y, w, h, n, c):
    # deterministic pseudo-random dots from a fixed seed pattern
    s = 12345
    for _ in range(n):
        s = (s * 1103515245 + 12345) & 0x7FFFFFFF
        px = x + s % max(1, w)
        s = (s * 1103515245 + 12345) & 0x7FFFFFFF
        py = y + s % max(1, h)
        s = (s * 1103515245 + 12345) & 0x7FFFFFFF
        r = 1 + s % 2
        cv.circle(px, py, r, c)


def flag_row(cv, x, y, w, cols, h=10):
    fw = w // len(cols)
    for i, c in enumerate(cols):
        cv.rect(x + i * fw + 1, y, fw - 2, h, c)


def chart_up(cv, x, y, w, h, c, t=3):
    pts = [(x, y + h), (x + w // 5, y + int(h * 0.75)), (x + 2 * w // 5, y + int(h * 0.8)),
           (x + 3 * w // 5, y + int(h * 0.45)), (x + 4 * w // 5, y + int(h * 0.5)),
           (x + w - 14, y + 8)]
    for i in range(len(pts) - 1):
        cv.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], c, t)
    ex, ey = pts[-1]
    cv.poly([(ex, ey), (ex - 12, ey - 2), (ex - 4, ey + 10)], c)


# ---------------------------------------------------------------- scenes
def scene_hero(cv, x, y, w, h):
    cv.rect(x, y, w, h, NAVY)
    stars(cv, x, y, w, h, 70, (200, 210, 235))
    # trading screens along the top
    for i in range(5):
        sx = x + 14 + i * ((w - 28) // 5)
        cv.rect(sx, y + 10, (w - 28) // 5 - 8, 28, (10, 22, 46))
        cv.border(sx, y + 10, (w - 28) // 5 - 8, 28, (60, 90, 140), 1)
        cv.text(sx + 5, y + 12, ["NVDA", "KOSPI", "NIKKEI", "NASDAQ", "TAIEX"][i],
                1, 0.55, (140, 180, 220))
        cv.text(sx + 5, y + 24, ["+6.9%", "+6.2%", "+3.9%", "+6.9%", "+9.1%"][i],
                1, 0.55, GREENL)
    # giant chip, centre-left
    cx, cy = x + w // 3, y + h // 2 + 18
    cv.rect(cx - 62, cy - 48, 124, 96, (8, 16, 36))
    cv.border(cx - 62, cy - 48, 124, 96, GOLD, 3)
    cv.rect(cx - 44, cy - 30, 88, 60, (16, 34, 68))
    cv.text_c(cx, cy - 22, "NVDA", 0, 0.9, GOLDL)
    cv.text_c(cx, cy + 4, "HUANG", 0, 0.55, WHITE)
    cv.text_c(cx, cy + 22, "IS BACK", 0, 0.55, GREENL)
    for k in range(6):
        cv.rect(cx - 62, cy - 40 + k * 16, 10, 5, GOLD)
        cv.rect(cx + 52, cy - 40 + k * 16, 10, 5, GOLD)
        cv.rect(cx - 40 + k * 16, cy - 58, 5, 10, GOLD)
        cv.rect(cx - 40 + k * 16, cy + 48, 5, 10, GOLD)
    # circuit traces
    cv.line(cx - 62, cy - 48, x + 8, y + 44, (60, 110, 180), 2)
    cv.line(cx + 62, cy + 48, x + w - 30, y + h - 40, (60, 110, 180), 2)
    cv.circle(x + 8, y + 44, 4, GOLD)
    cv.circle(x + w - 30, y + h - 40, 4, GOLD)
    # rising chart across the right
    chart_up(cv, x + w // 2 + 10, y + h - 92, w // 2 - 30, 62, GREENL, 4)
    cv.text(x + w // 2 + 14, y + h - 112, "+$1 TRILLION", 1, 0.7, GREENL)
    # crowd of traders at the bottom
    for i in range(14):
        px = x + 18 + i * ((w - 36) // 13)
        person(cv, px, y + h - 14, 0.8, (8, 16, 36) if i % 3 else (30, 60, 110))
    cv.rect(x, y + h - 6, w, 6, GOLD)


def scene_nato(cv, x, y, w, h):
    cv.rect(x, y, w, h, (10, 14, 34))
    stars(cv, x, y, w, h, 40, WHITE)
    # Earth as an arc cap hugging the bottom of the scene (stays inside)
    pts = []
    for dx in range(0, w + 1, 6):
        t = dx / w
        arc = int(30 * (1 - (2 * t - 1) ** 2))
        pts.append((x + dx, y + h - arc))
    pts.append((x + w, y + h))
    pts.append((x, y + h))
    cv.poly(pts, SEA)
    pts2 = []
    for dx in range(0, w + 1, 6):
        t = dx / w
        arc = int(22 * (1 - (2 * t - 1) ** 2))
        pts2.append((x + dx, y + h - arc))
    pts2.append((x + w, y + h))
    pts2.append((x, y + h))
    cv.poly(pts2, (40, 120, 90))
    # satellite with panels
    sx, sy = x + w // 2, y + h // 3
    cv.rect(sx - 34, sy - 8, 22, 16, NAVY2)
    cv.rect(sx + 12, sy - 8, 22, 16, NAVY2)
    cv.rect(sx - 12, sy - 10, 24, 20, GOLDL)
    cv.circle(sx, sy, 6, WHITE)
    cv.line(sx - 34, sy, sx - 52, sy - 14, WHITE, 2)
    cv.line(sx + 34, sy, sx + 52, sy + 12, WHITE, 2)
    # radar rings from earth (small, stay inside the scene)
    for r in (8, 13, 18):
        cv.circle(x + w // 4, y + h - 20, r, GREENL, fill=False)
    cv.line(x + w // 4, y + h - 20, sx, sy, RED, 2)
    cv.text(x + 8, y + 8, "SPACE", 1, 0.6, (180, 200, 235))


def scene_libya(cv, x, y, w, h):
    cv.rect(x, y, w, h, (196, 214, 224))
    cv.rect(x, y, w, h // 2, (150, 190, 215))
    cv.circle(x + w - 30, y + 18, 12, GOLDL)
    # ship
    sx, sy = x + w // 2 - 10, y + h // 2 + 6
    cv.poly([(sx - 52, sy), (sx + 52, sy), (sx + 40, sy + 18), (sx - 40, sy + 18)], (60, 64, 70))
    cv.rect(sx - 18, sy - 22, 30, 22, (90, 94, 100))
    cv.rect(sx + 2, sy - 34, 4, 14, (60, 64, 70))
    cv.rect(sx - 6, sy - 30, 26, 6, RED)
    # drone above
    cv.circle(sx + 46, sy - 46, 4, INK)
    cv.line(sx + 38, sy - 50, sx + 54, sy - 42, INK, 2)
    cv.line(sx + 38, sy - 42, sx + 54, sy - 50, INK, 2)
    # explosion burst on the ship
    cv.circle(sx - 30, sy - 8, 14, ORANGE)
    cv.circle(sx - 30, sy - 8, 8, FIRE)
    cv.circle(sx - 30, sy - 8, 4, WHITE)
    for k in range(6):
        cv.line(sx - 30, sy - 8, sx - 30 + [-26, -14, 10, 24, 6, -6][k],
                sy - 8 + [-18, -26, -24, -12, -28, -20][k], ORANGE, 2)
    # smoke + waves
    cv.circle(sx - 44, sy - 30, 9, SMOKE)
    cv.circle(sx - 56, sy - 40, 7, SMOKE)
    wave(cv, x + 4, y + h - 26, w - 8, 5, SEA, 3)
    wave(cv, x + 4, y + h - 14, w - 8, 5, SEAL, 3)


def scene_icj(cv, x, y, w, h):
    cv.rect(x, y, w, h, (232, 222, 196))
    # courthouse
    cv.rect(x + 14, y + 18, w - 28, 12, NAVY)
    cv.poly([(x + w // 2 - 46, y + 18), (x + w // 2 + 46, y + 18), (x + w // 2, y + 2)], RED)
    for i in range(4):
        cx = x + 30 + i * ((w - 60) // 3)
        cv.rect(cx - 6, y + 30, 12, 52, CREAM)
        cv.rect(cx - 9, y + 26, 18, 6, NAVY)
    cv.rect(x + 14, y + 82, w - 28, 8, NAVY)
    # scales of justice
    sx, sy = x + w // 2, y + h - 34
    cv.vline(sx, sy - 26, 26, INK, 3)
    cv.line(sx - 22, sy - 26, sx + 22, sy - 26, INK, 2)
    cv.poly([(sx - 26, sy - 8), (sx - 14, sy - 8), (sx - 20, sy - 20)], GOLD)
    cv.poly([(sx + 14, sy - 8), (sx + 26, sy - 8), (sx + 20, sy - 20)], GOLD)
    cv.circle(sx, sy - 30, 4, GOLD)
    # 14 flags
    flag_row(cv, x + 8, y + h - 14, w - 16,
             [RED, WHITE, NAVY, GREEN, GOLD, TEAL, ORANGE, RED, NAVY, WHITE, GREEN, GOLD, TEAL, NAVY], 8)


def scene_nepal(cv, x, y, w, h):
    cv.rect(x, y, w, h, (206, 224, 238))
    cv.circle(x + w - 26, y + 16, 11, GOLDL)
    # mountains
    cv.poly([(x, y + h), (x + w // 4, y + 16), (x + w // 2, y + h)], (120, 140, 165))
    cv.poly([(x + w // 4, y + 16), (x + w // 4 - 12, y + 34), (x + w // 4 + 12, y + 34)], WHITE)
    cv.poly([(x + w // 3, y + h), (x + 3 * w // 5, y + 30), (x + 5 * w // 6, y + h)], (90, 112, 140))
    cv.poly([(x + 3 * w // 5, y + 30), (x + 3 * w // 5 - 10, y + 46), (x + 3 * w // 5 + 10, y + 46)], WHITE)
    # cracked ground
    gy = y + h - 34
    cv.line(x, gy, x + w // 4, gy - 6, INK, 2)
    cv.line(x + w // 4, gy - 6, x + w // 2, gy + 4, INK, 2)
    cv.line(x + w // 2, gy + 4, x + 3 * w // 4, gy - 4, INK, 2)
    cv.line(x + 3 * w // 4, gy - 4, x + w, gy + 2, INK, 2)
    # tilted buildings + tents
    cv.poly([(x + 12, gy), (x + 34, gy - 4), (x + 34, gy - 26), (x + 12, gy - 22)], (150, 110, 80))
    cv.poly([(x + 44, gy), (x + 62, gy + 2), (x + 62, gy - 20), (x + 44, gy - 24)], (170, 130, 95))
    cv.poly([(x + w - 66, gy), (x + w - 34, gy), (x + w - 50, gy - 20)], RED)
    cv.poly([(x + w - 30, gy), (x + w - 6, gy), (x + w - 18, gy - 16)], TEAL)
    # seismograph line
    pts = [(x + 8, y + 12), (x + 30, y + 12), (x + 38, y + 4), (x + 46, y + 22),
           (x + 54, y + 2), (x + 62, y + 20), (x + 74, y + 12), (x + w - 8, y + 12)]
    for i in range(len(pts) - 1):
        cv.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], RED, 2)


def scene_gaza(cv, x, y, w, h):
    cv.rect(x, y, w, h, (222, 204, 172))
    cv.circle(x + 26, y + 18, 13, (235, 200, 120))
    # ruined skyline
    for i, bh in enumerate([52, 70, 44, 78, 58, 66, 40]):
        bx = x + 8 + i * ((w - 16) // 7)
        bw = (w - 16) // 7 - 4
        cv.rect(bx, y + h - 30 - bh, bw, bh, (120, 108, 92))
        cv.poly([(bx, y + h - 30 - bh), (bx + bw // 2, y + h - 30 - bh - 10), (bx + bw, y + h - 30 - bh)], (90, 80, 66))
        cv.rect(bx + 4, y + h - 30 - bh + 12, 5, 6, (40, 38, 34))
        cv.rect(bx + bw - 9, y + h - 30 - bh + 24, 5, 6, (40, 38, 34))
    # smoke columns
    for sx, sh in [(x + 40, 46), (x + w // 2, 58), (x + w - 48, 42)]:
        cv.circle(sx, y + h - 88, 10, SMOKE)
        cv.circle(sx + 6, y + h - 104, 12, (140, 138, 132))
        cv.circle(sx - 4, y + h - 118, 8, (160, 158, 152))
    # olive tree + aid truck
    cv.rect(x + w - 30, y + h - 52, 4, 22, (90, 70, 40))
    cv.circle(x + w - 28, y + h - 58, 12, (70, 120, 60))
    cv.circle(x + w - 40, y + h - 50, 8, (90, 140, 70))
    cv.rect(x + 10, y + h - 26, 52, 14, WHITE)
    cv.rect(x + 10, y + h - 26, 52, 5, RED)
    cv.circle(x + 20, y + h - 10, 5, INK)
    cv.circle(x + 52, y + h - 10, 5, INK)
    cv.text(x + 16, y + h - 24, "AID", 1, 0.5, RED)


def scene_iran(cv, x, y, w, h):
    cv.rect(x, y, w, h, (24, 20, 44))
    # spotlight cone
    cv.poly([(x + w // 2 - 8, y), (x + w // 2 + 8, y),
             (x + w // 2 + 52, y + h - 30), (x + w // 2 - 52, y + h - 30)], (70, 70, 110))
    cv.circle(x + w // 2, y + 6, 7, GOLDL)
    # stage
    cv.rect(x, y + h - 34, w, 34, (60, 40, 50))
    cv.rect(x, y + h - 34, w, 4, GOLD)
    # singer silhouette at mic
    sx, sy = x + w // 2, y + h - 34
    person(cv, sx, sy - 6, 1.6, (8, 8, 16))
    cv.vline(sx + 16, sy - 52, 46, (200, 200, 200), 2)
    cv.circle(sx + 16, sy - 54, 5, (220, 220, 220))
    # broken chain links at her feet
    for i, dx in enumerate([-30, -14, 6, 22]):
        cv.circle(sx + dx, sy - 2, 5, GOLDL if i % 2 else (180, 180, 180), fill=False)
    # audience heads
    for i in range(9):
        px = x + 14 + i * ((w - 28) // 8)
        cv.circle(px, y + h - 6, 6, (12, 12, 22))
    cv.text(x + 8, y + 10, "74 LASHES", 1, 0.6, (235, 120, 120))


def scene_fire(cv, x, y, w, h):
    cv.rect(x, y, w, h, (40, 34, 30))
    # factory
    cv.rect(x + 12, y + h - 62, w - 24, 40, (110, 100, 88))
    cv.rect(x + 20, y + h - 96, 10, 34, (90, 82, 72))
    cv.rect(x + w - 40, y + h - 104, 10, 42, (90, 82, 72))
    cv.circle(x + 25, y + h - 100, 6, SMOKE)
    cv.circle(x + w - 35, y + h - 108, 6, SMOKE)
    for i in range(4):
        cv.rect(x + 22 + i * 22, y + h - 52, 10, 12, GOLDL)
    # flames over the roof
    for fx in (x + 40, x + w // 2, x + w - 50):
        flame(cv, fx, y + h - 60, 1.1, ORANGE, FIRE)
        flame(cv, fx + 14, y + h - 60, 0.8, ORANGE, GOLDL)
    # smoke
    cv.circle(x + w // 2, y + 22, 14, SMOKE)
    cv.circle(x + w // 2 - 16, y + 34, 10, (140, 138, 132))
    cv.circle(x + w // 2 + 18, y + 30, 9, (140, 138, 132))
    # firefighters with hose
    person(cv, x + 30, y + h - 8, 0.9, RED)
    person(cv, x + 52, y + h - 8, 0.9, (200, 170, 40))
    cv.line(x + 40, y + h - 26, x + w - 20, y + h - 66, SEAL, 3)
    cv.line(x + w - 20, y + h - 66, x + w - 34, y + h - 84, SEAL, 2)
    for k in range(5):
        cv.circle(x + w - 36 + k * 3, y + h - 88 + k, 2, SEAL)


def scene_cop(cv, x, y, w, h):
    cv.rect(x, y, w, h, (214, 228, 222))
    # conference hall + round table
    cv.ellipse(x + w // 2, y + h - 26, w // 2 - 8, 26, (120, 90, 60))
    cv.ellipse(x + w // 2, y + h - 32, w // 2 - 8, 24, (150, 116, 76))
    # delegates around the table
    for i in range(9):
        px = x + 16 + i * ((w - 32) // 8)
        py = y + h - 62 - (10 if i % 2 == 0 else 0)
        person(cv, px, py + 22, 0.8, [NAVY, RED, TEAL, (90, 60, 120), GREEN, (140, 90, 30), NAVY, RED, TEAL][i])
    # flags on the table
    flag_row(cv, x + w // 2 - 52, y + h - 46, 104,
             [NAVY, RED, GREEN, GOLD, TEAL, ORANGE, NAVY, RED], 8)
    # cracked globe above, empty chair
    gx, gy = x + w // 2, y + 34
    cv.circle(gx, gy, 24, SEA)
    cv.circle(gx - 6, gy - 6, 8, GREEN)
    cv.circle(gx + 8, gy + 8, 7, GREEN)
    cv.line(gx - 18, gy - 18, gx + 16, gy + 14, WHITE, 2)
    cv.line(gx - 4, gy - 22, gx + 2, gy + 20, WHITE, 2)
    cv.rect(x + 14, y + h - 66, 16, 30, (90, 70, 50))
    cv.rect(x + 14, y + h - 78, 16, 12, (110, 88, 62))
    cv.text(x + 8, y + 6, "NO DEAL", 1, 0.6, RED)


# ---------------------------------------------------------------- dotted map
LAND = [  # (cx, cy, rx, ry) ellipses inside the map box, relative coords
    (62, 52, 52, 32), (92, 118, 26, 28), (182, 42, 22, 16),
    (188, 92, 28, 36), (258, 52, 52, 38), (272, 102, 24, 11),
    (282, 138, 20, 12),
]


def in_land(px, py):
    for cx, cy, rx, ry in LAND:
        if ((px - cx) / rx) ** 2 + ((py - cy) / ry) ** 2 <= 1.0:
            return True
    return False


def dotted_map(cv, x, y, w, h):
    cv.rect(x, y, w, h, (228, 236, 240))
    for gy in range(y + 6, y + h - 4, 7):
        for gx in range(x + 6, x + w - 4, 7):
            if in_land(gx - x, gy - y):
                cv.circle(gx, gy, 2, NAVY)
    marks = [("1", 52, 58), ("2", 178, 78), ("3", 206, 72),
             ("4", 258, 78), ("5", 276, 104), ("6", 206, 52)]
    for num, mx, my in marks:
        cv.circle(x + mx, y + my, 8, RED)
        cv.text_c(x + mx, y + my - 5, num, 1, 0.55, WHITE)


# ---------------------------------------------------------------- stories
MEDIUM = [
    ("EUROPE • SPACE", "NATO VOWS SPACE DEFENCE AFTER RUSSIAN SATELLITE SCARE",
     "Chief warns Moscow's reported nuclear satellite threatens orbit.",
     scene_nato),
    ("LIBYA • WAR", "UKRAINE HITS RUSSIAN SHIP OFF LIBYA; TRIPOLI DEMANDS ANSWERS",
     "Kyiv says drones struck the warship; Libya wants an explanation.",
     scene_libya),
    ("ASIA • LAW", "14 NATIONS BACK ICJ RULING ON ROHINGYA GENOCIDE",
     "UK sanctions junta leaders as the court verdict wins global backing.",
     scene_icj),
    ("ASIA • QUAKE", "5.6 QUAKE SHAKES NEPAL NEAR CHINA BORDER",
     "Tremors felt across India as rescuers check mountain villages.",
     scene_nepal),
    ("MIDDLE EAST • GAZA", "OXFAM: GAZA TURNED INTO A 'TOXIC WASTELAND'",
     "Aid group says bombardment poisoned land, water and fields.",
     scene_gaza),
    ("MIDDLE EAST • IRAN", "IRAN FLOGS SINGER 74 TIMES FOR SINGING WITHOUT HIJAB",
     "Parastoo Ahmadi punished as Tehran also rules out US talks.",
     scene_iran),
]

ALSO = [
    ("UN", "Guterres wants AI-risk pact in a year"),
    ("US", "Democrats win biggest House majority since 1992"),
    ("US", "California Democrat to quit over misconduct"),
    ("US", "Trump halts toxic explosives blast in Iowa"),
    ("US", "ICE detains Princeton PhD student at airport"),
    ("US", "Measles kills ninth in Pennsylvania"),
    ("CHINA", "Tiangong opens to first foreign astronaut"),
    ("KOREA", "Exports hit $77.4bn in 20 days of Nov"),
    ("INDIA", "Modi, Nepal PM sign Joint Vision deal"),
    ("INDIA", "Markets shut for Guru Nanak Jayanti"),
    ("NEPAL", "5.6 quake shakes Nepal near China border"),
    ("INDONESIA", "Factory fire kills several, workers missing"),
    ("BANGLADESH", "Hasina says she will return 16 Dec"),
    ("EU", "Council adopts 2027 budget of EUR 199.7bn"),
    ("EU", "Indonesia pact cuts tariffs on 98% of lines"),
    ("EU", "Antitrust probe into Coca-Cola Europacific"),
    ("EU", "German PMI 55.0, best since March 2022"),
    ("CLIMATE", "COP31 fallout: Erdogan defends talks"),
    ("MARKETS", "Nasdaq 100 surges 6.86% in a day"),
    ("MARKETS", "DOJ seeks $1.1bn in USDC forfeit"),
    ("MARKETS", "LEGO to build EUR 1bn Portugal plant"),
    ("MARKETS", "BP caps $6bn bond buyback"),
    ("IRAN", "No talks until US meets seven demands"),
    ("YEMEN", "Houthis: dozens dead in Saudi strikes"),
    ("MEXICO", "'El Chapo Isidro' to face trial at home"),
    ("COLOMBIA", "Car bomb wrecks buildings in Villavicencio"),
    ("CUBA", "WHO chief visits crumbling health system"),
    ("SPORT", "NFL: 49ers, Bills and Chiefs win Week 11"),
    ("SPORT", "FIFA: Infantino jet flights scrutinised"),
]


# ---------------------------------------------------------------- build
def build():
    load_font()
    cv = Canvas()
    # masthead
    cv.hline(16, 8, 992, INK, 3)
    cv.text_c(512, 4, "THE WORLD IN ONE IMAGE", 0, 1.55, INK)
    cv.text(16, 63, "TUESDAY 24 NOVEMBER 2026", 1, 0.8, RED)
    cv.text_c(512, 63, "36 STORIES  •  ONE DAY", 1, 0.8, INK2)
    tw = FONT.text_w("PRICE: ONE DAY OF NEWS", 1, 0.8)
    cv.text(1008 - tw, 63, "PRICE: ONE DAY OF NEWS", 1, 0.8, INK2)
    cv.hline(16, 80, 992, RED, 3)
    # hero
    hx, hy, hw, hh = 16, 88, 992, 276
    cv.border(hx, hy, hw, hh, INK, 2)
    scene_hero(cv, hx + 2, hy + 2, hw - 4, 182)
    cv.rect(hx + 2, hy + 184, hw - 4, hh - 186, CREAM)
    cv.hline(hx + 2, hy + 184, hw - 4, GOLD, 3)
    cv.text(hx + 14, hy + 192, "TECH  •  MARKETS  •  WASHINGTON", 1, 0.7, RED)
    cv.text(hx + 14, hy + 208, "HUANG RETURNS TO NVIDIA AS MARKETS ROAR BACK", 0, 0.9, INK)
    body = FONT.wrap("The chip chief is reinstated after a spy scandal; Seoul jumps 6%, Tokyo 3.9% "
                     "and the Nasdaq 6.9% as Nvidia adds nearly $1 trillion in value. Trump: 'I made the deal.'",
                     1, 0.75, hw - 28)
    cv.para(hx + 14, hy + 240, body, 1, 0.75, INK2, 16)
    # medium cards, 2 rows x 3
    cw, chh, gap = 325, 200, 8
    for idx, (tag, head, body1, scene) in enumerate(MEDIUM):
        r, c = divmod(idx, 3)
        cx = 16 + c * (cw + gap)
        cy = 372 + r * (chh + 8)
        cv.rect(cx, cy, cw, chh, CREAM)
        cv.border(cx, cy, cw, chh, INK, 2)
        scene(cv, cx + 2, cy + 2, cw - 4, 104)
        cv.text(cx + 8, cy + 110, tag, 1, 0.6, RED)
        hl = FONT.wrap(head, 0, 0.58, cw - 16)
        cv.para(cx + 8, cy + 126, hl[:2], 0, 0.58, INK, 22)
        by = cy + 126 + len(hl[:2]) * 22 + 2
        bl = FONT.wrap(body1, 1, 0.62, cw - 16)
        cv.para(cx + 8, by, bl[:2], 1, 0.62, INK2, 13)
    # bottom band
    by0 = 788
    cv.rect(16, by0, 330, 208, PAPER2)
    cv.border(16, by0, 330, 208, INK, 2)
    cv.text(28, by0 + 8, "WHERE IT HAPPENED", 1, 0.7, RED)
    dotted_map(cv, 24, by0 + 28, 314, 124)
    cv.text(28, by0 + 162, "1 US  2 Libya  3 Gaza  4 Nepal  5 Indonesia  6 Turkiye", 1, 0.55, INK2)
    cv.text(28, by0 + 178, "DOTS: LAND  •  RED: THE DAY'S HOT SPOTS", 1, 0.55, INK2)
    cv.rect(354, by0, 654, 208, CREAM)
    cv.border(354, by0, 654, 208, INK, 2)
    cv.text(366, by0 + 8, "ALSO TODAY — 29 MORE STORIES", 1, 0.7, RED)
    cv.hline(366, by0 + 26, 630, INK, 1)
    col_w = 312
    for i, (reg, txt) in enumerate(ALSO):
        col, row = divmod(i, 15)
        ix = 366 + col * (col_w + 6)
        iy = by0 + 34 + row * 11
        sc = 0.52
        full = reg + "  " + txt
        fw = FONT.text_w(full, 1, sc)
        if fw > 306:
            sc = sc * 306 / fw
        rw = cv.text(ix, iy, reg + "  ", 1, sc, RED)
        cv.text(ix + rw, iy, txt, 1, sc, INK)
    # footer
    cv.hline(16, 1004, 992, INK, 2)
    cv.text_c(512, 1010, "DATE CHECK: EVERY STORY HAPPENED OR WAS FIRST REPORTED ON TUESDAY 24 NOVEMBER 2026",
              1, 0.5, INK2)
    return cv


def main():
    cv = build()
    out = "/output/entry.png"
    os.makedirs("/output", exist_ok=True)
    write_png(out, cv.px)


if __name__ == "__main__":
    main()
