"""Robust JSON extraction from LLM responses.

LLMs frequently wrap JSON in markdown code fences or prepend/append prose.
This module handles all common wrapping patterns with a fallback chain.
"""

from __future__ import annotations

import json
import re
from typing import Any

from testloom.core.exceptions import ParseError


def extract_json(text: str) -> Any:
    """Extract a JSON value from an LLM response string.

    Tries each strategy in order, returning on first success:
    1. Direct parse (already clean JSON)
    2. ```json ... ``` code fence
    3. ``` ... ``` code fence (no language tag)
    4. First {...} or [...] span in the text

    Raises ParseError if all strategies fail.
    """
    text = text.strip()

    # 1. Direct parse — fastest path, handles clean responses
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. ```json ... ``` or ```JSON ... ```
    m = re.search(r"```(?:json|JSON)\s*([\s\S]+?)\s*```", text)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 3. ``` ... ``` (no language tag)
    m = re.search(r"```\s*([\s\S]+?)\s*```", text)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 4. Find the outermost {...} or [...] span
    for open_char, close_char in [('{', '}'), ('[', ']')]:
        start = text.find(open_char)
        if start == -1:
            continue
        # Walk to find matching close
        depth = 0
        in_string = False
        escape_next = False
        for i, ch in enumerate(text[start:], start):
            if escape_next:
                escape_next = False
                continue
            if ch == '\\' and in_string:
                escape_next = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == open_char:
                depth += 1
            elif ch == close_char:
                depth -= 1
                if depth == 0:
                    candidate = text[start:i + 1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        break

    raise ParseError(
        f"Could not extract valid JSON from LLM response. "
        f"First 300 chars: {text[:300]!r}"
    )
