## Tax design, discussion and findings

### Schedule and independent calculation
The implemented year is 1 July 2026–30 June 2027. Resident PAYE follows URA's amendment notice [T1]; nonresident PAYE uses its separate published table [T2]. Unsupported dates raise NoScheduleForDateError, not an invented schedule. The nonresident initial band charges 10%, and subsequent bands are not copied from the resident schedule.

At resident income UGX 10,000,000, tax is UGX 2,888,250. At UGX 10,000,001 it is UGX 2,888,250.40 before settlement: ordinary 30% continues and an extra 10% applies only to the excess. Neither tax on the entire salary nor freezing ordinary tax at the threshold is correct.

income is base monthly pay and allowances are additional taxable cash earnings. Gross is their sum. Avoid supplying inclusive gross and then double-counting allowances. Employee NSSF is 5%, employer NSSF 10% of gross [T4]. Employer NSSF is an employer cost, not an employee deduction. Employee NSSF does not reduce the PAYE base; configured LST does [T3]. Annual LST assessment and instalment schedules are outside scope.

Independent check: salary UGX 1,000,000, LST UGX 10,000, no allowances. Chargeable income is 990,000. PAYE = 33,750 + 30% × (990,000 − 485,000) = 185,250. Employee NSSF is 50,000, employer NSSF 100,000. Net = 1,000,000 − 10,000 − 185,250 − 50,000 = UGX 754,750. The configured LST is a scenario assumption, not a universal monthly liability.

### Why float is unsafe
Binary floats cannot exactly represent many decimal fractions: 0.1 + 0.2 != 0.3. Formatting float 2.675 to two decimals can produce 2.67. Decimal('0.1') + Decimal('0.2') is exactly 0.3, and ROUND_HALF_UP maps Decimal('2.675') to 2.68. The notebook's float example is deliberately isolated from tax arithmetic.

Money rejects floats, bools, NaN and infinity. It implements addition, multiplication, comparison, repr and subtraction. Calculations retain exact fractional shillings; Payroll rounds final PAYE and each NSSF contribution once to whole UGX using ROUND_HALF_UP. LST must already be whole UGX. This is a project settlement policy, not a sourced assertion about all statutory forms. Exact boundary tests retain UGX 0.20 PAYE at income 335,001 instead of rounding away the marginal result.

### Inheritance and composition
Tax is abstract and defines calculate(ctx: TaxContext) -> TaxResult. PAYETax, NSSFTax, VATTax and CorporateTax inherit because they implement interchangeable tax policies. TaxError has InvalidIncomeError and NoScheduleForDateError specializations so callers can distinguish financial validation from unavailable schedules. Invalid inputs never silently become zero-tax results.

Payroll composes PAYE and NSSF rather than inheriting Tax: coordinating multiple liabilities is not a single tax policy. Money and Invoice are value objects, not tax subclasses. Residency differences remain within one cohesive PAYE policy rather than duplicated payroll hierarchies. TaxPlanner composes the same Payroll and compares immutable input contexts.

### VAT, corporate tax and extension B
Invoices are tax-exclusive. Standard VAT is 18%; zero-rated and exempt sales both generate zero output VAT but remain distinct categories [T5]. Input credit requires credit_eligible plus a taxable_use fraction. Purchases wholly attributable to exempt supplies must have no eligible taxable use. The caller determines legal eligibility and statutory apportionment; the model does not infer entitlement merely because an invoice is a purchase.

Example output VAT is 180,000. Eligible purchases of 400,000 yield 72,000 input VAT; a 200,000 purchase with 50% eligible use adds 18,000. The ineligible purchase contributes no credit. Net VAT is UGX 90,000. Negative net VAT is retained as a credit balance, not an automatically approved refund.

Resident corporate tax is the standard 30% of nonnegative revenue less allowable deductions [T6]. Revenue 10,000,000 less deductions 6,000,000 gives tax UGX 1,200,000. Loss carry-forwards, sectoral exemptions and capital-allowance rules are outside scope.

Extension B compares salary 1,000,000 with 1,200,000, holding LST at 10,000. Added salary 200,000 is reduced by 60,000 additional PAYE and 10,000 employee NSSF, leaving 130,000 extra net pay. Employer NSSF rises separately by 20,000. This is a salary-versus-salary comparison, not unsupported dividend modelling.

### Validation and limits
Tests cover both residency schedules at all required edges, money errors, allowances, payroll reconciliation, VAT eligibility/credits, corporate losses and planner differences. A dense deterministic sweep checks nonnegative, monotonic PAYE bounded by income. Mandatory Hypothesis tests generate decimal incomes and residency flags with repeatable settings. Hypothesis is unavailable in the build environment; those tests are included but must be executed locally after installation. The sweep does not replace them. This teaching software is not production tax advice.
