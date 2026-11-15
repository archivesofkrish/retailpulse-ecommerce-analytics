# RetailPulse architecture

```text
UCI Online Retail II workbook (two Excel worksheets)
                   |
                   v
       scripts/download_data.py
          | provenance manifest
                   |
                   v
           data/raw/ (local)
                   |
                   v
       read_source() / normalise columns
                   |
                   v
          prepare_transactions()
          |        |         |
          |        |         +--> other valid rows
          |        +------------> return / cancellation lines
          +---------------------> positive sales lines
                   |
                   v
          calculate_analytics()
             |       |       |      |
             |       |       |      +--> cohort activity
             |       |       +---------> RFM customer table
             |       +-----------------> product / country tables
             +-------------------------> sales / weekday / hour / KPI tables
                   |
                   v
       data/processed/ (local generated exports)
             |           |             |
             v           v             v
         DuckDB SQL   Streamlit   Executive report + charts

Processed exports
       |
       v
scripts/run_phase3_analysis.py
       |--> customer concentration and segment economics
       |--> repeat purchase and cohort follow-up
       |--> product and country concentration
       |--> chronological 90-day inactivity backtest
       v
reports/phase3/ (local generated tables + figures + report)
```

## Runtime boundaries

- `src/retailpulse/analysis.py` contains reusable transaction, KPI, RFM and cohort logic.
- `scripts/` orchestrates download, the core pipeline, source validation, SQL and Phase 3 analytics.
- `dashboard/app.py` reads the local raw workbook through the shared analysis functions and reads generated Phase 3 outputs for the full-period intelligence tabs.
- `tests/` checks transaction rules, reconciliations, RFM tie handling, cohort right-censoring and temporal embargo logic.
- `reports/` and `presentations/` contain aggregated portfolio artefacts. Raw data, processed transaction rows, customer-level tables and local validation JSON are excluded from Git.

## Design principles

1. **Reproducibility:** the source download, transformations, validation and advanced analysis are scripted.
2. **Separation of concerns:** reusable transformations live in `src/`; orchestration in `scripts/`; presentation in `dashboard/`.
3. **Transparent accounting:** returns, cancellations, anonymous sales and other valid rows are separately accounted for.
4. **Responsible modelling:** the inactivity outcome is a historical proxy, with a chronological split, 90-day embargo and explicit limitations.
5. **Multiple consumption paths:** common processed exports support the dashboard, SQL, reports and downstream analysis.
6. **Offline-first development:** a labelled synthetic fixture supports tests and basic dashboard exploration without the full source workbook.
```
