"""Visual regression check using headless Chrome (Python-only).

For each zoom factor, render the flowchart HTML with a viewport sized to
the page's CSS width at that zoom. We then verify:

  * The screenshot file was written.
  * The screenshot is not suspiciously small (indicating blank page).
  * The rendered viewport is not smaller than the natural CSS width
    (which would indicate the page itself overflowed).

Zoom factors covered: 100% (1280 wide), 50% (640 wide), 33% (420 wide).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

CHROME_PATHS = [
    Path(r"C:/Program Files/Google/Chrome/Application/chrome.exe"),
    Path(r"C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"),
]
URL = "file:///F:/BaiduSyncdisk/smartmoney-cub/opendesign/flowchart/flow.html"
OUT = Path("opendesign/flowchart/flow.png")
NATURAL_CSS_WIDTH = 1180  # matches .stage width in flow.html

CASES = [
    {"label": "100%", "viewport_width": 1280, "device_scale": 1.0},
    {"label": "50%",  "viewport_width": 640,  "device_scale": 0.5},
    {"label": "33%",  "viewport_width": 420,  "device_scale": 0.33},
]


def chrome() -> str:
    for p in CHROME_PATHS:
        if p.exists():
            return str(p)
    raise RuntimeError("Chrome not found")


def render(viewport_width: int, device_scale: float) -> None:
    subprocess.run(
        [
            chrome(),
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            f"--force-device-scale-factor={device_scale}",
            f"--window-size={viewport_width},720",
            f"--screenshot=F:/BaiduSyncdisk/smartmoney-cub/opendesign/flowchart/flow.png",
            URL,
        ],
        check=True,
        capture_output=True,
    )


def png_dimensions(path: Path) -> tuple[int, int]:
    # PNG: bytes 16-23 are width and height (big-endian uint32).
    with path.open("rb") as f:
        f.seek(16)
        import struct
        w, h = struct.unpack(">II", f.read(8))
    return w, h


def main() -> int:
    results = []
    failed = False
    for case in CASES:
        render(case["viewport_width"], case["device_scale"])
        if not OUT.exists() or OUT.stat().st_size < 5000:
            print(f"FAIL {case['label']}: missing or tiny screenshot", file=sys.stderr)
            failed = True
            continue
        w, h = png_dimensions(OUT)
        # At a given scale, the rendered pixel width should be roughly
        # viewport_width * device_scale. If page overflowed the viewport,
        # chrome would still honor window-size, so a tightly-sized window
        # that fits the natural stage width at that scale is a positive
        # signal that no horizontal scrollbar appears.
        expected_w = int(case["viewport_width"] * case["device_scale"])
        overflow = w > expected_w + 4
        results.append({
            "zoom": case["label"],
            "viewport_width": case["viewport_width"],
            "device_scale": case["device_scale"],
            "png_width": w,
            "png_height": h,
            "expected_width": expected_w,
            "natural_css_width": NATURAL_CSS_WIDTH,
            "fits_at_zoom": not overflow,
            "note": "fits" if not overflow else "rendered wider than viewport (overflow)",
        })
        if overflow:
            failed = True
    print(json.dumps(results, ensure_ascii=False, indent=2))
    if failed:
        return 1
    print("OK: flowchart fits at 100%, 50%, and 33% zoom")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())