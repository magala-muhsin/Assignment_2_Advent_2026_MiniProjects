# Assignment 2: both mini-projects in one folder

Author: MAGALA MUHUSINU REG\_NO S26M19/046. The folder contains two notebooks, reusable src/ modules, tests, synthetic weather JSON, reports and source documentation.

## Folder layout

```text
assignment2\_advent2026/
  README.md
  requirements.txt
  pytest.ini
  .gitignore
  notebooks/project1\_weather.ipynb
  notebooks/project2\_uganda\_tax.ipynb
  src/\_\_init\_\_.py
  src/weather.py
  src/tax\_engine.py
  tests/test\_weather.py
  tests/test\_tax.py
  tests/test\_tax\_properties.py
  data/samples/README.md
  data/samples/geocoding\_kampala.json
  data/samples/geocoding\_empty.json
  data/samples/geocoding\_ambiguous.json
  data/samples/forecast\_kampala.json
  data/samples/met\_kampala.json
  docs/sources.md
  docs/weather\_report.md
  docs/tax\_design.md
  docs/validation.md
  docs/submission\_checklist.md
```

## Setup

Use Python 3.11 or 3.12. Open a terminal inside this extracted folder:

```bash
python -m venv .venv
```

Activate on Windows PowerShell:

```powershell
.venv\\Scripts\\Activate.ps1
```

Activate on Linux/macOS:

```bash
source .venv/bin/activate
```

Then install, test and open Jupyter:

```bash
python -m pip install -r requirements.txt
python -m pytest -q
python -m jupyterlab
```

Open each notebook and choose Restart Kernel and Run All Cells. Do not move individual files out of the repository. Notebooks locate src/ from the root or notebooks/ directory.

## Weather project

LIVE=False is the default. It uses synthetic JSON, not real weather observations or provider-issued forecasts. The fixed offline sample is seven Kampala days; changing LOCATION/DAYS affects live mode only. All manual settings are in one cell: location, email, candidate index, days and live/offline switch. There are no input() prompts. Inspect candidates and change the zero-based index to resolve ambiguity, then rerun.

For actual HTTP, set your genuine university email locally and switch LIVE=True:

```bash
export UNIVERSITY\_EMAIL='YOUR\_REAL\_UNIVERSITY\_EMAIL'
```

Windows PowerShell:

```powershell
$env:UNIVERSITY\_EMAIL='YOUR\_REAL\_UNIVERSITY\_EMAIL'
```

Replace the placeholder; never send it literally. The email check cannot establish ownership; you must supply your real address. Do not commit it or private outputs. Live mode runs urllib and requests, prints actual status/header/time measurements, and retrieves Open-Meteo daily and MET compact forecasts. It never silently falls back to fixtures. Failure demonstrations use mocks. Keep traffic low; a production deployment needs persistent caching/conditional requests beyond this teaching notebook.

The weather notebook includes table, chart, summary, WMO decoding, timezone-aware dates, attribution, qualified MET point-sample comparison, seven assertions and a roughly 1,119-word report. The Markdown copy under docs/ is for convenience.

## Tax model

Only FY 2026/27 is implemented. See sources for the URA resident amendment notice and separate nonresident schedule. Unsupported dates raise NoScheduleForDateError. Base pay is income; allowances are additional taxable earnings, not an amount already included in income. Gross = income + allowances. Employee NSSF is 5%, employer NSSF 10%. Employer NSSF is not an employee deduction. Employee NSSF does not reduce the PAYE base; configured LST does.

Money accepts string, int or Decimal, never float. Exact fractions are retained until settlement. Payroll rounds final PAYE and each NSSF contribution once using whole-UGX ROUND\_HALF\_UP, a project policy rather than a claim about all filing rules. LST must be whole UGX. Annual LST assessment is not implemented.

VAT invoices are tax-exclusive. Standard, zero-rated and exempt categories remain distinct. Input eligibility and taxable-use fractions are explicit caller decisions, not automatically inferred legal entitlement. Negative net VAT is a credit balance, not automatic refund approval. Corporate tax assumes supplied deductions are legally allowable and uses the standard resident-company rate; losses have zero current liability. Sectoral rules and loss carry-forwards are outside scope. This is classroom software, not legal advice.

Extension B is TaxPlanner, a comparison of two salary scenarios using the same Payroll policies. No unsupported dividend model is invented. Tax uses abstraction/inheritance; Payroll and TaxPlanner use composition. Float appears only in the isolated discussion example, not the actual engine.

## Summary of findings

* Synthetic fixture: seven days, minimum 18 °C, maximum 29 °C, precipitation sum 28 mm. These are test data, not actual meteorological findings.
* MET samples are instantaneous, not true daily extrema or observations. Their range comparison is not an accuracy test.
* Resident PAYE at UGX 500,000: UGX 38,250. At UGX 10,000,001: UGX 2,888,250.40 before settlement. Ordinary 30% continues plus an extra 10% on the excess above 10 million.
* Base salary 1,000,000 and LST 10,000 yield PAYE 185,250, employee NSSF 50,000 and net UGX 754,750.
* Salary 1,200,000 with the same LST adds UGX 130,000 net pay; employer NSSF rises separately by UGX 20,000.
* Example VAT output 180,000 less eligible input 90,000 gives UGX 90,000 net VAT. Example corporate tax is UGX 1,200,000 on chargeable income 4,000,000.

## Testing and reproducibility

63 tests passed, including the Hypothesis property tests in tests/test\_tax\_properties.py, and both notebooks executed top to bottom in fresh kernels in default offline mode. The tax notebook also runs the property tests itself. Re-run `python -m pytest -q` in your own environment before submitting. Live HTTP requests (LIVE=True) have not been checked and must be run locally. See docs/validation.md; do not claim unperformed checks.

Each notebook initializes np.random.default\_rng(2026). Hypothesis uses deterministic generation settings. Requirements are compatible version ranges, not a fully resolved lock. Record your local resolved environment after verification if exact package pinning is needed.

## Dependency justification

* requests/pandas/matplotlib: permitted HTTP, tabular data and plotting.
* numpy: required seeded generator and chart bar positions.
* pytest: offline and domain tests.
* hypothesis: explicitly required property-based tests.
* jupyterlab/ipykernel/nbformat: notebooks and their execution.
* nbclient: automated fresh-kernel checks.
* Standard-library abc/dataclasses/decimal/typing/pathlib/math/unittest.mock: abstraction, exact money, hints, file paths, validation and deterministic failure simulation.

## AI-use declaration — personalize accurately

I used an AI assistant partly on this assignment. I did write that first version myself.



In a working session with Claude, the AI also reviewed the project against the brief, reformatted the code, added docstrings and type hints, refactored the PAYE calculation into band tables, corrected the notebook text and README, and helped me fix setup errors when running the notebooks in Jupyter.



I set up the project and the environment on my own computer, ran both notebooks in Jupyter, and ran the weather notebook in live mode (LIVE = True) with my university email. The saved outputs come from my own runs. \[I ran python -m pytest and all 63 tests passed.] \[I checked the tax rates and sources against the URA pages.] \[I read through the code and can explain it.]



I understand that I may be asked to explain any line of the code and if asked to, will be ready.

