"""Mandatory Hypothesis properties. Install requirements before running."""

from decimal import Decimal
from hypothesis import given, settings, strategies as st
from src.tax_engine import Money, TaxContext, PAYETax

incomes = st.decimals(
    min_value=Decimal("0"),
    max_value=Decimal("1000000000000"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
)


@settings(max_examples=300, derandomize=True)
@given(income=incomes, resident=st.booleans())
def test_bounds(income, resident):
    tax = (
        PAYETax()
        .calculate(TaxContext(income=Money(income), resident=resident))
        .amount.amount
    )
    assert 0 <= tax <= income


@settings(max_examples=300, derandomize=True)
@given(a=incomes, b=incomes, resident=st.booleans())
def test_monotonic(a, b, resident):
    low, high = sorted((a, b))
    p = PAYETax()
    assert (
        p.calculate(TaxContext(income=Money(low), resident=resident)).amount.amount
        <= p.calculate(TaxContext(income=Money(high), resident=resident)).amount.amount
    )
