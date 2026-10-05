#!/usr/bin/env python3
"""Compare the existing RGB kernels with the proposed separated Y/C kernels.

This is a deterministic numerical report, complementary to the HDL testbench.
It uses the repository's endpoint-clamped tap positions and floor shifts,
including the baseline PAL horizontal-RGB then vertical-chroma operation.
"""

from __future__ import annotations

import random
from collections.abc import Callable

RGB = tuple[int, int, int]


def clip(v: int) -> int:
    return min(255, max(0, v))


def ycc(rgb: RGB) -> tuple[int, int, int, int]:
    r, g, b = rgb
    total = r + 2 * g + b
    y = total >> 2
    return y, r - y, b - y, total & 3


def pack(y: int, cr: int, cb: int, residue: int, *, clipping: bool = True) -> RGB:
    r = y + cr
    b = y + cb
    g = y - ((cr + cb - residue) >> 1)
    if clipping:
        return clip(r), clip(g), clip(b)
    return r, g, b


def taps(line: list[RGB], x: int) -> tuple[RGB, RGB, RGB, RGB]:
    at = lambda i: line[min(len(line) - 1, max(0, i))]
    return at(x - 2), at(x - 1), at(x), at(x + 1)


def luma_q2(line: list[RGB], x: int, mode: int) -> int:
    oldest, older, center, right = taps(line, x)
    q2 = [sum((pixel[0], 2 * pixel[1], pixel[2])) for pixel in
          (oldest, older, center, right)]
    if mode in (2, 5):
        return (q2[1] + 6 * q2[2] + q2[3]) >> 3
    if mode in (3, 6):
        light = (q2[1] + 6 * q2[2] + q2[3]) >> 3
        box = sum(q2) >> 2
        return (light + box) >> 1
    if mode in (4, 7, 8):
        return sum(q2) >> 2
    return q2[2]


def old_horizontal(line: list[RGB], x: int, mode: int) -> RGB:
    oldest, older, center, right = taps(line, x)
    if mode == 1:
        left = (0, 0, 0) if x == 0 else older
        return tuple((a + b) >> 1 for a, b in zip(left, center))  # type: ignore[return-value]
    n1 = tuple((a + 2 * b + c) >> 2 for a, b, c in zip(right, center, older))
    n3 = tuple((a + b + c + d) >> 2 for a, b, c, d in zip(oldest, older, center, right))
    if mode in (2, 5):
        return n1
    if mode in (3, 6):
        return tuple((a + b) >> 1 for a, b in zip(n1, n3))  # type: ignore[return-value]
    if mode in (4, 7, 8):
        return n3
    return center


def separated_horizontal(line: list[RGB], x: int, mode: int) -> tuple[RGB, tuple[int, int, int]]:
    center = line[x]
    q2 = luma_q2(line, x, mode)
    yc, _, _, residue = ycc(center)
    yc = q2 >> 2
    coeff_pixels = taps(line, x)
    oldest, older, middle, right = coeff_pixels

    def channel(pixel: RGB, cr: bool) -> int:
        py, pcr, pcb, _ = ycc(pixel)
        return pcr if cr else pcb

    def filtered(cr: bool) -> int:
        left1, c, r = (channel(older, cr), channel(middle, cr), channel(right, cr))
        n1 = (r + 2 * c + left1) >> 2
        n3 = sum(channel(p, cr) for p in (oldest, older, middle, right)) >> 2
        if mode == 2:
            return n1
        if mode in (3, 5):
            return (n1 + n3) >> 1
        if mode in (4, 6, 7, 8):
            return n3
        return channel(middle, cr)

    cr, cb = filtered(True), filtered(False)
    return pack(yc, cr, cb, residue), (yc, cr, cb)


def baseline_pal(current: RGB, previous: RGB) -> RGB:
    cy, ccr, ccb, _ = ycc(current)
    py, pcr, pcb, _ = ycc(previous)
    dcr = (pcr - ccr) >> 1
    dcb = (pcb - ccb) >> 1
    return clip(current[0] + dcr), clip(current[1] - ((dcb + dcr) >> 1)), clip(current[2] + dcb)


def separated_pal(current: RGB, current_cc: tuple[int, int, int], previous_cc: tuple[int, int, int],
                  mode: int = 7) -> RGB:
    y, _, _, residue = ycc(current)
    _, ccr, ccb = current_cc
    _, pcr, pcb = previous_cc
    if mode == 8:
        return pack(y, (ccr + pcr) >> 1, (ccb + pcb) >> 1, residue)
    return pack(y, (3 * ccr + pcr) >> 2, (3 * ccb + pcb) >> 2, residue)


