"""
Unit tests for validators.py

Each validator returns a (cleaned_value, error) tuple:
- On success: error is None, value is the cleaned/coerced input
- On failure: error is a user-facing string, value may be None or partial

Tests are grouped by validator.
"""

import pytest
from validators import (
    validate_required_text,
    validate_optional_text,
)


# ─────────────────────────────────────────────────────────────
# validate_required_text
# ─────────────────────────────────────────────────────────────

class TestValidateRequiredText:
    """Tests for validate_required_text."""

    def test_valid_input_returns_stripped_value(self):
        value, error = validate_required_text('  Hello World  ', 'Title')
        assert value == 'Hello World'
        assert error is None

    def test_normal_input_with_no_whitespace(self):
        value, error = validate_required_text('Hello', 'Title')
        assert value == 'Hello'
        assert error is None

    def test_empty_string_returns_error(self):
        value, error = validate_required_text('', 'Title')
        assert error == 'Title is required.'

    def test_none_input_returns_error(self):
        value, error = validate_required_text(None, 'Title')
        assert error == 'Title is required.'

    def test_whitespace_only_returns_error(self):
        value, error = validate_required_text('   ', 'Title')
        assert error == 'Title is required.'

    def test_field_label_appears_in_error(self):
        _, error = validate_required_text('', 'First name')
        assert 'First name' in error

    def test_exceeds_max_length_returns_error(self):
        long_text = 'a' * 201
        _, error = validate_required_text(long_text, 'Title', max_len=200)
        assert '200 characters or fewer' in error

    def test_exactly_max_length_is_valid(self):
        exact_text = 'a' * 200
        value, error = validate_required_text(exact_text, 'Title', max_len=200)
        assert value == exact_text
        assert error is None

    def test_custom_min_length_rejects_short_input(self):
        _, error = validate_required_text('hi', 'Title', min_len=5)
        assert error == 'Title is required.'


# ─────────────────────────────────────────────────────────────
# validate_optional_text
# ─────────────────────────────────────────────────────────────

class TestValidateOptionalText:
    """Tests for validate_optional_text."""

    def test_empty_string_is_valid(self):
        value, error = validate_optional_text('', 'Bio')
        assert value == ''
        assert error is None

    def test_none_is_valid(self):
        value, error = validate_optional_text(None, 'Bio')
        assert value == ''
        assert error is None

    def test_valid_text_returns_stripped_value(self):
        value, error = validate_optional_text('  hello  ', 'Bio')
        assert value == 'hello'
        assert error is None

    def test_exceeds_max_length_returns_error(self):
        long_text = 'a' * 1001
        _, error = validate_optional_text(long_text, 'Bio', max_len=1000)
        assert error is not None
        assert '1000 characters or fewer' in error

    def test_exactly_max_length_is_valid(self):
        exact_text = 'a' * 1000
        value, error = validate_optional_text(exact_text, 'Bio', max_len=1000)
        assert value == exact_text
        assert error is None

    def test_custom_max_length(self):
        _, error = validate_optional_text('hello world', 'Description', max_len=5)
        assert error is not None
        assert '5 characters or fewer' in error