"""Visual regression + deliverable render for the bilingual flowchart.

Outputs
-------
* flow.png             complete, trimmed full-page deliverable (never overwritten
                       by the zoom checks below).
* flow_zoom100.png     100% (1280 wide) render — proof of fit at desktop width.
* flow_zoom50.png      50%  (640  wide) render — proof of fit at tablet width.
* flow_zoom33.png      33%  (420  wide) render — proof of fit at mobile width.

Overflow guard
--------------
For each zoom we measure the page's scrollWidth vs innerWidth through headless
Chrome's DevTools Protocol (see overflow_check.mjs). The SVG uses width:100%
and .stage uses max-width:100%, so the page is responsive by construction;
this is a guard, not a workaround.

Note on the "half screenshot" bug this script replaces: an earlier version
wrote every zoom into the same flow.png, so the final 33% pass left a tiny
139x238 image in place. Here the deliverable and the zoom proofs are separate
files, and the deliverable is rendered tall then trimmed so no content is
clipped by the window-size boundary.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HTML = ROOT / "flow.html"
FLOW = ROOT / "flow.png"
URL = HTML.as_uri()

CHROME_PATHS = [
    Path(r"C:/Program Files/Google/Chrome/Application/chrome.exe"),
    Path(r"C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"),
]
NODE = shutil.which("node") or r"C:/Users/HP/.workbuddy/binaries/node/versions/22.22.2/node.exe"

CHROME = next((str(p) for p in CHROME_PATHS if p.exists()), None)
if CHROME is None:
    raise RuntimeError("Chrome not found")

# Desktop render height. The natural content height is ~770px; 900 leaves
# headroom so nothing is clipped, and we trim the leftover margin afterwards.
FULL_HEIGHT = 900

CASES = [
    {"label": "100%", "vp": 1280, "scale": 1.0},
    {"label": "50%",  "vp": 640,  "scale": 0.5},
    {"label": "33%",  "vp": 420,  "scale": 0.33},
]


def render(viewport: int, scale: float, out: Path) -> None:
    subprocess.run(
        [
            CHROME,
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            f"--force-device-scale-factor={scale}",
            f"--window-size={viewport},{FULL_HEIGHT}",
            f"--screenshot={out}",
            URL,
        ],
        check=True,
        capture_output=True,
    )


def trim(path: Path) -> tuple[int, int]:
    """Crop to the content bounding box, keep a 16px margin, return new size."""
    from PIL import Image, ImageChops

    img = Image.open(path).convert("RGB")
    bg = Image.new("RGB", img.size, (247, 241, 234))  # body background #F7F1EA
    diff = ImageChops.difference(img, bg)
    bbox = diff.getbbox()
    if not bbox:
        return img.size
    l, t, r, b = bbox
    m = 16
    l = max(0, l - m)
    t = max(0, t - m)
    r = min(img.width, r + m)
    b = min(img.height, b + m)
    img.crop((l, t, r, b)).save(path)
    return (r - l, b - t)


def overflow_at(vp: int) -> tuple[int, int]:
    """Return (scrollWidth, innerWidth) measured via CDP."""
    env = dict(__import__("os").environ, CHROME_PATH=CHROME)
    out = subprocess.run(
        [NODE, str(ROOT / "overflow_check.mjs"), URL, str(vp)],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    ).stdout.strip()
    sw, iw = (int(x) for x in out.split())
    return sw, iw


def main() -> int:
    # 1) Deliverable: render tall, then trim away bottom whitespace.
    render(1280, 1.0, FLOW)
    w, h = trim(FLOW)
    print(f"deliverable flow.png: {w}x{h} (trimmed, complete)")

    # 2) Zoom proofs + overflow guard (separate files, never touch flow.png).
    results = []
    failed = False
    for c in CASES:
        zp = ROOT / f"flow_zoom{c['label'].replace('%', '')}.png"
        render(c["vp"], c["scale"], zp)
        if not zp.exists() or zp.stat().st_size < 5000:
            print(f"FAIL {c['label']}: missing or tiny zoom render", file=sys.stderr)
            failed = True
            continue
        sw, iw = overflow_at(c["vp"])
        overflow = sw > iw
        results.append({
            "zoom": c["label"],
            "viewport_width": c["vp"],
            "scrollWidth": sw,
            "innerWidth": iw,
            "overflows": overflow,
        })
        if overflow:
            failed = True
            print(f"FAIL {c['label']}: scrollWidth {sw} > innerWidth {iw}", file=sys.stderr)
        else:
            print(f"ok {c['label']}: scrollWidth {sw} <= innerWidth {iw}")

    print(json.dumps(results, ensure_ascii=False, indent=2))
    if failed:
        return 1
    print("OK: flowchart fits at 100%, 50%, and 33% zoom with no horizontal overflow")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
