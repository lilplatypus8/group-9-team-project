from pathlib import Path
import subprocess

BASE_DIR = Path(r"C:\Users\L&L\Desktop\transmission_images\decrypted_images")
MD5_FILE = BASE_DIR / "matched.manifest.md5"

SERIAL_PORT = "COM4"
BAUD_RATE = 9600


def main():
    if not MD5_FILE.exists():
        raise RuntimeError("manifest.md5 not found")

    md5_string = MD5_FILE.read_text().split()[0].strip()

    if len(md5_string) != 32:
        raise RuntimeError("Invalid MD5 length")

    command = (
        f"$p = New-Object System.IO.Ports.SerialPort '{SERIAL_PORT}',{BAUD_RATE},None,8,one;"
        "$p.Open();"
        f"for($i=0;$i -lt 5;$i++){{$p.Write('{md5_string}'); Start-Sleep -Milliseconds 500}};"
        "$p.Close();"
    )

    subprocess.run(["powershell", "-Command", command])


if __name__ == "__main__":
    main()
