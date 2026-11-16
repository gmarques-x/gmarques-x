#!/usr/bin/env python3
"""Reduce a logo shot to 256 colours without losing its look.

    quantize-logo.py IN.png OUT.png   (needs Pillow)

make-logo.sh runs it when Pillow is there. After assets/banner/
quantize-banner.py of Project Grove, without the banner's accents (the logo
has none):
  - 248 entries for the square, found from it (median cut), which is then
    dithered onto them (Floyd-Steinberg), so the mottle does not band.
  - 8 entries for the corners: fully transparent, and seven steps of alpha
    for the anti-aliased edge of the rounding.
"""
import sys
from PIL import Image

EDGE = 8


def main():
    src, dst = sys.argv[1:3]
    rgba = Image.open(src).convert("RGBA")
    plate = rgba.convert("RGB")

    n = 256 - EDGE
    found = plate.quantize(n, method=Image.Quantize.MEDIANCUT).getpalette()[:n * 3]
    found += [0] * (n * 3 - len(found))
    reference = Image.new("P", (1, 1))
    reference.putpalette(found)
    out = plate.quantize(palette=reference, dither=Image.Dither.FLOYDSTEINBERG)

    # The corners: alpha 0 is entry 248, the edge's partial alphas 249..255,
    # each coloured with the mean of the edge pixels it stands for.
    first = 256 - EDGE
    pixels, alpha, colour = out.load(), rgba.getchannel("A").load(), rgba.load()
    width, height = rgba.size
    steps = {}
    for y in range(height):
        for x in range(width):
            a = alpha[x, y]
            if a == 255:
                continue
            k = 0 if a == 0 else 1 + a * (EDGE - 1) // 255
            steps.setdefault(k, []).append(colour[x, y][:3])
            pixels[x, y] = first + k
    palette = out.getpalette()[:first * 3]
    transparency = [255] * first
    for k in range(EDGE):
        cs = steps.get(k, [(0, 0, 0)])
        palette += [sum(c[i] for c in cs) // len(cs) for i in range(3)]
        transparency.append(0 if k == 0 else round((k - .5) * 255 / (EDGE - 1)))
    out.putpalette(palette)
    out.save(dst, optimize=True, transparency=bytes(transparency))


if __name__ == "__main__":
    main()
