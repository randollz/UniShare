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
    validate_price,
    validate_positive_int,
    validate_choice,
    validate_unit_code,
    validate_email,
    validate_password,
    validate_session_date,
    LISTING_CONDITIONS,
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

# ─────────────────────────────────────────────────────────────
# validate_price
# ─────────────────────────────────────────────────────────────

class TestValidatePrice:
    """Tests for validate_price."""

    def test_valid_integer_price(self):
        value, error = validate_price('50')
        assert value == 50.0
        assert error is None

    def test_valid_decimal_price(self):
        value, error = validate_price('19.99')
        assert value == 19.99
        assert error is None

    def test_price_is_rounded_to_two_decimals(self):
        value, error = validate_price('19.999')
        assert value == 20.0
        assert error is None

    def test_zero_is_valid_when_allowed(self):
        value, error = validate_price('0', allow_zero=True)
        assert value == 0.0
        assert error is None

    def test_zero_rejected_when_not_allowed(self):
        value, error = validate_price('0', allow_zero=False)
        assert value is None
        assert error is not None
        assert 'greater than 0' in error

    def test_negative_price_rejected(self):
        value, error = validate_price('-5')
        assert value is None
        assert 'cannot be negative' in error

    def test_non_numeric_input_rejected(self):
        value, error = validate_price('abc')
        assert value is None
        assert 'must be a number' in error

    def test_empty_string_rejected(self):
        value, error = validate_price('')
        assert value is None
        assert 'required' in error

    def test_none_input_rejected(self):
        value, error = validate_price(None)
        assert value is None
        assert 'required' in error

    def test_whitespace_input_rejected(self):
        value, error = validate_price('   ')
        assert value is None
        assert 'required' in error

    def test_exceeds_max_value_rejected(self):
        value, error = validate_price('100001', max_value=100000)
        assert value is None
        assert 'cannot exceed 100000' in error

    def test_custom_field_label_appears_in_error(self):
        _, error = validate_price('-5', field_label='Reward')
        assert 'Reward' in error


# ─────────────────────────────────────────────────────────────
# validate_positive_int
# ─────────────────────────────────────────────────────────────

class TestValidatePositiveInt:
    """Tests for validate_positive_int."""

    def test_valid_integer(self):
        value, error = validate_positive_int('10', 'Max attendees')
        assert value == 10
        assert error is None

    def test_below_min_rejected(self):
        value, error = validate_positive_int('1', 'Max attendees', min_value=2)
        assert value is None
        assert 'at least 2' in error

    def test_above_max_rejected(self):
        value, error = validate_positive_int('201', 'Max attendees', max_value=200)
        assert value is None
        assert 'at most 200' in error

    def test_exactly_min_is_valid(self):
        value, error = validate_positive_int('2', 'Max attendees', min_value=2)
        assert value == 2
        assert error is None

    def test_exactly_max_is_valid(self):
        value, error = validate_positive_int('200', 'Max attendees', max_value=200)
        assert value == 200
        assert error is None

    def test_non_numeric_rejected(self):
        value, error = validate_positive_int('abc', 'Max attendees')
        assert value is None
        assert 'whole number' in error

    def test_decimal_rejected(self):
        value, error = validate_positive_int('3.5', 'Max attendees')
        assert value is None
        assert 'whole number' in error

    def test_empty_string_rejected(self):
        value, error = validate_positive_int('', 'Max attendees')
        assert value is None
        assert 'required' in error

    def test_none_rejected(self):
        value, error = validate_positive_int(None, 'Max attendees')
        assert value is None
        assert 'required' in error


# ─────────────────────────────────────────────────────────────
# validate_choice
# ─────────────────────────────────────────────────────────────

class TestValidateChoice:
    """Tests for validate_choice."""

    def test_valid_choice_accepted(self):
        value, error = validate_choice('New', 'Condition', LISTING_CONDITIONS)
        assert value == 'New'
        assert error is None

    def test_invalid_choice_rejected(self):
        value, error = validate_choice('Slightly Used', 'Condition', LISTING_CONDITIONS)
        assert 'must be one of' in error

    def test_empty_input_rejected(self):
        _, error = validate_choice('', 'Condition', LISTING_CONDITIONS)
        assert 'required' in error

    def test_none_input_rejected(self):
        _, error = validate_choice(None, 'Condition', LISTING_CONDITIONS)
        assert 'required' in error

    def test_case_sensitive_matching(self):
        # Choice matching is case-sensitive — 'new' should not match 'New'
        _, error = validate_choice('new', 'Condition', LISTING_CONDITIONS)
        assert error is not None

    def test_all_valid_choices_accepted(self):
        for choice in LISTING_CONDITIONS:
            value, error = validate_choice(choice, 'Condition', LISTING_CONDITIONS)
            assert value == choice
            assert error is None, f"Expected {choice} to be valid"

    def test_whitespace_around_valid_choice_accepted(self):
        # The validator strips whitespace before matching
        value, error = validate_choice('  New  ', 'Condition', LISTING_CONDITIONS)
        assert value == 'New'
        assert error is None

# ─────────────────────────────────────────────────────────────
# validate_unit_code
# ─────────────────────────────────────────────────────────────

