from __future__ import annotations

import re

_THINK_OPEN = "<think>"
_THINK_CLOSE = "</think>"


def sanitize_model_text(text: str) -> str:
    sanitized = re.sub(r"<think>.*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL)
    sanitized = re.sub(r"<think>.*$", "", sanitized, flags=re.IGNORECASE | re.DOTALL)
    return sanitized.strip()


class StreamingReasoningFilter:
    def __init__(self) -> None:
        self._buffer = ""
        self._inside_think = False

    def feed(self, text: str) -> str:
        if not text:
            return ""
        self._buffer += text
        output_parts: list[str] = []

        while self._buffer:
            if self._inside_think:
                close_index = self._buffer.lower().find(_THINK_CLOSE)
                if close_index == -1:
                    self._buffer = self._buffer[-(len(_THINK_CLOSE) - 1) :]
                    break
                self._buffer = self._buffer[close_index + len(_THINK_CLOSE) :]
                self._inside_think = False
                continue

            open_index = self._buffer.lower().find(_THINK_OPEN)
            if open_index == -1:
                hold_length = _longest_suffix_prefix(self._buffer.lower(), _THINK_OPEN)
                safe_length = len(self._buffer) - hold_length
                if safe_length > 0:
                    output_parts.append(self._buffer[:safe_length])
                    self._buffer = self._buffer[safe_length:]
                break

            if open_index > 0:
                output_parts.append(self._buffer[:open_index])
            self._buffer = self._buffer[open_index + len(_THINK_OPEN) :]
            self._inside_think = True

        return "".join(output_parts)

    def flush(self) -> str:
        if self._inside_think:
            self._buffer = ""
            return ""
        remainder = sanitize_model_text(self._buffer)
        self._buffer = ""
        return remainder


def _longest_suffix_prefix(text: str, pattern: str) -> int:
    max_len = min(len(text), len(pattern) - 1)
    for size in range(max_len, 0, -1):
        if text.endswith(pattern[:size].lower()):
            return size
    return 0
