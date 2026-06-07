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

RESET = "\x1b[0m"
BOLD = "\x1b[1m"
DIM = "\x1b[2m"
FG = "\x1b[38;2;220;220;220m"
MUTED = "\x1b[38;2;150;155;160m"
ACCENT = "\x1b[38;2;86;216;201m"
BORDER = "\x1b[38;2;85;91;99m"
PANEL = "\x1b[48;2;24;26;30m"
INPUT = "\x1b[48;2;30;33;39m"
STATUS = "\x1b[38;2;131;199;70m"


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
            self._write("\x1b[?1049h\x1b[?25h\x1b[2 q\x1b[>1u")
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
            self._write("\x1b[<u\x1b[0 q\x1b[?25h\x1b[?1049l")
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

    def draw(self) -> None:
        size = shutil.get_terminal_size((76, 14))
        width = max(48, size.columns)
        height = max(12, size.lines)
        inner_w = width - 4
        input_h = height - 7

        lines = wrap_buffer(self.buffer, inner_w)
        if not lines:
            lines = [""]
        start = max(0, len(lines) - input_h)
        visible = lines[start:]
        cursor_line = max(0, len(lines) - 1 - start)
        cursor_col = min(len(lines[-1]), inner_w)

        out = ["\x1b[H\x1b[2J" + PANEL]
        out.append(BORDER + "╭" + "─" * (width - 2) + "╮")
        title = f"{BOLD}{FG}  LLM Corrector{RESET}{PANEL}"
        chip = f"{STATUS}● Ready{RESET}{PANEL}"
        gap = max(1, width - visible_len("  LLM Corrector") - visible_len("● Ready") - 4)
        out.append(f"{BORDER}│{title}{' ' * gap}{chip}  {BORDER}│")
        out.append(BORDER + "├" + "─" * (width - 2) + "┤")
        for i in range(input_h):
            line = visible[i] if i < len(visible) else ""
            if not self.buffer and i == 0:
                line = f"{DIM}Type text to correct...{RESET}{INPUT}"
            out.append(f"{BORDER}│{INPUT} {fit_ansi(line, inner_w)} {PANEL}{BORDER}│")
        out.append(BORDER + "├" + "─" * (width - 2) + "┤")
        footer = f"{MUTED}{self.status}{RESET}{PANEL}"
        out.append(f"{BORDER}│ {fit_ansi(footer, inner_w)} {BORDER}│")
        out.append(BORDER + "╰" + "─" * (width - 2) + "╯" + RESET)
        cursor_row = 4 + min(cursor_line, input_h - 1)
        cursor_column = 3 + cursor_col
        out.append(f"\x1b[{cursor_row};{cursor_column}H")
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


def visible_len(text: str) -> int:
    length = 0
    in_escape = False
    for char in text:
        if char == "\x1b":
            in_escape = True
            continue
        if in_escape:
            if char.isalpha():
                in_escape = False
            continue
        length += 1
    return length


def fit_ansi(text: str, width: int) -> str:
    out: list[str] = []
    length = 0
    in_escape = False
    for char in text:
        if char == "\x1b":
            in_escape = True
            out.append(char)
            continue
        if in_escape:
            out.append(char)
            if char.isalpha():
                in_escape = False
            continue
        if length >= width:
            break
        out.append(char)
        length += 1
    return "".join(out) + RESET + PANEL + (" " * max(0, width - length))