def scene(name: str, width: int, row: int, rng: random.Random) -> list[RGB]:
    if name == "black-white edge":
        return [(0, 0, 0) if x < width // 2 else (255, 255, 255) for x in range(width)]
    if name == "saturated RGB bars":
        bars = ((255, 0, 0), (0, 255, 0), (0, 0, 255))
        return [bars[(x // 4) % len(bars)] for x in range(width)]
    if name == "matched-luma magenta-green":
        return [(255, 0, 255) if x & 1 else (0, 255, 0) for x in range(width)]
    if name == "black-white checker":
        return [(255, 255, 255) if (x + row) & 1 else (0, 0, 0) for x in range(width)]
    if name == "cyan-magenta dither":
        return [(255, 0, 255) if x % 4 < 2 else (0, 255, 255) for x in range(width)]
    if name == "clipping colors":
        colors = ((255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0),
                  (0, 255, 255), (255, 0, 255), (255, 255, 255), (0, 0, 0))
        return [colors[x % len(colors)] for x in range(width)]
    return [(rng.randrange(256), rng.randrange(256), rng.randrange(256)) for _ in range(width)]


def summarize(name: str, mode: int, current: list[RGB], previous: list[RGB] | None = None) -> str:
    old_out: list[RGB] = []
    new_out: list[RGB] = []
    luma_abs = 0
    luma_abs_unclipped = 0
    count = len(current)
    for x, pixel in enumerate(current):
        old = old_horizontal(current, x, mode)
        new, cc = separated_horizontal(current, x, mode)
        q2 = luma_q2(current, x, mode)
        center_y, _, _, residue = ycc(pixel)
        center_y = q2 >> 2
        final_cr, final_cb = cc[1], cc[2]
        if previous is not None:
            old = baseline_pal(old, old_horizontal(previous, min(x, len(previous) - 1), mode))
            _, pcc = separated_horizontal(previous, min(x, len(previous) - 1), mode)
            if mode == 8:
                final_cr = (final_cr + pcc[1]) >> 1
                final_cb = (final_cb + pcc[2]) >> 1
            else:
                final_cr = (3 * final_cr + pcc[1]) >> 2
                final_cb = (3 * final_cb + pcc[2]) >> 2
            new = pack(center_y, final_cr, final_cb, residue)
        old_out.append(old)
        new_out.append(new)
        raw = pack(center_y, final_cr, final_cb, residue, clipping=False)
        luma_abs += abs(ycc(new)[0] - center_y)
        luma_abs_unclipped += abs(((raw[0] + 2 * raw[1] + raw[2]) >> 2) - center_y)
    diffs = [abs(a - b) for old, new in zip(old_out, new_out) for a, b in zip(old, new)]
    return (f"{name:27s} mode {mode}: RGB MAE={sum(diffs)/len(diffs):6.2f}, max={max(diffs):3d}, "
            f"changed={sum(d != 0 for d in diffs)*100/len(diffs):5.1f}%, "
            f"new luma MAE clipped={luma_abs/count:5.2f} raw={luma_abs_unclipped/count:5.2f}")


def chroma_peak_to_peak(values: list[int]) -> int:
    return max(values) - min(values)


def modulation_energy(values: list[int]) -> float:
    mean = sum(values) / len(values)
    return sum((value - mean) ** 2 for value in values) / len(values)


def print_matched_luma_chroma_progression() -> None:
    line = [(255, 0, 255) if (x % 4) < 2 else (0, 255, 0) for x in range(64)]
    interior = range(4, len(line) - 4)
    source_cr = [ycc(line[x])[1] for x in interior]
    source_cb = [ycc(line[x])[2] for x in interior]
    source_pp = (chroma_peak_to_peak(source_cr), chroma_peak_to_peak(source_cb))
    print("Matched-luma magenta/green 2-on/2-off interior chroma peak-to-peak:")
    print(f"input: Cr={source_pp[0]}, Cb={source_pp[1]}")
    for mode in (2, 3, 4):
        filtered = [separated_horizontal(line, x, mode)[1] for x in interior]
        cr_pp = chroma_peak_to_peak([cc[1] for cc in filtered])
        cb_pp = chroma_peak_to_peak([cc[2] for cc in filtered])
        print(f"mode {mode}: Cr={cr_pp} ({cr_pp/source_pp[0]*100:4.0f}%), "
              f"Cb={cb_pp} ({cb_pp/source_pp[1]*100:4.0f}%)")


def print_pal_chroma_kernel_mapping() -> None:
    line = [(255, 0, 255) if (x % 4) < 2 else (0, 255, 0) for x in range(64)]
    interior = range(4, len(line) - 4)
    responses = {}
    for mode in (2, 3, 4, 5, 6, 7, 8):
        cc = [separated_horizontal(line, x, mode)[1] for x in interior]
        responses[mode] = (chroma_peak_to_peak([sample[1] for sample in cc]),
                           chroma_peak_to_peak([sample[2] for sample in cc]))
    print("PAL horizontal chroma kernel mapping on repeated 2-on/2-off rows:")
    for mode in (2, 3, 4, 5, 6, 7, 8):
        cr_pp, cb_pp = responses[mode]
        print(f"mode {mode}: Cr/Cb p-p={cr_pp}/{cb_pp}")
    assert responses[5] == responses[3], "PAL1 must use the NTSC2 midpoint chroma kernel"
    assert responses[6] == responses[4], "PAL2 must use the NTSC3 box chroma kernel"
    assert responses[7] == responses[4], "PAL Strong must use the NTSC Strong box chroma kernel"
    assert responses[8] == responses[7], "PAL Strong+ must use the PAL Strong box chroma kernel"
    assert all(separated_horizontal(line, x, 8) == separated_horizontal(line, x, 7)
               for x in interior), "PAL Strong+ horizontal output must match PAL Strong"


def print_monochrome_luma_progression() -> None:
    for label, period in (("one-pixel", 2), ("two-pixel", 4)):
        line = [(0, 0, 0) if (x % period) < period // 2 else (255, 255, 255)
                for x in range(64)]
        interior = range(4, len(line) - 4)
        full_luma = [sum((v[0], 2 * v[1], v[2])) >> 2
                     for v in (old_horizontal(line, x, 1) for x in interior)]
        full_pp = chroma_peak_to_peak(full_luma)
        input_luma = [sum((line[x][0], 2 * line[x][1], line[x][2])) >> 2 for x in interior]
        input_energy = modulation_energy(input_luma)
        full_energy = modulation_energy(full_luma)
        print(f"Monochrome {label} checker luma contrast (peak-to-peak / energy):")
        print(f"input: 255 / 100%; Full mode: {full_pp} / {full_energy/input_energy*100:4.0f}%")
        results = []
        blend_strengths = []
        for mode in (2, 3, 4):
            values = [luma_q2(line, x, mode) >> 2 for x in interior]
            pp = chroma_peak_to_peak(values)
            energy = modulation_energy(values)
            results.append(pp)
            blend = 100 * (1 - energy / input_energy)
            blend_strengths.append(blend)
            print(f"mode {mode}: {pp} / {energy/input_energy*100:4.0f}% retained, "
                  f"blend {blend:4.0f}%")
        assert results[0] >= results[1] >= results[2], "NTSC luma strengths are not monotonic"
        assert blend_strengths[2] >= 100 * (1 - full_energy / input_energy), "NTSC3 should blend at least as much as Full"


def print_pal_vertical_weight() -> None:
    magenta, green = (255, 0, 255), (0, 255, 0)
    _, current_cr, current_cb, _ = ycc(magenta)
    _, previous_cr, previous_cb, _ = ycc(green)
    print("PAL vertical chroma on flat magenta over green (same luma):")
    for mode in (5, 6, 7, 8):
        if mode == 8:
            mixed_cr = (current_cr + previous_cr) >> 1
            mixed_cb = (current_cb + previous_cb) >> 1
            assert (mixed_cr, mixed_cb) == (0, 0)
            print(f"mode {mode}: current Cr/Cb={current_cr}/{current_cb}, previous={previous_cr}/{previous_cb}, "
                  f"50:50={mixed_cr}/{mixed_cb}")
            continue
        mixed_cr = (3 * current_cr + previous_cr) >> 2
        mixed_cb = (3 * current_cb + previous_cb) >> 2
        half_cr = (current_cr + previous_cr) >> 1
        half_cb = (current_cb + previous_cb) >> 1
        assert (mixed_cr, mixed_cb) == (64, 64)
        assert (half_cr, half_cb) == (0, 0)
        print(f"mode {mode}: current Cr/Cb={current_cr}/{current_cb}, previous={previous_cr}/{previous_cb}, "
              f"75:25={mixed_cr}/{mixed_cb}; prior 50:50 would be {half_cr}/{half_cb}")


def main() -> None:
    rng = random.Random(0x5A4553)
    names = ("black-white edge", "saturated RGB bars", "matched-luma magenta-green",
             "black-white checker", "cyan-magenta dither", "clipping colors", "random RGB")
    lines = {name: scene(name, 64, 1, rng) for name in names}
    print("Comparison against baseline RGB-domain kernels (64 pixels, endpoint-clamped):")
    for name, line in lines.items():
        for mode in (2, 3, 4):
            print(summarize(name, mode, line))
    print_matched_luma_chroma_progression()
    print_pal_chroma_kernel_mapping()
    print_monochrome_luma_progression()
    print_pal_vertical_weight()
    print("PAL modes include vertical chroma averaging against a distinct preceding line:")
    for mode in (5, 6, 7, 8):
        current = lines["saturated RGB bars"]
        previous = lines["matched-luma magenta-green"]
        print(summarize("RGB bars over magenta-green", mode, current, previous))

    # Lossless fixed-point decomposition before chroma filtering: all 24-bit
    # colors reconstruct exactly when no filtering or clipping is applied.
    for r in range(256):
        for g in range(256):
            for b in (0, 1, 127, 254, 255):
                rgb = (r, g, b)
                y, cr, cb, residue = ycc(rgb)
                assert pack(y, cr, cb, residue, clipping=False) == rgb
    print("Y/chroma/residue reconstruction: 327,680 sampled colors exact")


if __name__ == "__main__":
    main()
