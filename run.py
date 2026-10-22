"""Qafila gross margin pipeline: raw files -> DuckDB -> dbt -> Iceberg.

    uv run python run.py --data-dir data --warehouse warehouse

Must work on an empty warehouse folder, and must be safe to run again on the same one.
The grader runs it on a dataset you haven't seen, so never hard-code file names, row counts or SKUs.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

import duckdb
from pyiceberg.catalog.sql import SqlCatalog

DBT_DIR = Path(__file__).resolve().parent / "dbt"


def get_catalog(warehouse: Path) -> SqlCatalog:
    """The Iceberg catalog the grader reads. Don't change the name, the URI or the warehouse."""
    warehouse.mkdir(parents=True, exist_ok=True)
    return SqlCatalog("qafila", uri=f"sqlite:///{(warehouse / 'catalog.db').as_posix()}", warehouse=warehouse.resolve().as_posix())


def ingest(data_dir: Path, db: Path) -> None:
    """Step 1: land the sources in DuckDB, schema `raw`, exactly as they arrive.

    - From data_dir/qafila_oltp.sqlite: orders, order_items, products, stores.
    - Every data_dir/suppliers/prices_*.csv, keeping the file name of each row.

    Running this twice must not duplicate anything.
    """
    import csv
    import sqlite3

    if not (data_dir / "qafila_oltp.sqlite").exists():
        raise FileNotFoundError(data_dir / "qafila_oltp.sqlite")
    with duckdb.connect(str(db)) as con:
        con.execute("CREATE SCHEMA IF NOT EXISTS raw")
        with sqlite3.connect(data_dir / "qafila_oltp.sqlite") as source:
            for table in ("orders", "order_items", "products", "stores"):
                rows = source.execute(f'SELECT * FROM "{table}"')
                names = [x[0] for x in rows.description]
                import pandas as pd
                frame = pd.DataFrame(rows.fetchall(), columns=names)
                con.register("incoming", frame)
                con.execute(f'CREATE OR REPLACE TABLE raw.{table} AS SELECT * FROM incoming')
                con.unregister("incoming")
        prices = []
        for file in sorted((data_dir / "suppliers").glob("prices_*.csv")):
            with file.open(encoding="utf-8-sig", newline="") as stream:
                for row in csv.DictReader(stream):
                    prices.append((file.name, row.get("sku"), row.get("valid_from"),
                                   row.get("unit_cost", row.get("cost_sar"))))
        con.execute("""CREATE OR REPLACE TABLE raw.supplier_prices
                       (source_file VARCHAR, sku VARCHAR, valid_from VARCHAR, raw_cost VARCHAR)""")
        if prices:
            con.executemany("INSERT INTO raw.supplier_prices VALUES (?, ?, ?, ?)", prices)


def transform(db: Path) -> None:
    """Steps 2-4: build and test the dbt project in dbt/ against the DuckDB file.

    dbt runs in its own process: in this one it would keep the DuckDB file open and block publish().
    """
    env = {**os.environ, "QAFILA_DUCKDB": str(db.resolve())}
    cmd = [sys.executable, "-c", "from dbt.cli.main import cli; cli()",
           "build", "--project-dir", str(DBT_DIR), "--profiles-dir", str(DBT_DIR)]
    if subprocess.run(cmd, env=env).returncode != 0:
        raise SystemExit("dbt build failed")


def publish(db: Path, warehouse: Path) -> None:
    """Step 5: publish three dbt models to Iceberg (see the brief for the exact columns).

        silver.product_cost_history   gold.weekly_margin   quality.price_quarantine

    Update existing tables in place, never drop and recreate them: the table's snapshots are
    how we see what a number was before the supplier's correction arrived.
    """
    import pyarrow as pa
    from pyiceberg.exceptions import NoSuchTableError

    catalog = get_catalog(warehouse)
    with duckdb.connect(str(db), read_only=True) as con:
        for namespace, name in (("silver", "product_cost_history"),
                                ("gold", "weekly_margin"),
                                ("quality", "price_quarantine")):
            catalog.create_namespace_if_not_exists(namespace)
            arrow = con.execute(f'SELECT * FROM {namespace}.{name}').fetch_arrow_table()
            # Iceberg's overwrite creates a new snapshot without destroying older snapshots.
            identifier = f"{namespace}.{name}"
            try:
                table = catalog.load_table(identifier)
            except NoSuchTableError:
                table = catalog.create_table(identifier, schema=arrow.schema)
                if arrow.num_rows:
                    table.append(arrow)
                continue
            old = table.scan().to_arrow()
            def canonical(t: pa.Table) -> list[tuple]:
                return sorted(tuple(str(v) for v in row.values()) for row in t.to_pylist())
            if canonical(old) != canonical(arrow):
                table.overwrite(arrow)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data-dir", type=Path, default=Path("data"))
    ap.add_argument("--warehouse", type=Path, default=Path("warehouse"))
    args = ap.parse_args()

    args.warehouse.mkdir(parents=True, exist_ok=True)
    db = args.warehouse / "qafila.duckdb"
    ingest(args.data_dir, db)
    transform(db)
    publish(db, args.warehouse)
    print(f"done: {args.warehouse.resolve()}")


if __name__ == "__main__":
    main()
