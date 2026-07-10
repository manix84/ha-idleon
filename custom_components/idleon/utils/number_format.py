"""Idleon number formatting helpers.

This module is the canonical place for formatting large Idleon values. Keep
raw values separately on entities whenever precision matters; these helpers are
for display states and display attributes only.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, localcontext
from math import isfinite
from typing import Any

type IdleonNumericInput = str | int | float | Decimal
MAX_SAFE_INTEGER = 9_007_199_254_740_991

IDLEON_NUMBER_TIERS = (
    ("", 1),
    ("K", 10**3),
    ("M", 10**6),
    ("B", 10**9),
    ("T", 10**12),
    ("Q", 10**15),
    ("QQ", 10**18),
    ("QQQ", 10**21),
    ("E24", 10**24),
    ("E26", 10**26),
    ("E28", 10**28),
    ("E30", 10**30),
    ("E32", 10**32),
    ("E34", 10**34),
    ("E36", 10**36),
    ("E38", 10**38),
)

IDLEON_COIN_TIERS = (
    ("Copper", 1),
    ("Silver", 100),
    ("Gold", 10_000),
    ("Platinum", 1_000_000),
    ("Dementia", 100_000_000),
    ("Void", 10_000_000_000),
    ("Lustre", 1_000_000_000_000),
    ("Starfire", 100_000_000_000_000),
    ("Dreadlo", 10_000_000_000_000_000),
    ("Godshard", 10**18),
    ("Sunder", 10**20),
    ("Tydal", 10**22),
    ("Marbiglass", 10**24),
    ("Orberal", 10**26),
    ("Eclipse", 10**28),
    ("Neuro", 10**30),
    ("Isometric", 10**32),
    ("Cyber", 10**34),
    ("Synthesis", 10**36),
    ("Polarity", 10**38),
)


@dataclass(frozen=True, kw_only=True)
class IdleonFormattedNumber:
    """A formatted Idleon number and its exact source value."""

    formatted: str
    raw_value: str
    suffix: str
    mantissa: str


@dataclass(frozen=True, kw_only=True)
class IdleonFormattedMoney:
    """A formatted Idleon money value and selected coin tier metadata."""

    formatted: str
    raw_value: str
    coin_tier: str
    coin_tier_value: str
    amount: str


def parse_idleon_decimal(value: IdleonNumericInput | Any) -> Decimal | None:
    """Parse an Idleon numeric value as a finite Decimal.

    Floats are parsed through ``str(value)`` so their binary representation is not
    exposed in formatted attributes.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, Decimal):
        decimal_value = value
    elif isinstance(value, int):
        decimal_value = Decimal(value)
    elif isinstance(value, float):
        if not isfinite(value):
            return None
        decimal_value = Decimal(str(value))
    else:
        text = str(value).strip().replace(",", "")
        if not text:
            return None
        try:
            decimal_value = Decimal(text)
        except InvalidOperation:
            return None
    return decimal_value if decimal_value.is_finite() else None


def decimal_to_ha_number(value: Decimal) -> int | float | None:
    """Return a Home Assistant-compatible finite numeric state."""
    if not value.is_finite():
        return None
    if value == value.to_integral_value() and abs(value) <= MAX_SAFE_INTEGER:
        return int(value)
    numeric_value = float(value)
    return numeric_value if isfinite(numeric_value) else None


def format_decimal_exact(value: Decimal) -> str:
    """Return a non-exponent decimal string without unnecessary zeroes."""
    text = format(value, "f")
    if "." not in text:
        return text
    return text.rstrip("0").rstrip(".")


def format_decimal_grouped(value: Decimal) -> str:
    """Return a comma-grouped display string without unnecessary zeroes."""
    exact = format_decimal_exact(value)
    sign = ""
    if exact.startswith("-"):
        sign = "-"
        exact = exact[1:]
    integer, separator, fraction = exact.partition(".")
    grouped_integer = f"{int(integer):,}" if integer else "0"
    return f"{sign}{grouped_integer}{separator}{fraction}"


def format_decimal_scientific(
    value: Decimal,
    significant_digits: int = 15,
) -> str:
    """Return normalized scientific notation without float conversion."""
    if value.is_zero():
        return "0"
    with localcontext() as context:
        context.prec = max(significant_digits, 1)
        normalized = +value
    mantissa, exponent = f"{normalized:.{max(significant_digits - 1, 0)}E}".split("E")
    mantissa = mantissa.rstrip("0").rstrip(".")
    exponent_value = int(exponent)
    exponent_sign = "+" if exponent_value >= 0 else "-"
    return f"{mantissa}e{exponent_sign}{abs(exponent_value)}"


