# Validation record for rebuilt package

Command: python -m pytest tests/test_tax.py tests/test_weather.py -q

Result: 63 passed (including Hypothesis property tests), one environment requests dependency-compatibility warning. Both notebooks executed top to bottom in separate fresh kernels in default offline mode. Python syntax and notebook schema validated. The sandbox's nonstandard display MIME extras were filtered while saving portable notebook outputs; tables render through HTML to avoid environment-specific Decimal serialization issues. No code-cell failures were suppressed.

Not executed: live HTTP, because the code execution environment has no internet; Hypothesis, because the dependency is unavailable. Install requirements and run the full suite locally, then run weather LIVE=True with a genuine contact email. The deterministic sweep does not replace Hypothesis, and no skip logic hides that dependency.

All bundled weather JSON is synthetic. No real forecast values, network status/header measurements or timings are fabricated. A clean local virtual environment is recommended. The repository was rebuilt and rechecked after the earlier archive was unavailable.
