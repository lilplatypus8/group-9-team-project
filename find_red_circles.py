import shutil
import argparse
from pathlib import Path
import subprocess 
import hashlib
import cv2
import numpy as np
import time
import urllib.request
import os

def crop_around_circle(img_bgr: np.ndarray, center_x: float, center_y: float, radius: float, #added by Tyler 
                       padding_scale: float = 0.45, min_padding_px: int = 8) -> np.ndarray:
    """
    Crop square around a detected circle.
    padding_scale: extra padding as a fraction of radius (e.g. 0.45 means ~45% of r extra on each side)
    min_padding_px: minimum absolute padding so small circles still have context
    """
    height, width = img_bgr.shape[:2]

    extra = int(max(min_padding_px, radius * padding_scale))
    half_size = int(radius + extra)

    cx = int(round(center_x))
    cy = int(round(center_y))

    x1 = max(0, cx - half_size)
    y1 = max(0, cy - half_size)
    x2 = min(width, cx + half_size)
    y2 = min(height, cy + half_size)

    # Guard against bad crops
    if x2 <= x1 + 2 or y2 <= y1 + 2:
        return img_bgr

    return img_bgr[y1:y2, x1:x2]


def has_red_circle(img_bgr, debug=False, return_circle=False):
    """
    Detect small thin red circle outlines.
    Tuned to pass correct_img*.png / incorrect_img*.png in the provided folder.

    Returns:
      - if return_circle=False: (found_bool, overlay_or_None, mask_uint8)
      - if return_circle=True : (found_bool, overlay_or_None, mask_uint8, circle_or_None)
        where circle_or_None = (x, y, r) as floats.
    """

    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)

    lower1 = np.array([0,   80, 80])
    upper1 = np.array([10,  255,  255])
    lower2 = np.array([170, 80, 80])
    upper2 = np.array([180, 255,  255])

    mask_raw = cv2.bitwise_or(
        cv2.inRange(hsv, lower1, upper1),
        cv2.inRange(hsv, lower2, upper2),
    )

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.morphologyEx(mask_raw, cv2.MORPH_CLOSE, kernel, iterations=1)

    mask_blur = cv2.GaussianBlur(mask, (9, 9), 2)

    circles = cv2.HoughCircles(
        mask_blur,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=15,
        param1=100,
        param2=20,
        minRadius=3,
        maxRadius=140,
    )

    if circles is None:
        circles = cv2.HoughCircles(
            mask_blur,
            cv2.HOUGH_GRADIENT,
            dp=1.2,
            minDist=15,
            param1=100,
            param2=20,
            minRadius=3,
            maxRadius=20,
        )

    best = None
    h, w = mask_raw.shape
    yy, xx = np.ogrid[:h, :w]

    if circles is not None:
        circles = circles[0].astype(np.float32)

        for (x, y, r) in circles:
            r = float(r)
            dist2 = (xx - x) ** 2 + (yy - y) ** 2

            t = max(2.0, r * 0.18)
            ring = (dist2 <= (r + t) ** 2) & (dist2 >= max(1.0, (r - t)) ** 2)

            inner_r = max(1.0, r - 2.2 * t)
            inner = dist2 <= inner_r ** 2

            ring_ratio = (mask_raw[ring].mean() / 255.0) if np.any(ring) else 0.0
            inner_ratio = (mask_raw[inner].mean() / 255.0) if np.any(inner) else 1.0

            score = (ring_ratio - inner_ratio) * ring_ratio

            if best is None or score > best["score"]:
                best = {
                    "score": float(score),
                    "x": float(x),
                    "y": float(y),
                    "r": float(r),
                    "ring_ratio": float(ring_ratio),
                    "inner_ratio": float(inner_ratio),
                }

    def _ret(found: bool, overlay_img, mask_img, circle):
        if return_circle:
            return found, overlay_img, mask_img, circle
        return found, overlay_img, mask_img

    if best is None or best["ring_ratio"] <= 0.12 or best["inner_ratio"] >= 0.25 or best["score"] <= 0.02:
        return _ret(False, None, mask_raw, None)

    coords = np.column_stack(np.nonzero(mask_raw > 0))
    if coords.size == 0:
        return _ret(False, None, mask_raw, None)

    dy = coords[:, 0] - best["y"]
    dx = coords[:, 1] - best["x"]
    dist = np.sqrt(dx * dx + dy * dy)

    t = max(2.0, best["r"] * 0.18)
    annulus = (dist >= best["r"] - t) & (dist <= best["r"] + t)
    ann_coords = coords[annulus]
    if ann_coords.shape[0] < 12:
        return _ret(False, None, mask_raw, None)

    dy_a = ann_coords[:, 0] - best["y"]
    dx_a = ann_coords[:, 1] - best["x"]
    angles = (np.arctan2(dy_a, dx_a) + 2 * np.pi) % (2 * np.pi)

    bins = 12
    bin_idx = np.floor(angles / (2 * np.pi) * bins).astype(int)
    hist = np.bincount(bin_idx, minlength=bins)

    coverage = int((hist >= 1).sum())
    if coverage < 10:
        return _ret(False, None, mask_raw, None)

    circle = (best["x"], best["y"], best["r"])

    if not debug:
        return _ret(True, None, mask_raw, circle)

    overlay = img_bgr.copy()
    x, y, r = int(best["x"]), int(best["y"]), int(best["r"])
    cv2.circle(overlay, (x, y), r, (0, 255, 0), 2)
    cv2.circle(overlay, (x, y), 2, (0, 255, 0), 2)
    cv2.putText(
        overlay,
        f"r={r} ring={best['ring_ratio']:.2f} inner={best['inner_ratio']:.2f} cov={coverage}/12",
        (max(0, x - 90), max(15, y - r - 8)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.45,
        (0, 255, 0),
        2,
        cv2.LINE_AA,
    )
    return _ret(True, overlay, mask_raw, circle)

def encrypt_file_openssl(in_path: Path, out_path: Path, key_path: Path):
    key_hex = key_path.read_bytes().hex()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "openssl", "enc", "-aes-256-cbc",
            "-K", key_hex,
            "-iv", "00000000000000000000000000000000",
            "-in", str(in_path),
            "-out", str(out_path),
        ],
        check=True,
    )
    
    
