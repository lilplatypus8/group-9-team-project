#!/usr/bin/env python3

from pathlib import Path
import time
import os
import select
import sys

SERIAL_PORT = "/dev/serial0"
BASE_DIR = Path("/home/user/group-9-team-project-main/red-circle-finder/matched")
OUTPUT_FILE = BASE_DIR / "returned.manifest.md5"

def main():
    os.system(f"stty -F {SERIAL_PORT} 9600 raw -echo -crtscts")

    md5_chars = []
    start = time.time()
    timeout_seconds = 300

    with open(SERIAL_PORT, "rb", buffering=0) as serial_file:
        serial_fd = serial_file.fileno()

        while len(md5_chars) < 32:
            remaining = timeout_seconds - (time.time() - start)
            if remaining <= 0:
                sys.exit(3)

            readable, _, _ = select.select([serial_fd], [], [], min(0.1, remaining))
            if not readable:
                continue

            byte = os.read(serial_fd, 1)
            if not byte:
                continue

            char = byte.decode(errors="ignore")
            if char in "0123456789abcdefABCDEF":
                md5_chars.append(char.lower())

    md5_string = "".join(md5_chars)
    OUTPUT_FILE.write_text(md5_string + "  matched.manifest\n")
    sys.exit(0)

if __name__ == "__main__":
    main()
