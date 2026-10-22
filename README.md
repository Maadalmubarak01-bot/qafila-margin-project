# Qafila Gross Margin — Data Engineering Project

**Submitted by:** Maad Ali Almubarak  
**Academy:** @SDAIAAcademy

## Project Overview

This project implements an end-to-end data engineering pipeline for Qafila to calculate weekly gross margins using order transactions and historical supplier costs.

The solution uses Python, DuckDB, dbt and Apache Iceberg. Detailed project requirements are available in [BRIEF.md](BRIEF.md).

## Design

SQLite and supplier CSV files → Python ingestion → DuckDB raw tables → dbt staging → Silver cost history and quality quarantine → Gold weekly margin → Apache Iceberg publication.

| Model | Layer | Grain | Materialization |
|---|---|---|---|
| Supplier prices and source data | Staging | One record per normalized source row | DuckDB dbt models |
| product_cost_history | Silver | One record per SKU and changed cost | DuckDB table and Iceberg |
| weekly_margin | Gold | One record per ISO week, city and category | DuckDB table and Iceberg |
| price_quarantine | Quality | One record per invalid supplier price row | DuckDB table and Iceberg |

### SCD Type 2 Cost History

Supplier prices are standardized and ordered by SKU, effective date and source-file precedence. A new cost-history version is created when the supplier cost changes. Unchanged costs are not duplicated. Missing weeks are covered by carrying forward the previous valid cost until the next change, using exclusive valid-to boundaries.

Supplier correction files are included during subsequent ingestion runs and can revise historical costs. The affected historical versions and downstream margins are recalculated.

### Order-Line Cost Matching

Each eligible order line is matched to the historical cost version for its SKU and order date. The selected version must be effective on or before the order date and remain valid at that time. Unmatched order lines contribute to revenue and the uncosted-line count but not to calculated cost or margin.

## Data Quality

| Problem | Treatment |
|---|---|
| Unknown supplier SKU | Quarantine with unknown_sku reason |
| Invalid or nonpositive supplier cost | Quarantine with invalid_cost reason |
| Arabic-Indic numerals | Normalize to standard numeric representation |
| Duplicate or superseded supplier prices | Apply deterministic precedence and cost-change logic |
| Missing weekly supplier prices | Carry forward the applicable historical cost |
| UTC and Riyadh date differences | Convert timestamps to the business timezone |

The initial sample dataset produced 7 quarantine records. After the supplier correction, the quarantine table still contained 7 records.

## Automated Tests

| Validation | Result |
|---|---|
| Initial project checker | 22/22 passed |
| Checker after supplier correction | 22/22 passed |
| dbt tests after correction | 8 passed, 0 warnings, 0 errors |
| SCD Type 2 history checks | Passed |
| Quarantine validation | Passed |
| Weekly margin contract checks | Passed |
| Pipeline rerun | GitHub Actions step passed |
| Supplier correction | GitHub Actions step passed |

The initial run produced 633 cost-history rows, 165 weekly-margin rows and 7 quarantine rows. After correction, cost history contained 637 rows, with 165 weekly-margin rows and 7 quarantine rows.

## Reruns and Iceberg Snapshots

The pipeline was executed initially, rerun, and executed after generating a supplier correction.

The automated checker reported three snapshots for gold.weekly_margin after the correction workflow. This confirms snapshot creation and retention during the tested sequence.

A separate historical time-travel query and before/after margin-value comparison remain to be documented. Snapshot IDs and numerical comparison evidence should be added after that verification.

## Running the Project

```bash
uv sync
uv run python tools/make_data.py
uv run python run.py
uv run python tools/check.py
```

### Rerun and correction validation

```bash
uv run python run.py
uv run python tools/check.py
uv run python tools/make_data.py --add-correction
uv run python run.py
uv run python tools/check.py
```

### Alternate dataset validation

```bash
uv run python tools/make_data.py --seed 11 --out data_11
uv run python run.py --data-dir data_11 --warehouse warehouse_11
uv run python tools/check.py --data-dir data_11 --warehouse warehouse_11
```

The alternate-seed commands are provided for additional testing; successful execution on that dataset has not yet been verified.

## What I'd Do Next

For 100 times more data, the main challenges would include full-table reload costs, transformation performance and growing historical tables. Incremental ingestion, partition pruning, data-quality monitoring and optimized Iceberg maintenance would become important.

For daily supplier feeds, I would add scheduled orchestration, schema-change monitoring, ingestion audit metadata, late-arriving correction handling and alerts for failed quality checks.

## AI Assistance

AI assistance was used to help draft and review Python and SQL implementation, testing workflows and project documentation. The implementation was executed and checked through GitHub Actions. Any additional independent verification should be documented before final submission.
