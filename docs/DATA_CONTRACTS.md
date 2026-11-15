# RetailPulse input data contract

This document defines the transaction-level contract enforced by `src/retailpulse/analysis.py`.

## Required fields

| Canonical field | Accepted source aliases | Requirement |
|---|---|---|
| `invoice` | `invoice`, `invoiceno`, `invoice no`, `invoice_no` | Required; blank values are rejected |
| `stock_code` | `stockcode`, `stock code`, `stock_code` | Required; blank values are rejected |
| `quantity` | `quantity`, `qty` | Required; must parse as a finite number |
| `invoice_date` | `invoicedate`, `invoice date`, `invoice_date` | Required; parsed with day-first date handling |
| `unit_price` | `unitprice`, `unit price`, `price`, `unit_price` | Required; must be finite and non-negative |
| `country` | `country` | Required; blank values are labelled `Unknown` |

The `description` and `customer_id` columns are optional. Missing descriptions become `Unknown product`; missing customer identifiers remain unavailable for customer-level analysis but do not invalidate an otherwise valid sales line.

## Header handling

Headers are trimmed and lower-cased before alias matching. The pipeline fails fast if:

- Two headers become identical after normalisation.
- Multiple aliases are supplied for the same canonical field (for example, both `Invoice` and `InvoiceNo`).

This avoids silently selecting one column when source files contain conflicting fields.

## Row-level validation

A transaction row is excluded from the valid set when it has a blank invoice or stock code, an unparseable date, a missing/non-numeric quantity or price, a non-finite quantity or price, a negative unit price, or a non-finite extended line value (`quantity × unit_price`).

A zero quantity or zero price is retained as an "other valid non-sale/non-return" row, consistent with the existing reconciliation design. Negative quantities and invoices prefixed with `C` are classified as return/cancellation records. Positive quantities and positive prices on non-cancellation invoices are sales lines.

## Customer identifier handling

- Numeric integral IDs are converted to integer strings, so Excel's `123.0` and a CSV value `123` refer to the same ID.
- Digit-only strings retain leading zeroes (for example, `00123` remains `00123`).
- Decimal/scientific numeric representations are normalised when their value is integral.
- Fractional or non-finite numeric identifiers are treated as unavailable rather than rounded into another customer's ID.
- Alphanumeric identifiers are trimmed and preserved.

An invalid customer ID does not cause a valid transaction line to be dropped from sales-level metrics. It is treated like a missing customer ID and excluded from customer-level segmentation and modelling.

## Reconciliation and diagnostics

The pipeline reports counts for invalid core rows, non-finite numeric values, rows dropped because their extended line value was non-finite, invalid customer IDs, missing customer IDs, and the three retained transaction classes. Invalid customer identifiers are not included in the invalid-core-row count because they do not invalidate sales-level data.
