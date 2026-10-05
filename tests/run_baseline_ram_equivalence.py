#!/usr/bin/env python3
"""Run a paired simulation of the preserved baseline before/after RAM inference."""

from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    root = repo.parents[1]
    snapshots = root / "outputs" / "snes-luma-chroma" / "baseline"
    original = snapshots / "composite_blend_unmodified.sv"
    ram_fixed = snapshots / "composite_blend.sv"
    testbench = repo / "tests" / "composite_blend_ram_diff_tb.sv"
    with tempfile.TemporaryDirectory(prefix="composite-ram-diff-") as tmp:
        tmpdir = Path(tmp)
        source_paths = []
        for source, module in ((original, "composite_blend_original"),
                               (ram_fixed, "composite_blend_ram")):
            text = source.read_text(encoding="utf-8")
            text, count = re.subn(r"\bmodule\s+composite_blend\s*\(",
                                  f"module {module} (", text, count=1)
            if count != 1:
                raise RuntimeError(f"Could not rename composite_blend in {source}")
            output = tmpdir / f"{module}.sv"
            output.write_text(text, encoding="utf-8")
            source_paths.append(str(output))

        executable = tmpdir / "equivalence.vvp"
        compile_cmd = ["iverilog", "-g2012", "-s", "composite_blend_ram_diff_tb",
                       "-o", str(executable), *source_paths, str(testbench)]
        subprocess.run(compile_cmd, check=True)
        result = subprocess.run(["vvp", str(executable)], check=True,
                                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        print(result.stdout, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
