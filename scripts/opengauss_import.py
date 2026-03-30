from __future__ import annotations

import argparse
import os
import re
import sys
from getpass import getpass
from pathlib import Path
from typing import Iterator

from dotenv import load_dotenv
import py_opengauss

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"

DEFAULT_CSV_PATH = Path(r"D:\database\crimes-2001-to-present\Crimes_-_2001_to_Present.csv")

COLUMNS = [
    "id",
    "case_number",
    "date_str",
    "block_name",
    "iucr",
    "primary_type",
    "description_text",
    "location_description",
    "arrest",
    "domestic",
    "beat",
    "district",
    "ward",
    "community_area",
    "fbi_code",
    "x_coordinate",
    "y_coordinate",
    "year",
    "updated_on",
    "latitude",
    "longitude",
    "location_text",
]

IDENT_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def quote_ident(identifier: str) -> str:
    if not IDENT_PATTERN.match(identifier):
        raise ValueError(f"Invalid SQL identifier: {identifier}")
    return f'"{identifier}"'


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import Chicago Crimes CSV into Huawei Cloud openGauss (create table + COPY)."
    )
    parser.add_argument("--host", default=os.getenv("OG_HOST", ""), help="openGauss host")
    parser.add_argument("--port", type=int, default=int(os.getenv("OG_PORT", "26000")), help="openGauss port")
    parser.add_argument("--database", default=os.getenv("OG_DATABASE", ""), help="Database name")
    parser.add_argument("--user", default=os.getenv("OG_USER", ""), help="Database username")
    parser.add_argument("--password", default=os.getenv("OG_PASSWORD", ""), help="Database password")
    parser.add_argument("--schema", default=os.getenv("OG_SCHEMA", "public"), help="Target schema")
    parser.add_argument("--table", default=os.getenv("OG_TABLE", "crimes_raw"), help="Target table")
    parser.add_argument(
        "--csv",
        dest="csv_path",
        default=os.getenv("OG_CSV_PATH", str(DEFAULT_CSV_PATH)),
        help="CSV path",
    )
    parser.add_argument(
        "--sslmode",
        default=os.getenv("OG_SSLMODE", "prefer"),
        choices=["disable", "allow", "prefer", "require", "verify-ca", "verify-full"],
        help="SSL mode",
    )
    parser.add_argument(
        "--connect-timeout",
        type=int,
        default=int(os.getenv("OG_CONNECT_TIMEOUT", "15")),
        help="Connection timeout in seconds",
    )
    parser.add_argument(
        "--no-truncate",
        action="store_true",
        help="Do not truncate table before COPY",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=0,
        help="Import only first N data rows (excluding header). 0 means import all rows.",
    )
    return parser.parse_args()


def ensure_required(args: argparse.Namespace) -> None:
    missing: list[str] = []
    for field in ["host", "database", "user"]:
        if not getattr(args, field):
            missing.append(field)

    if missing:
        raise ValueError("Missing required arguments: " + ", ".join(missing))


def resolve_password(raw_password: str) -> str:
    if raw_password:
        return raw_password

    if not sys.stdin.isatty():
        raise ValueError("Password is required. Set OG_PASSWORD in .env or pass --password.")

    password = getpass("openGauss password: ")
    if not password:
        raise ValueError("Password cannot be empty.")
    return password


def iter_csv_lines(csv_path: Path, max_rows: int) -> Iterator[bytes]:
    with csv_path.open("rb") as csv_file:
        for index, line in enumerate(csv_file):
            # Keep header for COPY ... HEADER true
            if index == 0:
                yield line
                continue

            if max_rows > 0 and index > max_rows:
                break

            yield line


def main() -> int:
    load_dotenv(ENV_FILE)
    args = parse_args()
    ensure_required(args)

    csv_path = Path(args.csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    password = resolve_password(args.password)

    schema_sql = quote_ident(args.schema)
    table_sql = quote_ident(args.table)
    full_table = f"{schema_sql}.{table_sql}"

    column_defs = ",\n  ".join(f"{quote_ident(col)} TEXT NULL" for col in COLUMNS)
    create_schema_sql = f"CREATE SCHEMA IF NOT EXISTS {schema_sql};"
    create_table_sql = (
        f"CREATE TABLE IF NOT EXISTS {full_table} (\n"
        f"  {column_defs}\n"
        ");"
    )

    copy_columns = ", ".join(quote_ident(col) for col in COLUMNS)
    copy_sql = (
        f"COPY {full_table} ({copy_columns}) "
        "FROM STDIN WITH (FORMAT csv, HEADER true, DELIMITER ',', QUOTE '\"', ESCAPE '\"');"
    )

    truncate_sql = f"TRUNCATE TABLE {full_table};"
    count_sql = f"SELECT COUNT(*) FROM {full_table};"

    print(f"[openGauss] Connecting {args.host}:{args.port}/{args.database} as {args.user}")
    iri = f"opengauss://{args.user}@{args.host}:{args.port}/{args.database}"

    db = None
    try:
        db = py_opengauss.open(
            iri,
            password=password,
            sslmode=args.sslmode,
            connect_timeout=args.connect_timeout,
        )

        db.execute(create_schema_sql)
        db.execute(create_table_sql)

        if not args.no_truncate:
            print(f"[openGauss] Truncating table {args.schema}.{args.table}")
            db.execute(truncate_sql)

        print(f"[openGauss] COPY importing from {csv_path}")
        if args.max_rows > 0:
            print(f"[openGauss] Import mode: first {args.max_rows} rows")
        copy_stmt = db.prepare(copy_sql)
        copied_rows = copy_stmt.load_rows(iter_csv_lines(csv_path, args.max_rows))

        row_count = db.prepare(count_sql).first()
        print(f"[openGauss] COPY loaded rows: {copied_rows}")
    finally:
        if db is not None:
            db.close()

    print(f"[openGauss] Import success. Table {args.schema}.{args.table} row count: {row_count}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[openGauss] Import failed: {exc}")
        raise SystemExit(1)