def md5_file(file_path: Path) -> str: #added by Tyler
    md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            md5.update(chunk)
    return md5.hexdigest()

def start_qrs_server_and_open_chromium(): #added by Tyler
    qrs_dir = Path.home() / "qrs"
    

    # Start server in background
    env = os.environ.copy()
    env["QRS_DEFAULT_FILE_PATH"] = "/home/user/group-9-team-project-main/red-circle-finder/matched_encrypted.zip"
    
    server_proc = subprocess.Popen(
        ["node", ".output/server/index.mjs"],
        cwd=str(qrs_dir),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,   # keeps it alive if script exits
    )

    # Wait until server responds (or time out)
    server_url = "http://localhost:3000" 
    deadline = time.time() + 5.0
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(server_url, timeout=0.5) as resp:
                if 200 <= resp.status < 500:
                    break
        except Exception:
            time.sleep(0.25)

    # Open Chromium maximized
    subprocess.Popen(
        ["chromium", "--start-maximized", server_url],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    return server_proc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in_dir", required=True, help="Folder with input images")
    ap.add_argument("--out_dir", required=True, help="Folder to write matched (cropped) images into")
    ap.add_argument("--debug_dir", default=None, help="Optional folder to save debug overlays/masks")
    ap.add_argument("--crop", action="store_true", help="If set, save cropped match instead of full image")
    ap.add_argument("--pad_scale", type=float, default=0.45, help="Crop padding as a fraction of radius")
    ap.add_argument("--min_pad", type=int, default=8, help="Minimum crop padding in pixels")
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

        ok, overlay, mask, circle = has_red_circle(img, debug=bool(debug_dir), return_circle=True)

        if ok:
            matches += 1

            if args.crop and circle is not None:
                cx, cy, r = circle
                cropped = crop_around_circle(
                    img,
                    center_x=cx,
                    center_y=cy,
                    radius=r,
                    padding_scale=args.pad_scale,
                    min_padding_px=args.min_pad,
                )
                # Write cropped image and change to jpeg
                jpeg_name = p.stem + ".jpg"
                out_path = out_dir / jpeg_name
                cv2.imwrite(str(out_path), cropped, [cv2.IMWRITE_JPEG_QUALITY, 95])
            else:
                # copy full image
                shutil.copy2(p, out_dir / p.name)

        if debug_dir:
            base = p.stem
            cv2.imwrite(str(debug_dir / f"{base}_mask.png"), mask)

            if overlay is None:
                overlay = img.copy()

            # If cropping is enabled, also save a debug crop preview
            if args.crop and ok and circle is not None:
                cx, cy, r = circle
                crop_preview = crop_around_circle(img, cx, cy, r, args.pad_scale, args.min_pad)
                cv2.imwrite(str(debug_dir / f"{base}_crop.png"), crop_preview)

            cv2.imwrite(str(debug_dir / f"{base}_overlay.png"), overlay)
            

    print(f"Scanned {len(files)} images. Found {matches} matches. Output -> {out_dir}")
    
    # Always encrypt the zip (predetermined key)
    key_file = Path("qr_shared.key")  # adjust if needed
    if not key_file.exists():
        raise FileNotFoundError(f"Key file not found: {key_file}")
        
    # Create MD5 of the matched FOLDER contents (pre-zip, single hash)
    manifest_lines = []
    for p in sorted(out_dir.rglob("*")):
        if p.is_file() and p.name not in {"matched.manifest", "matched.manifest.md5"}:
            rel = p.relative_to(out_dir).as_posix()
            size = p.stat().st_size
            manifest_lines.append(f"{rel}\t{size}")

    manifest_path = out_dir / "matched.manifest"
    manifest_path.write_text("\n".join(manifest_lines) + "\n")
    manifest_md5 = hashlib.md5(manifest_path.read_bytes()).hexdigest()
    (out_dir / "matched.manifest.md5").write_text(f"{manifest_md5}  matched.manifest\n")
    
    
# ENCRYPT THE FOLDER CONTENTS FIRST (creates an encrypted copy folder)
    encrypted_dir = out_dir.parent / (out_dir.name + "_encrypted")
    if encrypted_dir.exists():
        shutil.rmtree(encrypted_dir)
    encrypted_dir.mkdir(parents=True, exist_ok=True)

    for p in sorted(out_dir.rglob("*")):
        if p.is_dir():
            continue
        rel = p.relative_to(out_dir)
        out_p = encrypted_dir / rel
        encrypt_file_openssl(p, out_p, key_file)

    print(f"Encrypted folder contents -> {encrypted_dir}")

    # ZIP THE ENCRYPTED FOLDER
    zip_base = encrypted_dir.parent / encrypted_dir.name
    zip_path = Path(str(zip_base) + ".zip")



    shutil.make_archive(
        base_name=str(zip_base),
        format="zip",
        root_dir=str(encrypted_dir),
    )

    print(f"Created zip: {zip_path}")


    # md5_path = enc_path.with_suffix(enc_path.suffix + ".md5")
    # md5_path.write_text(f"{md5_value} {enc_path.name}\n")
    # print(f"MD5(enc): {md5_value} (saved to {md5_path})")

    start_qrs_server_and_open_chromium()
    
if __name__ == "__main__":
    main()

