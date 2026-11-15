"""IBAN format and mod-97 checksum, against well-known valid and invalid numbers."""

import pytest

from apps.payments.iban import is_valid, normalise

VALID = [
    "IT60X0542811101000000123456",  # Italy
    "DE89370400440532013000",  # Germany
    "FR1420041010050500013M02606",  # France
    "GB82WEST12345698765432",  # United Kingdom
    "ES9121000418450200051332",  # Spain
]


@pytest.mark.parametrize("iban", VALID)
def test_known_valid_ibans_pass(iban):
    assert is_valid(iban)


@pytest.mark.parametrize("iban", VALID)
def test_spaces_and_lowercase_are_accepted(iban):
    grouped = " ".join(iban[i : i + 4] for i in range(0, len(iban), 4))
    assert is_valid(grouped.lower())
    assert normalise(grouped.lower()) == iban


@pytest.mark.parametrize(
    "iban",
    [
        "IT60X0542811101000000123457",  # last digit changed: wrong checksum
        "IT61X0542811101000000123456",  # check digits changed
        "DE89370400440532013001",
        "IT60X054281110100000012345",  # one character short for a valid checksum
        "IT60X05428111010000001234567",  # one character too many
        "12345678901234567890",  # no country letters
        "IT6X0542811101000000123456",  # one check digit only
        "IT60 X054 2811 1010 0000 0123 45!",  # a symbol
        "IT",  # far too short
        "",
        "   ",
    ],
)
def test_wrong_checksum_length_or_shape_is_refused(iban):
    assert not is_valid(iban)


def test_a_single_typo_is_always_caught():
    # Swapping any one digit of a valid IBAN breaks the checksum (mod 97 detects single errors).
    original = "IT60X0542811101000000123456"
    for position in range(4, len(original)):
        char = original[position]
        for replacement in "0123456789":
            if replacement != char and char.isdigit():
                typo = original[:position] + replacement + original[position + 1 :]
                assert not is_valid(typo), typo
