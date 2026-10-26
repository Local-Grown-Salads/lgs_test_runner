"""Tests for runner/server utility functions."""

import sys
sys.path.insert(0, ".")

from runner import parse_input, normalize_value, extract_spreadsheet_id


class TestParseInput:
    def test_numbers(self):
        assert parse_input("1, 2") == [1, 2]
        assert parse_input("3.14, 2") == [3.14, 2]

    def test_strings(self):
        assert parse_input('"hello", "world"') == ["hello", "world"]
        assert parse_input("'a', 'b'") == ["a", "b"]

    def test_empty(self):
        assert parse_input("") == []
        assert parse_input("   ") == []

    def test_mixed(self):
        assert parse_input('1, "two", 3.0') == [1, "two", 3.0]


class TestNormalizeValue:
    def test_int_string(self):
        assert normalize_value("42") == 42

    def test_float_string(self):
        assert normalize_value("3.14") == 3.14

    def test_plain_string(self):
        assert normalize_value("hello") == "hello"

    def test_passthrough(self):
        assert normalize_value(42) == 42


class TestExtractSpreadsheetId:
    def test_url(self):
        url = "https://docs.google.com/spreadsheets/d/1kZuKg0KHtIkCM1o7iJk0AMCoPPv2sKD-N5NHA21_LNE/edit"
        assert extract_spreadsheet_id(url) == "1kZuKg0KHtIkCM1o7iJk0AMCoPPv2sKD-N5NHA21_LNE"

    def test_raw_id(self):
        assert extract_spreadsheet_id("abc123") == "abc123"
