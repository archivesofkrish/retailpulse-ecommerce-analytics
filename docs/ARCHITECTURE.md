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
          | schema, identifiers, finite-number checks
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
       data/processed/ (local exports + pipeline_manifest.json)
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
reports/phase3/ (local tables + figures + report + matching phase3_manifest.json)
```

## Runtime boundaries

- `src/retailpulse/analysis.py` contains reusable transaction, KPI, RFM and cohort logic.
- `scripts/` orchestrates download, the core pipeline, source validation, SQL and Phase 3 analytics.
- `dashboard/app.py` reads the local raw workbook through the shared analysis functions and reads generated Phase 3 outputs for the full-period intelligence tabs.
- `tests/` checks transaction rules, reconciliations, RFM tie handling, cohort right-censoring, temporal embargo logic, and a synthetic core-to-Phase-3 integration run.
- `reports/` and `presentations/` contain aggregated portfolio artefacts. Raw data, processed transaction rows, customer-level tables and local validation JSON are excluded from Git.

## Design principles

1. **Reproducibility:** the source download, transformations, validation and advanced analysis are scripted.
2. **Separation of concerns:** reusable transformations live in `src/`; orchestration in `scripts/`; presentation in `dashboard/`.
3. **Transparent accounting:** returns, cancellations, anonymous sales and other valid rows are separately accounted for.
4. **Responsible modelling:** the inactivity outcome is a historical proxy, with a chronological split, 90-day embargo and explicit limitations.
5. **Multiple consumption paths:** common processed exports support the dashboard, SQL, reports and downstream analysis.
6. **Offline-first development:** a labelled synthetic fixture supports tests and basic dashboard exploration without the full source workbook.
```

## Input contract and validation

The pipeline requires the invoice, stock code, quantity, invoice date, unit price and country fields. Description and customer ID are optional. Header aliases are normalised, but duplicate normalised headers or multiple aliases for one canonical field fail fast rather than silently choosing a column.

Blank invoice/stock-code values, invalid dates, missing numeric transaction values, non-finite quantity or price values, negative unit prices, and non-finite extended line values are excluded from the valid transaction set. Customer IDs are normalised separately: integral numeric values are represented consistently, zero-padded digit strings remain unchanged, non-integral numeric IDs are treated as unavailable, and alphanumeric identifiers are preserved. Unidentified or invalid customer IDs do not remove otherwise valid sales lines from sales-level reporting.

## Data lineage and freshness

Each successful core run writes `data/processed/pipeline_manifest.json` last. It contains a unique run ID, source path, file size, modification signature, SHA-256 digest, reporting dates and core row counts. The manifest is first marked `building`; it becomes `complete` only after all core exports and KPIs have been written.

The Phase 3 runner refuses incomplete core outputs and writes `reports/phase3/phase3_manifest.json` only after its outputs and summary are complete. The dashboard compares the two run IDs and source fingerprints and checks the current source file signature before enabling full-period advanced panels. This prevents a refreshed source workbook or a new core run from being combined with stale Phase 3 reports. Streamlit cache keys include each input file's modification time and size so regenerated outputs are reloaded.

The SQL example runner also requires a completed core manifest before opening the generated CSV views.

## End-to-end smoke validation

The automated suite runs the synthetic demonstration file through the same core pipeline and Phase 3 orchestration used by the project. It verifies that core and advanced manifests agree on the pipeline run ID and source SHA-256 digest, that the expected advanced output files are created, and that a core run explicitly marked as incomplete is rejected by Phase 3. The demo is intentionally too small to guarantee a meaningful inactivity-model backtest; a skipped model is a valid outcome and must not prevent the remaining analytical outputs from being published.

The source's absolute path is retained for audit traceability but is not required to match across deployment environments. Freshness checks compare file size, modification signature and the live SHA-256 content digest. The dashboard caches that digest against the source path and modification signature, so the same read-only workbook can be mounted at a different path inside a container without falsely invalidating its derived analytics.

## Business decision intelligence

Phase 3 feeds validated KPI and analytical summaries into `src/retailpulse/insights.py`. This deterministic rules layer does not call an LLM or infer a recommendation from free-form prompts. It evaluates version-controlled thresholds, emits a structured finding with the exact evidence, trigger rule, recommended action and guardrail, and writes `reports/phase3/business_insights.csv` plus a JSON representation in `phase3_summary.json`. The dashboard renders those records in a dedicated Decision Brief tab. Rule definitions are documented in `docs/BUSINESS_INSIGHTS.md` and covered by unit and end-to-end tests.
