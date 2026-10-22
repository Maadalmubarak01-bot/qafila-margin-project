# Qafila gross margin

Submitted by: Maad Ali Almubarak — academy: @SDAIAAcademy

The task, rules and grading are in [BRIEF.md](BRIEF.md).

```bash
uv sync
uv run python tools/make_data.py          # data/
uv run python run.py                      # data/ -> warehouse/ (DuckDB + Iceberg)
uv run python tools/check.py              # contract self-check
```

> Replace every `<...>` below. Keep it short: tables and a few sentences are enough.

## Design

<A one-line flow: files → raw → staging → silver → gold → Iceberg, with the tool at each step.>

| Model | Layer | Grain (one row per ...) | Materialization |
|---|---|---|---|
| | staging | | |
| `product_cost_history` | silver | | |
| `weekly_margin` | gold | | |
| `price_quarantine` | quality | | |

**How the SCD2 history is built:** <2–3 sentences: how you handle missing weeks, unchanged costs and the correction file.>

**How each order line finds its cost:** <1–2 sentences.>

## Data problems I found

| Problem | Where | Rows affected | What I did |
|---|---|---|---|
| | | | |

## Tests

| Test | On | What it protects against |
|---|---|---|
| | | |

## Re-runs and the correction

<Show that a second run changes nothing, and that after the correction an older Iceberg snapshot still holds the old numbers: snapshot ids and one number before and after.>

## What I'd do next

<What would break first with 100× more data, or with daily supplier files?>

## AI assistance

<None, or what you used and for what.>


## Implementation notes

- `raw`: complete reload of four SQLite source tables and all supplier files on each execution; each price row retains `source_file`.
- `staging`: normalized SKU, Unicode Arabic-Indic numeric conversion, and UTC-to-Riyadh date conversion.
- `quality.price_quarantine`: one row per invalid input row; unknown SKU takes precedence over invalid cost.
- `silver.product_cost_history`: one row per SKU and changed cost; last filename wins per SKU/date; missing weeks carry forward via half-open intervals.
- `gold.weekly_margin`: one row per ISO week × city × category; revenue includes uncosted lines but cost and margin do not.
- `publish`: compares content before overwriting Iceberg; unchanged reruns do not add snapshots; changed content overwrites in place preserving prior snapshots.

## Commands

```bash
uv sync
uv run python tools/make_data.py
uv run python run.py
uv run python tools/check.py
uv run python run.py  # idempotence
uv run python tools/make_data.py --add-correction
uv run python run.py
uv run python tools/check.py
uv run python tools/make_data.py --seed 11 --out data_11
uv run python run.py --data-dir data_11 --warehouse warehouse_11
uv run python tools/check.py --data-dir data_11 --warehouse warehouse_11
```

## AI assistance

AI assistance was used to draft Python and SQL implementation and testing instructions. Review, understand, validate and adapt the code before submitting as individual work.

## Verification still required

Fill in actual data-quality counts, dbt test results, pre/post-correction snapshot IDs and margin figures after running locally. Do not claim unexecuted tests passed.
