"""Tests for Idleon number formatting utilities."""

from __future__ import annotations

from decimal import Decimal

from custom_components.idleon.utils.number_format import (
    format_idleon_money,
    format_idleon_number,
    idleon_money_parts,
    idleon_number_parts,
    idleon_raw_value,
)


def test_format_idleon_number_small_values() -> None:
    """Test small values do not receive suffixes."""
    assert format_idleon_number(0) == "0"
    assert format_idleon_number(123) == "123"
    assert format_idleon_number(-123) == "-123"


def test_format_idleon_number_suffixes() -> None:
    """Test common Idleon number suffixes."""
    assert format_idleon_number(1_250) == "1.25K"
    assert format_idleon_number(4_820_000) == "4.82M"
    assert format_idleon_number(913_000_000_000) == "913B"
    assert format_idleon_number(7_410_000_000_000) == "7.41T"
    assert format_idleon_number(52_700_000_000_000_000) == "52.7Qa"
    assert format_idleon_number(91_200_000_000_000_000_000) == "91.2Qi"
    assert format_idleon_number(4_180_000_000_000_000_000_000) == "4.18Sx"


def test_format_idleon_number_large_values_preserve_raw_value() -> None:
    """Test huge values format without losing raw precision."""
    raw_value = "125730617448470844548605638835437568"
    formatted = idleon_number_parts(raw_value)

    assert formatted.formatted == "12.57QQQ"
    assert formatted.raw_value == raw_value
    assert formatted.suffix == "QQQ"
    assert formatted.mantissa == "12.57"


def test_idleon_raw_value_preserves_large_integral_strings() -> None:
    """Test raw conversion does not use JavaScript-sized numeric limits."""
    raw_value = "9007199254740993123456789"

    assert idleon_raw_value(raw_value) == raw_value
    assert idleon_raw_value(Decimal(raw_value)) == raw_value


def test_format_idleon_money_tier_boundaries() -> None:
    """Test Idleon money formatting at requested tier boundaries."""
    assert format_idleon_money(99) == "99 Copper"
    assert format_idleon_money(100) == "1 Silver"
    assert format_idleon_money(10_000) == "1 Gold"
    assert format_idleon_money(1_000_000) == "1 Platinum"
    assert format_idleon_money(10**38) == "1 Polarity"


def test_format_idleon_money_examples() -> None:
    """Test representative money formatting examples."""
    assert format_idleon_money(1_234_000) == "1.23 Platinum"
    assert format_idleon_money(125_000_000) == "1.25 Dementia"
    assert format_idleon_money(34_000_000_000) == "3.4 Void"
    assert format_idleon_money(1257 * 10**20) == "12.57 Tydal"
    assert format_idleon_money(12573 * 10**36) == "125.73 Polarity"


def test_format_idleon_money_above_polarity_preserves_raw_value() -> None:
    """Test values above the known tier table continue using Polarity."""
    raw_value = "125730617448470844548605638835437568000000"
    formatted = idleon_money_parts(raw_value)

    assert formatted.formatted == "1257.31 Polarity"
    assert formatted.raw_value == raw_value
    assert formatted.coin_tier == "Polarity"
    assert formatted.coin_tier_value == str(10**38)


def test_format_idleon_money_negative_values() -> None:
    """Test negative money values format predictably."""
    assert format_idleon_money(-100) == "-1 Silver"
