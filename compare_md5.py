#!/usr/bin/env python3

from pathlib import Path
import time
import sys
import subprocess

BASE_DIR = Path("/home/user/group-9-team-project-main/red-circle-finder/matched")

ORIGINAL_MD5 = BASE_DIR / "matched.manifest.md5"
RETURNED_MD5 = BASE_DIR / "returned.manifest.md5"

MATCH_IMAGE = "/home/user/group-9-team-project-main/red-circle-finder/hellothere.jpg"
MISMATCH_IMAGE = "/home/user/group-9-team-project-main/red-circle-finder/youhavefailed.jpg"

FIND_SCRIPT = Path("/home/user/group-9-team-project-main/red-circle-finder/photodiode_receiver.py")


def read_md5(md5_file: Path) -> str:
    return md5_file.read_text().split()[0].strip().lower()


def wait_for_file(file_path: Path, timeout=300):
    start = time.time()
    while not file_path.exists():
        if time.time() - start > timeout:
            return False
        time.sleep(1)
    return True


def open_image(image_path: Path):
    subprocess.Popen(
        ["eom", "--fullscreen", str(image_path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(6)
    subprocess.run(["pkill", "eom"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def restart_find_script():
    subprocess.Popen(
        ["python3", str(FIND_SCRIPT)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )


def main():
    if not ORIGINAL_MD5.exists():
        sys.exit(1)

    for _ in range(2):
        if not wait_for_file(RETURNED_MD5, 300):
            open_image(MISMATCH_IMAGE)
            restart_find_script()
            continue

        original_hash = read_md5(ORIGINAL_MD5)
        returned_hash = read_md5(RETURNED_MD5)

        if original_hash == returned_hash:
            subprocess.Popen(
                ["eom", "--fullscreen", MATCH_IMAGE],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            sys.exit(0)  

        open_image(MISMATCH_IMAGE)
        RETURNED_MD5.unlink(missing_ok=True)
        restart_find_script()

    sys.exit(2)


if __name__ == "__main__":
    main()

