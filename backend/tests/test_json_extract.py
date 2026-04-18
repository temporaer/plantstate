"""Tests for JSON extraction from LLM responses."""

from backend.application.json_extract import extract_json


def test_direct_json():
    assert extract_json('{"name": "Tomate"}') == {"name": "Tomate"}


def test_fenced_json():
    text = 'Here is the result:\n```json\n{"name": "Tomate"}\n```\nEnjoy!'
    assert extract_json(text) == {"name": "Tomate"}


def test_generic_fence():
    text = '```\n{"name": "Tomate"}\n```'
    assert extract_json(text) == {"name": "Tomate"}


def test_prose_around_json():
    text = 'Sure, here is the JSON:\n{"name": "Tomate", "language": "de"}\n\nLet me know!'
    result = extract_json(text)
    assert result is not None
    assert result["name"] == "Tomate"


def test_invalid_json():
    assert extract_json("This is not JSON at all") is None


def test_empty():
    assert extract_json("") is None


def test_nested_braces():
    text = '{"name": "T", "rules": [{"task_type": "sow"}]}'
    result = extract_json(text)
    assert result is not None
    assert result["name"] == "T"
    assert len(result["rules"]) == 1
