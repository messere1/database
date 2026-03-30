from __future__ import annotations

import argparse
import os
import re
import sys
from getpass import getpass
from pathlib import Path

from dotenv import load_dotenv
import py_opengauss

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"

IDENT_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def quote_ident(identifier: str) -> str:
    if not IDENT_PATTERN.match(identifier):
        raise ValueError(f"Invalid SQL identifier: {identifier}")
    return f'"{identifier}"'


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build crimes_clean table in Huawei Cloud openGauss from crimes_raw."
    )
    parser.add_argument("--host", default=os.getenv("OG_HOST", ""), help="openGauss host")
    parser.add_argument("--port", type=int, default=int(os.getenv("OG_PORT", "26000")), help="openGauss port")
    parser.add_argument("--database", default=os.getenv("OG_DATABASE", ""), help="Database name")
    parser.add_argument("--user", default=os.getenv("OG_USER", ""), help="Database username")
    parser.add_argument("--password", default=os.getenv("OG_PASSWORD", ""), help="Database password")
    parser.add_argument("--schema", default=os.getenv("OG_SCHEMA", "public"), help="Target schema")
    parser.add_argument("--raw-table", default=os.getenv("OG_TABLE", "crimes_raw"), help="Raw table name")
    parser.add_argument(
        "--clean-table",
        default=os.getenv("OG_ANALYSIS_TABLE", "crimes_clean"),
        help="Clean analysis table name",
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
        "--no-drop",
        action="store_true",
        help="Do not drop clean table before rebuilding",
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


def main() -> int:
    load_dotenv(ENV_FILE)
    args = parse_args()
    ensure_required(args)

    password = resolve_password(args.password)

    schema_sql = quote_ident(args.schema)
    raw_table_sql = quote_ident(args.raw_table)
    clean_table_sql = quote_ident(args.clean_table)
    full_raw = f"{schema_sql}.{raw_table_sql}"
    full_clean = f"{schema_sql}.{clean_table_sql}"

    iri = f"opengauss://{args.user}@{args.host}:{args.port}/{args.database}"

    print(f"[openGauss] Connecting {args.host}:{args.port}/{args.database} as {args.user}")

    db = None
    try:
        db = py_opengauss.open(
            iri,
            password=password,
            sslmode=args.sslmode,
            connect_timeout=args.connect_timeout,
        )

        db.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_sql};")

        if not args.no_drop:
            print(f"[openGauss] Dropping existing table {args.schema}.{args.clean_table}")
            db.execute(f"DROP TABLE IF EXISTS {full_clean};")

        print(f"[openGauss] Creating table {args.schema}.{args.clean_table}")
        db.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {full_clean} (
              clean_id BIGSERIAL PRIMARY KEY,
              source_id BIGINT NULL,
              case_number VARCHAR(32) NULL,
              occurred_at TIMESTAMP NULL,
              year_num SMALLINT NULL,
              month_num SMALLINT NULL,
              day_num SMALLINT NULL,
              hour_num SMALLINT NULL,
              weekday_num SMALLINT NULL,
              block_name VARCHAR(128) NULL,
              iucr VARCHAR(16) NULL,
              primary_type VARCHAR(64) NULL,
              description_text VARCHAR(255) NULL,
              location_description VARCHAR(128) NULL,
              arrest SMALLINT NULL,
              domestic SMALLINT NULL,
              beat INT NULL,
              district INT NULL,
              ward INT NULL,
              community_area INT NULL,
              fbi_code VARCHAR(16) NULL,
              x_coordinate INT NULL,
              y_coordinate INT NULL,
              updated_on TIMESTAMP NULL,
              latitude NUMERIC(10,8) NULL,
              longitude NUMERIC(11,8) NULL,
              source_location_text VARCHAR(64) NULL
            );
            """
        )

        print(f"[openGauss] Building {args.clean_table} from {args.raw_table} ...")
        db.execute(
            f"""
            INSERT INTO {full_clean} (
              source_id,
              case_number,
              occurred_at,
              year_num,
              month_num,
              day_num,
              hour_num,
              weekday_num,
              block_name,
              iucr,
              primary_type,
              description_text,
              location_description,
              arrest,
              domestic,
              beat,
              district,
              ward,
              community_area,
              fbi_code,
              x_coordinate,
              y_coordinate,
              updated_on,
              latitude,
              longitude,
              source_location_text
            )
            SELECT
              CASE WHEN src.id ~ '^[0-9]+$' THEN CAST(src.id AS BIGINT) ELSE NULL END AS source_id,
              NULLIF(BTRIM(src.case_number), '') AS case_number,
              src.parsed_occurred_at AS occurred_at,
              COALESCE(
                CASE WHEN src.year ~ '^[0-9]{{4}}$' THEN CAST(src.year AS SMALLINT) ELSE NULL END,
                CASE
                  WHEN src.parsed_occurred_at IS NOT NULL
                    THEN CAST(EXTRACT(YEAR FROM src.parsed_occurred_at) AS SMALLINT)
                  ELSE NULL
                END
              ) AS year_num,
              CASE
                WHEN src.parsed_occurred_at IS NOT NULL
                  THEN CAST(EXTRACT(MONTH FROM src.parsed_occurred_at) AS SMALLINT)
                ELSE NULL
              END AS month_num,
              CASE
                WHEN src.parsed_occurred_at IS NOT NULL
                  THEN CAST(EXTRACT(DAY FROM src.parsed_occurred_at) AS SMALLINT)
                ELSE NULL
              END AS day_num,
              CASE
                WHEN src.parsed_occurred_at IS NOT NULL
                  THEN CAST(EXTRACT(HOUR FROM src.parsed_occurred_at) AS SMALLINT)
                ELSE NULL
              END AS hour_num,
              CASE
                WHEN src.parsed_occurred_at IS NOT NULL
                  THEN CAST(((EXTRACT(DOW FROM src.parsed_occurred_at)::INT + 6) % 7) + 1 AS SMALLINT)
                ELSE NULL
              END AS weekday_num,
              NULLIF(BTRIM(src.block_name), '') AS block_name,
              NULLIF(BTRIM(src.iucr), '') AS iucr,
              NULLIF(BTRIM(src.primary_type), '') AS primary_type,
              NULLIF(BTRIM(src.description_text), '') AS description_text,
              NULLIF(BTRIM(src.location_description), '') AS location_description,
              CASE LOWER(BTRIM(src.arrest)) WHEN 'true' THEN 1 WHEN 'false' THEN 0 ELSE NULL END AS arrest,
              CASE LOWER(BTRIM(src.domestic)) WHEN 'true' THEN 1 WHEN 'false' THEN 0 ELSE NULL END AS domestic,
              CASE WHEN src.beat ~ '^[0-9]+$' THEN CAST(src.beat AS INT) ELSE NULL END AS beat,
              CASE WHEN src.district ~ '^[0-9]+$' THEN CAST(src.district AS INT) ELSE NULL END AS district,
              CASE WHEN src.ward ~ '^[0-9]+$' THEN CAST(src.ward AS INT) ELSE NULL END AS ward,
              CASE WHEN src.community_area ~ '^[0-9]+$' THEN CAST(src.community_area AS INT) ELSE NULL END AS community_area,
              NULLIF(BTRIM(src.fbi_code), '') AS fbi_code,
              CASE WHEN src.x_coordinate ~ '^[0-9]+$' THEN CAST(src.x_coordinate AS INT) ELSE NULL END AS x_coordinate,
              CASE WHEN src.y_coordinate ~ '^[0-9]+$' THEN CAST(src.y_coordinate AS INT) ELSE NULL END AS y_coordinate,
              src.parsed_updated_on AS updated_on,
              src.lat_num AS latitude,
              src.lon_num AS longitude,
              NULLIF(BTRIM(src.location_text), '') AS source_location_text
            FROM (
              SELECT
                id,
                case_number,
                date_str,
                block_name,
                iucr,
                primary_type,
                description_text,
                location_description,
                arrest,
                domestic,
                beat,
                district,
                ward,
                community_area,
                fbi_code,
                x_coordinate,
                y_coordinate,
                year,
                updated_on,
                latitude,
                longitude,
                location_text,
                to_timestamp(NULLIF(BTRIM(date_str), ''), 'MM/DD/YYYY HH12:MI:SS AM') AS parsed_occurred_at,
                to_timestamp(NULLIF(BTRIM(updated_on), ''), 'MM/DD/YYYY HH12:MI:SS AM') AS parsed_updated_on,
                CASE
                  WHEN NULLIF(BTRIM(latitude), '') ~ '^-?[0-9]+(\\.[0-9]+)?$'
                    THEN CAST(BTRIM(latitude) AS NUMERIC(10,8))
                  ELSE NULL
                END AS lat_num,
                CASE
                  WHEN NULLIF(BTRIM(longitude), '') ~ '^-?[0-9]+(\\.[0-9]+)?$'
                    THEN CAST(BTRIM(longitude) AS NUMERIC(11,8))
                  ELSE NULL
                END AS lon_num
              FROM {full_raw}
            ) src;
            """
        )

        index_statements = [
            f"CREATE INDEX IF NOT EXISTS idx_clean_occurred_at ON {full_clean} (occurred_at);",
            f"CREATE INDEX IF NOT EXISTS idx_clean_year_num ON {full_clean} (year_num);",
            f"CREATE INDEX IF NOT EXISTS idx_clean_month_num ON {full_clean} (month_num);",
            f"CREATE INDEX IF NOT EXISTS idx_clean_weekday_num ON {full_clean} (weekday_num);",
            f"CREATE INDEX IF NOT EXISTS idx_clean_hour_num ON {full_clean} (hour_num);",
            f"CREATE INDEX IF NOT EXISTS idx_clean_primary_type ON {full_clean} (primary_type);",
            f"CREATE INDEX IF NOT EXISTS idx_clean_district ON {full_clean} (district);",
            f"CREATE INDEX IF NOT EXISTS idx_clean_community_area ON {full_clean} (community_area);",
            f"CREATE INDEX IF NOT EXISTS idx_clean_arrest ON {full_clean} (arrest);",
            f"CREATE INDEX IF NOT EXISTS idx_clean_domestic ON {full_clean} (domestic);",
            f"CREATE INDEX IF NOT EXISTS idx_clean_type_year ON {full_clean} (primary_type, year_num);",
        ]
        for statement in index_statements:
            db.execute(statement)

        clean_count_raw = db.prepare(f"SELECT COUNT(*) FROM {full_clean}").first()
        if isinstance(clean_count_raw, (list, tuple)):
          clean_count = int(clean_count_raw[0]) if clean_count_raw else 0
        else:
          clean_count = int(clean_count_raw)
        print(f"[openGauss] Build complete. {args.clean_table} row count: {clean_count}")

    finally:
        if db is not None:
            db.close()

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[openGauss] Prepare clean table failed: {exc}")
        raise SystemExit(1)
