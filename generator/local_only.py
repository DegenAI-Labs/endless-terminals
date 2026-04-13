"""Shared rules: tasks and tests must not depend on DNS, outbound network, or fake *.example hostnames."""
from __future__ import annotations

import re
from typing import Final

# Phrases that imply tests or tasks expect the public Internet or non-resolvable DNS.
BANNED_SUBSTRINGS: Final[tuple[str, ...]] = (
    "example.com",
    "example.org",
    "example.net",
    "artifacts.example",
    "backup-server.example",
)


def text_suggests_external_network(s: str) -> bool:
    """True if text looks like it requires external DNS / placeholder hosts."""
    if not s:
        return False
    sl = s.lower()
    return any(b in sl for b in BANNED_SUBSTRINGS)


def strip_model_reasoning_preamble(raw: str) -> str:
    """Remove common reasoning wrappers before parsing <task>/<truth> XML."""
    out = raw
    for pat in (
        r"<redacted_thinking>[\s\S]*?</redacted_thinking>",
        r"<thinking>[\s\S]*?</thinking>",
    ):
        out = re.sub(pat, "", out, flags=re.IGNORECASE | re.DOTALL)
    return out
