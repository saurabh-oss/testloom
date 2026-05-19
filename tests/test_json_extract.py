"""Tests for the JSON extraction utility."""

from __future__ import annotations

import pytest

from testloom.core.exceptions import ParseError
from testloom.utils.json_extract import extract_json


def test_clean_json_object():
    raw = '{"test_cases": [{"id": "tc-001", "title": "Login"}]}'
    result = extract_json(raw)
    assert result["test_cases"][0]["id"] == "tc-001"


def test_clean_json_array():
    raw = '[{"id": "tc-001"}, {"id": "tc-002"}]'
    result = extract_json(raw)
    assert len(result) == 2


def test_json_in_backtick_fence_with_language_tag():
    raw = '```json\n{"test_cases": [{"id": "tc-001"}]}\n```'
    result = extract_json(raw)
    assert result["test_cases"][0]["id"] == "tc-001"


def test_json_in_backtick_fence_no_language_tag():
    raw = '```\n{"test_cases": []}\n```'
    result = extract_json(raw)
    assert result["test_cases"] == []


def test_json_with_surrounding_prose():
    raw = (
        "Here are the generated test cases:\n\n"
        '{"test_cases": [{"id": "tc-001", "title": "Test"}]}\n\n'
        "Let me know if you need more!"
    )
    result = extract_json(raw)
    assert result["test_cases"][0]["title"] == "Test"


def test_json_with_leading_explanation_and_fence():
    raw = (
        "Sure! Here are your test cases:\n"
        "```json\n"
        '{"test_cases": [{"id": "tc-001"}]}\n'
        "```\n"
        "Hope this helps."
    )
    result = extract_json(raw)
    assert result["test_cases"][0]["id"] == "tc-001"


def test_raises_parse_error_on_garbage():
    with pytest.raises(ParseError):
        extract_json("This is not JSON at all.")


def test_raises_parse_error_on_empty():
    with pytest.raises(ParseError):
        extract_json("   ")


def test_nested_json_object():
    raw = '{"outer": {"inner": [1, 2, 3]}}'
    result = extract_json(raw)
    assert result["outer"]["inner"] == [1, 2, 3]


def test_json_with_whitespace_padding():
    raw = '\n\n   {"test_cases": []}   \n\n'
    result = extract_json(raw)
    assert result == {"test_cases": []}
