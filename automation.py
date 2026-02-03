import subprocess
import time
from pathlib import Path

QRS_DIR = r"C:\Users\L&L\qrs\qrs-main"
WATCH_DIR = Path(r"C:\Users\L&L\Desktop\transmission_images")
SEVEN_ZIP = r"C:\Program Files\7-Zip\7z.exe"
OPENSSL = r"C:\Program Files\OpenSSL-Win64\bin\openssl.exe"



def wait_until_stable(path: Path, stable_checks: int = 4, interval: float = 0.5) -> None:
    last_size = -1
    same_count = 0

    while same_count < stable_checks:
        size = path.stat().st_size

        if size == last_size:
            same_count += 1
        else:
            same_count = 0
            last_size = size

        time.sleep(interval)


def find_payload_root(extract_dir: Path) -> Path:
    root = extract_dir

    for _ in range(5):
        entries = list(root.iterdir())

        files = [p for p in entries if p.is_file()]
        dirs = [p for p in entries if p.is_dir()]

        if not files and len(dirs) == 1:
            root = dirs[0]
            continue

        break

    return root

PNPM = r"C:\npm\pnpm.cmd"

subprocess.Popen(
    f'cmd /k "{PNPM}" run dev',
    cwd=QRS_DIR,
    shell=True,
)


print("Waiting...")
time.sleep(25)
# Open Chrome at startup
subprocess.Popen('start msedge', shell=True)

print("Startup complete. Waiting for ZIP files...")

seen = {p for p in WATCH_DIR.iterdir() if p.is_file()}

while True:
    print("Waiting...")
    time.sleep(10)

    current = {p for p in WATCH_DIR.iterdir() if p.is_file()}
    new_files = current - seen
    seen = current

    if not new_files:
        continue

    archive = next(iter(new_files))

    #if archive.suffix.lower() != (".7z", ".zip"):
     #   print(f"Skipping non-zip file: {archive.name}")
     #   continue

    print(f"New ZIP detected: {archive.name}")

    wait_until_stable(archive)
    print("ZIP file is stable.")

    # Extract
    extract_dir = archive.with_suffix("")
    extract_dir.mkdir(exist_ok=True)

    print(f"Extracting to: {extract_dir}")

    subprocess.run(
        [SEVEN_ZIP, "x", str(archive), f"-o{extract_dir}", "-y"],
        check=True
    )

    payload_root = find_payload_root(extract_dir)
    print(f"Payload root: {payload_root}")

    # Key file
    key_file = WATCH_DIR / "qr_shared.key"

    if not key_file.exists():
        raise RuntimeError(f"qr_shared.key not found: {key_file}")

    # Output folder
    decrypted_dir = WATCH_DIR / "decrypted_images"
    decrypted_dir.mkdir(exist_ok=True)

    # Find encrypted files
    encrypted_files = [
        p for p in payload_root.rglob("*")
        if p.is_file() and p.suffix.lower() in {".manifest", ".md5", ".jpg"}
    ]

    print("Attempting decryption...")

    if not encrypted_files:
        print("WARNING: No encrypted files found to decrypt.")
        break

    print(f"Found {len(encrypted_files)} encrypted files.")

    # Decrypt
    for enc_path in encrypted_files:
        out_path = decrypted_dir / enc_path.with_suffix("").name

         # Force correct extensions
        if out_path.name == "matched.manifest":
            out_path = out_path.with_suffix(".txt")
        elif out_path.suffix == "":
            out_path = out_path.with_suffix(".jpg")

        print(f"Decrypting: {enc_path.name}")

        key_hex = key_file.read_bytes().hex()

        subprocess.run(
            [
                OPENSSL, "enc", "-d", "-aes-256-cbc",
                "-K", key_hex,
                "-iv", "00000000000000000000000000000000",
                "-in", str(enc_path),
                "-out", str(out_path),
            ],
        check=True
)

    print("Decryption process finished.")
    print(f"Output directory: {decrypted_dir}")

    break
