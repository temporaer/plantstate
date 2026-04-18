"""Utilities for extracting JSON from LLM responses.

LLMs often wrap JSON in markdown code fences or add prose around it.
These helpers robustly extract the first valid JSON object.
"""

from __future__ import annotations

import json
import re


def extract_json(text: str) -> dict | None:
    """Extract first valid JSON object from text.

    Tries in order:
    1. Direct parse
    2. Fenced ```json block
    3. Any fenced ``` block
    4. First balanced {...} object
    """
    # 1. Direct parse
    try:
        result = json.loads(text.strip())
        if isinstance(result, dict):
            return result
    except (json.JSONDecodeError, ValueError):
        pass

    # 2. Fenced ```json block
    match = re.search(r"```json\s*\n?(.*?)```", text, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group(1).strip())
            if isinstance(result, dict):
                return result
        except (json.JSONDecodeError, ValueError):
            pass

    # 3. Any fenced ``` block
    match = re.search(r"```\s*\n?(.*?)```", text, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group(1).strip())
            if isinstance(result, dict):
                return result
        except (json.JSONDecodeError, ValueError):
            pass

    # 4. First balanced {...}
    brace_start = text.find("{")
    if brace_start >= 0:
        depth = 0
        for i in range(brace_start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        result = json.loads(text[brace_start : i + 1])
                        if isinstance(result, dict):
                            return result
                    except (json.JSONDecodeError, ValueError):
                        pass
                    break

    return None
