import shutil
import argparse
from pathlib import Path

import cv2
import numpy as np


def has_red_circle(img_bgr, debug=False):
    """
    Detect thin red circle outlines by:
    1) HSV threshold for red (two hue bands)
    2) Morph close to connect/thicken the ring
    3) HoughCircles on the mask
    Returns: (found_bool, overlay_or_None, mask_uint8)
    """
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)

    lower1 = np.array([0, 40, 40])
    upper1 = np.array([12, 255, 255])
    lower2 = np.array([168, 40, 40])
    upper2 = np.array([180, 255, 255])

    mask = cv2.bitwise_or(
        cv2.inRange(hsv, lower1, upper1),
        cv2.inRange(hsv, lower2, upper2),
    )

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

    # Blur
    mask_blur = cv2.GaussianBlur(mask, (9, 9), 2)

    # Detect circles / the mask
    circles = cv2.HoughCircles(
        mask_blur,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=40,
        param1=100,
        param2=50,     # lower = more sensitive 
        minRadius=8,   # tune rings 
        maxRadius=140,
    )

    found = circles is not None

    if not debug:
        return found, None, mask

    overlay = img_bgr.copy()
    if found:
        circles = np.uint16(np.around(circles))
        # Draw the first detected circle
        x, y, r = circles[0][0]
        cv2.circle(overlay, (x, y), r, (0, 255, 0), 3)
        cv2.circle(overlay, (x, y), 2, (0, 255, 0), 3)
        cv2.putText(
            overlay,
            f"circle r={int(r)}",
            (max(0, x - 40), max(0, y - r - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )

    return found, overlay, mask


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in_dir", required=True, help="Folder with input images")
    ap.add_argument("--out_dir", required=True, help="Folder to copy matched images into")
    ap.add_argument("--debug_dir", default=None, help="Optional folder to save debug overlays/masks")
    args = ap.parse_args()

    in_dir = Path(args.in_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    debug_dir = Path(args.debug_dir) if args.debug_dir else None
    if debug_dir:
        debug_dir.mkdir(parents=True, exist_ok=True)

    exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    files = [p for p in in_dir.iterdir() if p.suffix.lower() in exts]

    matches = 0
    for p in files:
        img = cv2.imread(str(p))
        if img is None:
            continue

        ok, overlay, mask = has_red_circle(img, debug=bool(debug_dir))

        if ok:
            matches += 1
            shutil.copy2(p, out_dir / p.name)

        if debug_dir:
            base = p.stem
            cv2.imwrite(str(debug_dir / f"{base}_mask.png"), mask)
            if overlay is None:
                overlay = img
            cv2.imwrite(str(debug_dir / f"{base}_overlay.png"), overlay)

    print(f"Scanned {len(files)} images. Found {matches} matches. Output -> {out_dir}")


if __name__ == "__main__":
    main()
