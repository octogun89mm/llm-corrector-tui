from __future__ import annotations

import os
import select
import shutil
import sys
import termios
import textwrap
import tty
from collections.abc import Callable


KEY_ENTER = "enter"
KEY_SHIFT_ENTER = "shift-enter"
KEY_BACKSPACE = "backspace"
KEY_ESCAPE = "escape"
KEY_CTRL_C = "ctrl-c"


class CorrectorTui:
    def __init__(self, on_submit: Callable[[str], str]) -> None:
        self.on_submit = on_submit
        self.buffer = ""
        self.status = "Enter sends. Shift+Enter adds a newline. Esc cancels."

    def run(self) -> int:
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            self._write("\x1b[?1049h\x1b[?25l\x1b[>1u")
            while True:
                self.draw()
                key = read_key(fd)
                if key in {KEY_ESCAPE, KEY_CTRL_C}:
                    return 130
                if key == KEY_BACKSPACE:
                    self.buffer = self.buffer[:-1]
                elif key == KEY_SHIFT_ENTER:
                    self.buffer += "\n"
                elif key == KEY_ENTER:
                    if not self.buffer.strip():
                        self.status = "Nothing to correct."
                        continue
                    self.status = "Correcting..."
                    self.draw()
                    try:
                        self.on_submit(self.buffer)
                    except Exception as exc:
                        self.status = f"Error: {exc}"
                        continue
                    return 0
                elif isinstance(key, str):
                    self.buffer += key
        finally:
            self._write("\x1b[<u\x1b[?25h\x1b[?1049l")
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

    def draw(self) -> None:
        size = shutil.get_terminal_size((86, 20))
        width = max(40, size.columns)
        height = max(10, size.lines)
        inner_w = width - 4
        input_h = height - 6

        lines = wrap_buffer(self.buffer, inner_w)
        visible = lines[-input_h:] if lines else [""]

        out = ["\x1b[H\x1b[2J"]
        out.append("+" + "-" * (width - 2) + "+")
        title = " local llm corrector "
        out.append("|" + title.ljust(width - 2)[: width - 2] + "|")
        out.append("|" + "-" * (width - 2) + "|")
        for i in range(input_h):
            line = visible[i] if i < len(visible) else ""
            out.append("| " + line.ljust(inner_w)[:inner_w] + " |")
        out.append("|" + "-" * (width - 2) + "|")
        out.append("| " + self.status.ljust(inner_w)[:inner_w] + " |")
        out.append("+" + "-" * (width - 2) + "+")
        self._write("\r\n".join(out))

    def _write(self, text: str) -> None:
        os.write(sys.stdout.fileno(), text.encode("utf-8", errors="replace"))


def read_key(fd: int) -> str:
    data = os.read(fd, 1)
    if data == b"\x03":
        return KEY_CTRL_C
    if data == b"\x1b":
        seq = read_pending(fd)
        full = data + seq
        if full in {b"\x1b[13;2u", b"\x1b[27;2;13~"}:
            return KEY_SHIFT_ENTER
        return KEY_ESCAPE
    if data in {b"\r", b"\n"}:
        return KEY_ENTER
    if data in {b"\x7f", b"\b"}:
        return KEY_BACKSPACE
    return data.decode("utf-8", errors="ignore")


def read_pending(fd: int) -> bytes:
    chunks: list[bytes] = []
    while True:
        ready, _, _ = select.select([fd], [], [], 0.01)
        if not ready:
            break
        chunks.append(os.read(fd, 16))
    return b"".join(chunks)


def wrap_buffer(buffer: str, width: int) -> list[str]:
    if not buffer:
        return [""]
    result: list[str] = []
    for raw_line in buffer.split("\n"):
        if raw_line == "":
            result.append("")
            continue
        wrapped = textwrap.wrap(
            raw_line,
            width=width,
            replace_whitespace=False,
            drop_whitespace=False,
            break_long_words=True,
            break_on_hyphens=False,
        )
        result.extend(wrapped or [""])
    return result
