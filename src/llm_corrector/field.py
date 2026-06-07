from __future__ import annotations

import subprocess
import time

from .llama import LlamaClient


def correct_focused_field() -> str:
    previous_clipboard = read_clipboard()
    select_all()
    copy_selection()
    original = read_clipboard().strip()
    if not original:
        restore_clipboard(previous_clipboard)
        raise RuntimeError("focused field copy was empty")

    corrected = LlamaClient.from_env().correct(original)
    if corrected == original:
        restore_clipboard(previous_clipboard)
        return corrected

    write_clipboard(corrected)
    paste_clipboard()
    time.sleep(0.25)
    restore_clipboard(previous_clipboard)
    return corrected


def select_all() -> None:
    subprocess.run(["wtype", "-M", "ctrl", "-k", "a", "-m", "ctrl"], check=True)
    time.sleep(0.08)


def copy_selection() -> None:
    subprocess.run(["wtype", "-M", "ctrl", "-k", "c", "-m", "ctrl"], check=True)
    time.sleep(0.18)


def paste_clipboard() -> None:
    subprocess.run(["wtype", "-M", "ctrl", "-k", "v", "-m", "ctrl"], check=True)


def read_clipboard() -> str | None:
    result = subprocess.run(
        ["wl-paste", "--no-newline", "--type", "text/plain"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def write_clipboard(text: str) -> None:
    subprocess.run(["wl-copy", "--type", "text/plain"], input=text, text=True, check=True)


def restore_clipboard(text: str | None) -> None:
    if text is not None:
        write_clipboard(text)