def format_idleon_compact(value: Decimal) -> str:
    """Return the established Idleon-style compact representation."""
    return idleon_number_parts(value).formatted


def format_idleon_number(value: int | str | Decimal) -> str:
    """Return an Idleon-style abbreviated number without losing precision."""
    return idleon_number_parts(value).formatted


def idleon_number_parts(value: int | str | Decimal) -> IdleonFormattedNumber:
    """Return formatted Idleon number parts for entity attributes."""
    raw_value = _coerce_integral_decimal(value)
    sign = "-" if raw_value < 0 else ""
    absolute_value = abs(raw_value)
    raw_string = _decimal_integral_string(raw_value)

    if absolute_value < 1000:
        mantissa = _decimal_integral_string(absolute_value)
        return IdleonFormattedNumber(
            formatted=f"{sign}{mantissa}",
            raw_value=raw_string,
            suffix="",
            mantissa=f"{sign}{mantissa}",
        )

    suffix, divisor = _number_tier_for_value(absolute_value)
    mantissa = _format_scaled_decimal(absolute_value / divisor)
    signed_mantissa = f"{sign}{mantissa}"
    return IdleonFormattedNumber(
        formatted=f"{signed_mantissa}{suffix}",
        raw_value=raw_string,
        suffix=suffix,
        mantissa=signed_mantissa,
    )


def format_idleon_money(value: int | str | Decimal) -> str:
    """Return Idleon money formatted from a raw copper coin value."""
    return idleon_money_parts(value).formatted


def idleon_money_parts(value: int | str | Decimal) -> IdleonFormattedMoney:
    """Return formatted Idleon money parts for entity attributes."""
    raw_value = _coerce_integral_decimal(value)
    sign = "-" if raw_value < 0 else ""
    absolute_value = abs(raw_value)
    tier_name, tier_value = _coin_tier_for_value(absolute_value)
    amount = _format_scaled_decimal(absolute_value / Decimal(tier_value))
    signed_amount = f"{sign}{amount}"
    return IdleonFormattedMoney(
        formatted=f"{signed_amount} {tier_name}",
        raw_value=_decimal_integral_string(raw_value),
        coin_tier=tier_name,
        coin_tier_value=str(tier_value),
        amount=signed_amount,
    )


def idleon_raw_value(value: int | str | Decimal | Any) -> str:
    """Return a raw value string while preserving source notation where useful."""
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return "0"
        decimal_value = parse_idleon_decimal(text)
        if decimal_value is None:
            return "0"
        if "e" in text.lower():
            return text
        return format_decimal_exact(decimal_value)
    if isinstance(value, float):
        decimal_value = parse_idleon_decimal(value)
        return str(value) if decimal_value is not None else "0"
    decimal_value = parse_idleon_decimal(value)
    if decimal_value is None:
        return "0"
    if decimal_value == decimal_value.to_integral_value():
        return _decimal_integral_string(decimal_value)
    return format_decimal_exact(decimal_value)


def _coin_tier_for_value(value: Decimal) -> tuple[str, int]:
    """Return the highest known coin tier less than or equal to value."""
    selected = IDLEON_COIN_TIERS[0]
    for tier in IDLEON_COIN_TIERS:
        if value >= tier[1]:
            selected = tier
        else:
            break
    return selected


def _number_tier_for_value(value: Decimal) -> tuple[str, Decimal]:
    """Return the highest known Idleon number tier for value."""
    selected_suffix, selected_value = IDLEON_NUMBER_TIERS[0]
    for suffix, tier_value in IDLEON_NUMBER_TIERS:
        if value >= tier_value:
            selected_suffix = suffix
            selected_value = tier_value
        else:
            break
    return selected_suffix, Decimal(selected_value)


def _coerce_integral_decimal(value: int | str | Decimal) -> Decimal:
    """Return value as an integral Decimal without passing through float."""
    decimal_value = parse_idleon_decimal(value)
    if decimal_value is None:
        return Decimal(0)
    return decimal_value.to_integral_value()


def _decimal_integral_string(value: Decimal) -> str:
    """Return an integral Decimal string without scientific notation."""
    return format(value, "f").split(".", maxsplit=1)[0]


def _format_scaled_decimal(value: Decimal) -> str:
    """Return a compact decimal string with up to two fractional digits."""
    with localcontext() as context:
        context.prec = max(len(value.as_tuple().digits) + 2, 28)
        quantized = value.quantize(Decimal("0.01"))
    return format(quantized, "f").rstrip("0").rstrip(".")