class TestValidateUnitCode:
    """Tests for validate_unit_code (e.g. 'CITS3403')."""

    def test_standard_unit_code_accepted(self):
        value, error = validate_unit_code('CITS3403')
        assert value == 'CITS3403'
        assert error is None

    def test_lowercase_is_normalized_to_uppercase(self):
        value, error = validate_unit_code('cits3403')
        assert value == 'CITS3403'
        assert error is None

    def test_mixed_case_is_normalized(self):
        value, error = validate_unit_code('CiTs3403')
        assert value == 'CITS3403'
        assert error is None

    def test_whitespace_is_stripped(self):
        value, error = validate_unit_code('  CITS3403  ')
        assert value == 'CITS3403'
        assert error is None

    def test_two_letter_prefix_accepted(self):
        value, error = validate_unit_code('IT1100')
        assert value == 'IT1100'
        assert error is None

    def test_four_letter_prefix_accepted(self):
        value, error = validate_unit_code('MATH1001')
        assert value == 'MATH1001'
        assert error is None

    def test_only_letters_rejected(self):
        _, error = validate_unit_code('CITS')
        assert error is not None

    def test_only_digits_rejected(self):
        _, error = validate_unit_code('3403')
        assert error is not None

    def test_random_word_rejected(self):
        _, error = validate_unit_code('banana')
        assert error is not None

    def test_empty_string_rejected(self):
        _, error = validate_unit_code('')
        assert error == 'Unit code is required.'

    def test_none_rejected(self):
        _, error = validate_unit_code(None)
        assert error == 'Unit code is required.'

    def test_too_few_digits_rejected(self):
        _, error = validate_unit_code('CITS34')
        assert error is not None

    def test_too_many_digits_rejected(self):
        _, error = validate_unit_code('CITS340345')
        assert error is not None

    def test_letters_after_digits_rejected(self):
        _, error = validate_unit_code('CITS3403A')
        assert error is not None


# ─────────────────────────────────────────────────────────────
# validate_email
# ─────────────────────────────────────────────────────────────

class TestValidateEmail:
    """Tests for validate_email."""

    def test_standard_email_accepted(self):
        value, error = validate_email('student@uwa.edu.au')
        assert value == 'student@uwa.edu.au'
        assert error is None

    def test_uppercase_email_normalized_to_lowercase(self):
        value, error = validate_email('STUDENT@UWA.EDU.AU')
        assert value == 'student@uwa.edu.au'
        assert error is None

    def test_whitespace_is_stripped(self):
        value, error = validate_email('  user@example.com  ')
        assert value == 'user@example.com'
        assert error is None

    def test_missing_at_sign_rejected(self):
        _, error = validate_email('notanemail')
        assert 'valid email' in error

    def test_missing_domain_rejected(self):
        _, error = validate_email('user@')
        assert 'valid email' in error

    def test_missing_tld_rejected(self):
        _, error = validate_email('user@domain')
        assert 'valid email' in error

    def test_spaces_inside_rejected(self):
        _, error = validate_email('user name@example.com')
        assert 'valid email' in error

    def test_empty_string_rejected(self):
        _, error = validate_email('')
        assert 'required' in error

    def test_none_rejected(self):
        _, error = validate_email(None)
        assert 'required' in error

    def test_overly_long_email_rejected(self):
        long_email = 'a' * 250 + '@example.com'
        _, error = validate_email(long_email)
        assert error is not None


# ─────────────────────────────────────────────────────────────
# validate_password
# ─────────────────────────────────────────────────────────────

class TestValidatePassword:
    """Tests for validate_password."""

    def test_valid_password_accepted(self):
        value, error = validate_password('mypassword123')
        assert value == 'mypassword123'
        assert error is None

    def test_password_at_minimum_length_accepted(self):
        value, error = validate_password('12345678', min_len=8)
        assert value == '12345678'
        assert error is None

    def test_short_password_rejected(self):
        _, error = validate_password('abc', min_len=8)
        assert 'at least 8 characters' in error

    def test_empty_password_rejected(self):
        _, error = validate_password('')
        assert 'required' in error

    def test_none_rejected(self):
        _, error = validate_password(None)
        assert 'required' in error

    def test_very_long_password_rejected(self):
        long_pw = 'a' * 200
        _, error = validate_password(long_pw, max_len=128)
        assert '128 characters or fewer' in error

    def test_password_with_special_chars_accepted(self):
        value, error = validate_password('p@ssw0rd!#$')
        assert value == 'p@ssw0rd!#$'
        assert error is None

    def test_whitespace_in_password_preserved(self):
        # Unlike other fields, passwords should NOT be stripped
        value, error = validate_password('my password ')
        assert value == 'my password '
        assert error is None


# ─────────────────────────────────────────────────────────────
# validate_session_date
# ─────────────────────────────────────────────────────────────

class TestValidateSessionDate:
    """Tests for validate_session_date (datetime-local format)."""

    def test_valid_datetime_accepted(self):
        value, error = validate_session_date('2026-05-15T14:30')
        assert value == '2026-05-15T14:30'
        assert error is None

    def test_datetime_with_seconds_accepted(self):
        value, error = validate_session_date('2026-05-15T14:30:00')
        assert value == '2026-05-15T14:30:00'
        assert error is None

    def test_empty_rejected(self):
        _, error = validate_session_date('')
        assert 'required' in error

    def test_none_rejected(self):
        _, error = validate_session_date(None)
        assert 'required' in error

    def test_plain_date_rejected(self):
        _, error = validate_session_date('2026-05-15')
        assert error is not None

    def test_random_string_rejected(self):
        _, error = validate_session_date('tomorrow at 3pm')
        assert error is not None

    def test_whitespace_only_rejected(self):
        _, error = validate_session_date('   ')
        assert 'required' in error