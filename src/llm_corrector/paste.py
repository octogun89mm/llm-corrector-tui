from __future__ import annotations

import subprocess
import time


def focus_target(address: str) -> None:
    if not address:
        return
    subprocess.run(
        ["hyprctl", "dispatch", "focuswindow", f"address:{address}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    time.sleep(0.12)


def paste_text(text: str) -> None:
    if not text:
        return
    result = subprocess.run(["wtype", text], check=False)
    if result.returncode != 0:
        raise RuntimeError("wtype failed to type corrected text")
