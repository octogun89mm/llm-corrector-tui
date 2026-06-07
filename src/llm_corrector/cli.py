from __future__ import annotations

import argparse
import os
import sys

from .llama import LlamaClient
from .paste import focus_target, paste_text
from .tui import CorrectorTui
from .field import correct_focused_field


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Correct text with a local llama.cpp server.")
    parser.add_argument("--print-only", action="store_true", help="print corrected text instead of pasting")
    parser.add_argument("--focused-field", action="store_true", help="correct and replace the focused text field")
    parser.add_argument("--text", help="correct this text without opening the TUI")
    return parser


def correct_and_deliver(text: str, print_only: bool = False) -> str:
    client = LlamaClient.from_env()
    corrected = client.correct(text)

    if print_only:
        print(corrected)
        return corrected

    target = os.environ.get("LLM_CORRECTOR_TARGET_ADDRESS", "")
    focus_target(target)
    paste_text(corrected)
    return corrected


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.focused_field:
        corrected = correct_focused_field()
        if args.print_only:
            print(corrected)
        return 0

    if args.text is not None:
        correct_and_deliver(args.text, print_only=args.print_only)
        return 0

    if not sys.stdin.isatty() or not sys.stdout.isatty():
        data = sys.stdin.read()
        if not data.strip():
            return 2
        correct_and_deliver(data, print_only=args.print_only)
        return 0

    tui = CorrectorTui(lambda text: correct_and_deliver(text, print_only=args.print_only))
    return tui.run()
