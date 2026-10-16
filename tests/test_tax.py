"""Exact boundary, validation and integration checks."""

from datetime import date
from decimal import Decimal
import pytest
from src.tax_engine import *


@pytest.mark.parametrize(
    "x,y",
    [
        ("0", "0"),
        ("335000", "0"),
        ("335001", "0.20"),
        ("410000", "15000"),
        ("485000", "33750"),
        ("10000000", "2888250"),
        ("10000001", "2888250.40"),
        ("500000", "38250"),
    ],
)
def test_resident(x, y):
    assert PAYETax().calculate(TaxContext(income=Money(x))).amount == Money(y)


@pytest.mark.parametrize(
    "x,y",
    [
        ("0", "0"),
        ("335000", "33500"),
        ("335001", "33500.20"),
        ("410000", "48500"),
        ("485000", "71000"),
        ("10000000", "2925500"),
        ("10000001", "2925500.40"),
    ],
)
def test_nonresident(x, y):
    assert PAYETax().calculate(
        TaxContext(income=Money(x), resident=False)
    ).amount == Money(y)


def test_allowances_lst():
    assert PAYETax().calculate(
        TaxContext(income=Money(450000), allowances=Money(60000), lst=Money(10000))
    ).amount == Money(38250)


def test_money():
    assert Money("0.1") + Money("0.2") == Money("0.3") and Money(10) * "0.5" == Money(5)
    assert Money(1) < Money(2) and repr(Money(1000)) == "UGX 1,000.00"
    assert Money("0.5").rounded() == Money(1) and Money("-0.5").rounded() == Money(-1)


@pytest.mark.parametrize("bad", [0.1, True, "NaN", "Infinity", "bad"])
def test_invalid_decimal(bad):
    with pytest.raises(InvalidIncomeError):
        Money(bad)


def test_negative_and_lst():
    with pytest.raises(InvalidIncomeError):
        TaxContext(income=Money(-1))
    with pytest.raises(InvalidIncomeError):
        PAYETax().calculate(TaxContext(lst=Money(1)))


@pytest.mark.parametrize("period", [date(2026, 6, 30), date(2027, 7, 1)])
def test_date(period):
    with pytest.raises(NoScheduleForDateError):
        PAYETax().calculate(TaxContext(period=period))


def test_payroll():
    r = Payroll().calculate(TaxContext(income=Money(1000000), lst=Money(10000)))
    assert r["paye"] == Money(185250) and r["nssf_employee"] == Money(50000)
    assert r["net"] == Money(754750) and r["nssf_employer"] == Money(100000)
    assert r["net"] + r["paye"] + r["lst"] + r["nssf_employee"] == r["gross"]


def test_vat():
    invoices = (
        Invoice(Money(1000000)),
        Invoice(Money(200000), "zero"),
        Invoice(Money(300000), "exempt"),
        Invoice(Money(400000), direction="purchase"),
        Invoice(Money(100000), direction="purchase", credit_eligible=False),
        Invoice(Money(200000), direction="purchase", taxable_use=Decimal("0.5")),
    )
    r = VATTax().calculate(TaxContext(invoices=invoices))
    assert (
        r.breakdown["output_vat"] == Money(180000)
        and r.breakdown["input_vat"] == Money(90000)
        and r.amount == Money(90000)
    )


def test_credit():
    assert VATTax().calculate(
        TaxContext(invoices=(Invoice(Money(1000), direction="purchase"),))
    ).amount == Money(-180)


@pytest.mark.parametrize(
    "kwargs", [{"category": "bad"}, {"direction": "bad"}, {"taxable_use": "1.1"}]
)
def test_invoice_invalid(kwargs):
    with pytest.raises(TaxError):
        Invoice(Money(100), **kwargs)


def test_corporate():
    assert CorporateTax().calculate(
        TaxContext(income=Money(10000000), deductions=Money(6000000))
    ).amount == Money(1200000)
    assert CorporateTax().calculate(
        TaxContext(income=Money(10), deductions=Money(20))
    ).amount == Money(0)


def test_planner():
    a = TaxContext(income=Money(1000000), lst=Money(10000))
    b = TaxContext(income=Money(1200000), lst=Money(10000))
    assert TaxPlanner().compare(a, b)["net"] == Money(130000)


def test_abstract():
    with pytest.raises(TypeError):
        Tax()


def test_sweep():
    for resident in (True, False):
        values = sorted(
            set(range(0, 20000001, 7919))
            | {335000, 335001, 410000, 485000, 10000000, 10000001}
        )
        taxes = [
            PAYETax()
            .calculate(TaxContext(income=Money(x), resident=resident))
            .amount.amount
            for x in values
        ]
        assert taxes == sorted(taxes) and all(
            0 <= t <= x for x, t in zip(values, taxes)
        )
