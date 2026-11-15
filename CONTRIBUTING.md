# Contributing to RetailPulse

Thanks for considering an improvement. RetailPulse is a portfolio analytics project built around a fixed historical public dataset.

## Development setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Download the source workbook and regenerate the full outputs when working on end-to-end behaviour:

```bash
python scripts/download_data.py
python scripts/run_analysis.py
python scripts/validate_real_data.py
python scripts/run_phase3_analysis.py
```

## Before submitting a change

```bash
python -m compileall -q dashboard scripts src tests
python -W error::DeprecationWarning -m pytest -q
```

For changes to the dashboard, launch `streamlit run dashboard/app.py` and visually inspect the affected section. For changes to the cohort calculations or model split, add regression tests for right-censoring or temporal leakage respectively.

## Data and privacy

- Do not commit the downloaded UCI workbook, processed transaction extracts, customer-level outputs, credentials or local validation JSON.
- Do not present synthetic sample data as UCI results.
- Keep aggregated reports reproducible and clearly identify the source period.
- Preserve explicit limitations around revenue vs profit, historical spend vs CLV, and inactivity vs churn.

## Pull requests

Describe the analytical question, the code or methodology change, the tests run, and any effect on reported metrics. Include updated documentation when definitions or interpretation change.
