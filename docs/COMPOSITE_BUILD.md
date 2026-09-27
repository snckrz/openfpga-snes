# Build and validation notes

## Source and compiler

- Base: [drizzt/openfpga-snes at `397f759356ec680dd516a05a89b3734ea5716d71`](https://github.com/drizzt/openfpga-snes/tree/397f759356ec680dd516a05a89b3734ea5716d71).
- Build version: `2026.09.26-composite1`; package date: `2026-09-26`.
- Compiler: Quartus Prime Lite 21.1.1, build 850.
- Container: `ghcr.io/drizzt/quartus@sha256:b5b0f0b7af271a0b9e9adc0cad59ff773d8690742a1426500fd71056d2c09787`.
- Packaging helper: [agg23/pocketpublish at `55dff61f77a9d16ba3e4f42679b3c6426e0fc718`](https://github.com/agg23/pocketpublish/tree/55dff61f77a9d16ba3e4f42679b3c6426e0fc718).

## Measured results

Worst reported slack across the analyzed models, in nanoseconds:

| Variant | Setup | Hold | Logic utilization |
|---|---:|---:|---|
| main | 1.746 | 0.105 | 17,394 / 18,480 ( 94 % ) |
| pal | 2.417 | 0.084 | 17,404 / 18,480 ( 94 % ) |
| spc | 2.318 | 0.097 | 17,314 / 18,480 ( 94 % ) |
| sa1 | 2.482 | 0.082 | 17,183 / 18,480 ( 93 % ) |
| cx4 | 1.546 | 0.072 | 17,082 / 18,480 ( 92 % ) |
| pal_sa1 | 2.233 | 0.105 | 17,234 / 18,480 ( 93 % ) |
| pal_cx4 | 2.236 | 0.073 | 17,017 / 18,480 ( 92 % ) |

Full compilation and FPGA fit succeeded. All reported setup, hold, recovery, removal and minimum pulse-width slacks are nonnegative, with zero total negative slack. No unconstrained clocks were reported. These results use the repository’s existing constraints and do not prove timing for unconstrained I/O or replace hardware testing.

The design emits warnings including unmatched clock filters and power-up-level warnings in upstream CEGen/SPC7110 registers. External I/O is not fully constrained. The BSX MIF provides 550 entries for a 1,024-entry memory; Quartus initializes the remaining entries to zero (warning 127005). The stale MIF path was corrected before the final SPC build. PAL CX4 seed 1 had a -0.029 ns palette-memory hold violation; the delivered seed-2 build passes. All other variants use seed 1.

The seven variants are main (NTSC), PAL, SPC/S-DD1/BSX, NTSC SA-1, NTSC CX4, PAL SA-1 and PAL CX4. The loader selects them automatically. Hardware coverage of each variant has not been recorded.

## Hardware and simulation coverage

I’ve tried this build on my Pocket and haven’t noticed any obvious problems. I haven’t recorded specific game, firmware and display-mode coverage yet. Broader handheld/Dock, palette, Off/Full, save/load and Sleep/Wake testing is welcome on compatible games. This is not a claim of complete compatibility.

The standalone Icarus test covers disabled bypass, independent RGB arithmetic, odd-sum rounding, overflow, enable changes and blanking/line boundaries. Packaging verifies JSON, menu IDs, bitstream byte-wise reversal and archive integrity. Installed files were read back and checked by SHA-256 during initial testing.

## Integration

The menu uses ID `54` and bridge address `0x20C`. Its enable bit is synchronized into the Pocket pixel clock domain. The filter averages the current and previous input pixel without adding a pixel-cycle pipeline delay. A line’s first pixel uses black as its left neighbor. Blanking invalidates history.

Blending occurs before the Pocket video-slot metadata is inserted. Sync/data-enable timing and save-state logic are not changed. SNES Pseudo Transparency remains independent. The separate Analogizer path is not filtered.

## Rebuild with Docker

These commands use a POSIX shell, including WSL, from the repository root. Docker stores Quartus and build databases in its configured data location. The pinned image occupies roughly 12 GB; allow additional working space. Use a fresh build volume/container name for each attempt.

```sh
docker volume create snes-composite-build
docker run --name snes-composite-build \
  --mount type=bind,source="$PWD",target=/source,readonly \
  --mount type=volume,source=snes-composite-build,target=/build \
  ghcr.io/drizzt/quartus@sha256:b5b0f0b7af271a0b9e9adc0cad59ff773d8690742a1426500fd71056d2c09787 \
  bash /source/tools/build-composite.sh
docker cp snes-composite-build:/build/results ./build-results
python3 tools/package-composite.py --results build-results --output release
```

Python 3.10 or newer is sufficient for packaging; no Python dependency installation is needed. The packaging tool rejects reported negative timing slack, missing memory-initialization files, failed compilation or unconstrained clocks. Review all compiler warnings too. A locally reproduced ZIP can differ in archive timestamps while containing identical payload files; compare per-file SHA-256 values in the manifests.

To rerun the filter simulation with Icarus installed:

```sh
iverilog -g2012 -s composite_blend_tb -o /tmp/composite-blend \
  target/pocket/composite_blend.sv tests/composite_blend_tb.sv
vvp /tmp/composite-blend
```
