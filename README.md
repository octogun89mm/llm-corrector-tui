# llm-corrector-tui

Small terminal TUI for Hyprland that:

- opens from a keybind in a floating terminal window
- accepts multiline text
- uses `Shift+Enter` for a newline and `Enter` to send
- sends text to a local llama.cpp OpenAI-compatible server
- refocuses the previously active window and types the corrected text

## Requirements

- Hyprland
- `ghostty`
- `python3`
- `wtype`
- llama.cpp server with `/v1/models` and `/v1/chat/completions`

The defaults target `http://127.0.0.1:8080/v1` and start `llama.service` if no server is reachable.

## Run

```bash
/home/juju/Projects/llm-corrector-tui/bin/llm-corrector-launch
```

## Configuration

Environment variables:

```bash
LLM_CORRECTOR_BASE_URL=http://127.0.0.1:8080/v1
LLM_CORRECTOR_MODEL=auto
LLM_CORRECTOR_START_CMD="systemctl --user start llama.service"
LLM_CORRECTOR_START_TIMEOUT=45
LLM_CORRECTOR_TEMPERATURE=0.1
LLM_CORRECTOR_MAX_TOKENS=512
```

Set `LLM_CORRECTOR_START_CMD=""` to test the "model not already running" path without starting anything.

## Hyprland

Example:

```ini
bindd = $mainMod CONTROL, semicolon, Correct text with local LLM, exec, /home/juju/Projects/llm-corrector-tui/bin/llm-corrector-launch

windowrule {
    name = llm-corrector-float
    match:class = llm-corrector
    float = true
    size = 760 360
    center = true
    stay_focused = true
}
```

## Notes

`Shift+Enter` depends on the terminal reporting modified enter keys. The launcher enables this in Ghostty by default; the TUI also requests Kitty keyboard protocol as a fallback for terminals that support it.
