from __future__ import annotations

from pathlib import Path

import qrcode


REPOSITORY_URL = "https://github.com/emmmdty/SARGE"
OUTPUT = Path(__file__).resolve().parents[1] / "assets/github_repository_qr.png"


def main() -> None:
    image = qrcode.make(REPOSITORY_URL)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT)
    print(f"{OUTPUT} -> {REPOSITORY_URL}")


if __name__ == "__main__":
    main()
