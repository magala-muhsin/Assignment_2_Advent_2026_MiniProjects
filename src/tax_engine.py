"""Decimal-only Uganda tax teaching model, FY 2026/27."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, ROUND_HALF_UP


class TaxError(Exception):
    """Base tax-domain error."""


class InvalidIncomeError(TaxError):
    """Invalid financial amount."""


class NoScheduleForDateError(TaxError):
    """No implemented schedule for date."""


def dec(value: str | int | Decimal) -> Decimal:
    """Accept exact finite amounts, never floats/bools."""
    if isinstance(value, (float, bool)):
        raise InvalidIncomeError("Use string, integer or Decimal.")
    try:
        result = Decimal(value)
    except Exception as exc:
        raise InvalidIncomeError("Invalid decimal.") from exc
    if not result.is_finite():
        raise InvalidIncomeError("Amount must be finite.")
    return result


@dataclass(frozen=True)
class Money:
    """Immutable UGX amount, exact until explicit settlement."""

    amount: Decimal

    def __post_init__(self) -> None:
        """Coerce the amount to a validated, finite Decimal."""
        object.__setattr__(self, "amount", dec(self.amount))

    def __add__(self, other: "Money") -> "Money":
        """Return the sum of two Money values."""
        if not isinstance(other, Money):
            return NotImplemented
        return Money(self.amount + other.amount)

    def __sub__(self, other: "Money") -> "Money":
        """Return the difference of two Money values."""
        if not isinstance(other, Money):
            return NotImplemented
        return Money(self.amount - other.amount)

    def __mul__(self, factor: str | int | Decimal) -> "Money":
        """Scale by an exact factor (str, int or Decimal; never float)."""
        return Money(self.amount * dec(factor))

    def __lt__(self, other: "Money") -> bool:
        """Order Money values by amount."""
        if not isinstance(other, Money):
            return NotImplemented
        return self.amount < other.amount

    def rounded(self) -> "Money":
        """Project settlement rule: whole UGX, ROUND_HALF_UP."""
        return Money(self.amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    def __repr__(self) -> str:
        """Show the amount as UGX with thousands separators."""
        return f"UGX {self.amount:,.2f}"


@dataclass(frozen=True)
class Invoice:
    """Tax-exclusive invoice; caller explicitly determines input entitlement."""

    amount: Money
    category: str = "standard"
    direction: str = "sale"
    credit_eligible: bool = True
    taxable_use: Decimal = Decimal("1")

    def __post_init__(self) -> None:
        """Validate amount, category, direction and taxable-use fraction."""
        if self.amount.amount < 0:
            raise InvalidIncomeError("Negative invoice.")
        if self.category not in {"standard", "zero", "exempt"}:
            raise TaxError("Invalid VAT category.")
        if self.direction not in {"sale", "purchase"}:
            raise TaxError("Invalid direction.")
        object.__setattr__(self, "taxable_use", dec(self.taxable_use))
        if not 0 <= self.taxable_use <= 1:
            raise TaxError("Taxable use must be 0–1.")


@dataclass(frozen=True)
class TaxContext:
    """Validated inputs; income is base pay, allowances are additional."""

    income: Money = field(default_factory=lambda: Money(0))
    allowances: Money = field(default_factory=lambda: Money(0))
    lst: Money = field(default_factory=lambda: Money(0))
    deductions: Money = field(default_factory=lambda: Money(0))
    resident: bool = True
    period: date = date(2026, 10, 1)
    invoices: tuple[Invoice, ...] = ()

    def __post_init__(self) -> None:
        """Reject negative amounts and non-boolean residency."""
        for name in ("income", "allowances", "lst", "deductions"):
            if getattr(self, name).amount < 0:
                raise InvalidIncomeError(name + " cannot be negative.")
        if type(self.resident) is not bool:
            raise TaxError("resident must be boolean.")


@dataclass(frozen=True)
class TaxResult:
    """Exact liability and its components."""

    name: str
    amount: Money
    breakdown: dict[str, Money] = field(default_factory=dict)


class Tax(ABC):
    """Common tax policy interface."""

    @abstractmethod
    def calculate(self, ctx: TaxContext) -> TaxResult:
        """Compute tax without mutating context."""
        raise NotImplementedError


def schedule(ctx: TaxContext) -> None:
    """Reject dates outside implemented year."""
    if not date(2026, 7, 1) <= ctx.period <= date(2027, 6, 30):
        raise NoScheduleForDateError("Supported: 2026-07-01 to 2027-06-30.")


# Monthly PAYE bands as (upper limit, tax at band start, band start, marginal rate).
# The last band has no upper limit. The 10% surcharge above 10,000,000 is separate.
Band = tuple[Decimal | None, Decimal, Decimal, Decimal]
RESIDENT_BANDS: tuple[Band, ...] = (
    (Decimal(335000), Decimal(0), Decimal(0), Decimal(0)),
    (Decimal(410000), Decimal(0), Decimal(335000), Decimal("0.20")),
    (Decimal(485000), Decimal(15000), Decimal(410000), Decimal("0.25")),
    (None, Decimal(33750), Decimal(485000), Decimal("0.30")),
)
NONRESIDENT_BANDS: tuple[Band, ...] = (
    (Decimal(335000), Decimal(0), Decimal(0), Decimal("0.10")),
    (Decimal(410000), Decimal(33500), Decimal(335000), Decimal("0.20")),
    (None, Decimal(48500), Decimal(410000), Decimal("0.30")),
)
SURCHARGE_THRESHOLD = Decimal(10000000)
SURCHARGE_RATE = Decimal("0.10")


def band_tax(chargeable: Decimal, bands: tuple[Band, ...]) -> Decimal:
    """Apply a progressive band table to a chargeable monthly income."""
    for upper, base_tax, start, rate in bands:
        if upper is None or chargeable <= upper:
            return base_tax + (chargeable - start) * rate
    raise TaxError("Band table must end with an open band.")


class PAYETax(Tax):
    """Separate monthly resident/nonresident bands plus excess-income surcharge."""

    def calculate(self, ctx: TaxContext) -> TaxResult:
        """Compute PAYE on gross pay less LST, with a surcharge above 10,000,000."""
        schedule(ctx)
        gross = ctx.income + ctx.allowances
        if ctx.lst.amount > gross.amount:
            raise InvalidIncomeError("LST exceeds earnings.")
        chargeable = (gross - ctx.lst).amount
        bands = RESIDENT_BANDS if ctx.resident else NONRESIDENT_BANDS
        banded = band_tax(chargeable, bands)
        surcharge = max(Decimal(0), chargeable - SURCHARGE_THRESHOLD) * SURCHARGE_RATE
        return TaxResult(
            "PAYE",
            Money(banded + surcharge),
            {"chargeable_income": Money(chargeable), "surcharge": Money(surcharge)},
        )


class NSSFTax(Tax):
    """Employee 5%, employer 10% of gross."""

    def calculate(self, ctx: TaxContext) -> TaxResult:
        schedule(ctx)
        gross = ctx.income + ctx.allowances
        return TaxResult("NSSF employee", gross * "0.05", {"employer": gross * "0.10"})


class VATTax(Tax):
    """Invoice VAT ledger with explicit eligible-input apportionment."""

    def calculate(self, ctx: TaxContext) -> TaxResult:
        schedule(ctx)
        output, credit = Money(0), Money(0)
        for i in ctx.invoices:
            vat = i.amount * ("0.18" if i.category == "standard" else "0")
            if i.direction == "sale":
                output = output + vat
            elif i.credit_eligible:
                credit = credit + vat * i.taxable_use
        return TaxResult(
            "Net VAT", output - credit, {"output_vat": output, "input_vat": credit}
        )


class CorporateTax(Tax):
    """Standard resident-company tax; losses have zero current liability."""

    def calculate(self, ctx: TaxContext) -> TaxResult:
        schedule(ctx)
        if not ctx.resident:
            raise TaxError("Resident companies only.")
        chargeable = Money(max(Decimal(0), (ctx.income - ctx.deductions).amount))
        return TaxResult(
            "Corporate income tax",
            chargeable * "0.30",
            {"chargeable_income": chargeable},
        )


class Payroll:
    """Compose tax policies; only LST reduces the PAYE base."""

    def __init__(
        self, paye: PAYETax | None = None, nssf: NSSFTax | None = None
    ) -> None:
        self.paye = paye or PAYETax()
        self.nssf = nssf or NSSFTax()

    def calculate(self, ctx: TaxContext) -> dict[str, Money]:
        """Settle deductions once; employer NSSF never reduces net pay."""
        gross = ctx.income + ctx.allowances
        paye = self.paye.calculate(ctx).amount.rounded()
        n = self.nssf.calculate(ctx)
        employee = n.amount.rounded()
        lst = ctx.lst.rounded()
        if ctx.lst != lst:
            raise TaxError("LST must be whole UGX.")
        net = gross - paye - employee - lst
        if net.amount < 0:
            raise InvalidIncomeError("Deductions exceed earnings.")
        return {
            "gross": gross,
            "lst": lst,
            "paye": paye,
            "nssf_employee": employee,
            "nssf_employer": n.breakdown["employer"].rounded(),
            "net": net,
        }


class TaxPlanner:
    """Extension B: compare two salary scenarios using the same policies."""

    def __init__(self, payroll: Payroll | None = None) -> None:
        self.payroll = payroll or Payroll()

    def compare(self, first: TaxContext, second: TaxContext) -> dict[str, Money]:
        """Return second minus first for each component."""
        a, b = self.payroll.calculate(first), self.payroll.calculate(second)
        return {k: b[k] - a[k] for k in a}
