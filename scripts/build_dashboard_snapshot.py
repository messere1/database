from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db import get_db
from app.services.analysis_service import CrimeAnalysisService
from app.services.sample_data import (
    get_sample_analysis,
    get_sample_conclusions,
    get_sample_overview,
    get_sample_quality,
)

DEFAULT_OUTPUT = PROJECT_ROOT / "app" / "static" / "dashboard_snapshot.json"


def _to_jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)

    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(item) for item in value]

    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass

    return str(value)


def _build_payload_from_db(top_n: int, type_options_top_n: int) -> dict[str, Any]:
    db_gen = get_db()
    db = next(db_gen)
    service = CrimeAnalysisService()

    try:
        payload = service.dashboard_bundle(
            db,
            start_year=None,
            end_year=None,
            crime_type=None,
            top_n=top_n,
            type_options_top_n=type_options_top_n,
        )
    finally:
        db_gen.close()

    return payload


def _build_payload_from_sample(top_n: int, type_options_top_n: int) -> dict[str, Any]:
    type_share = get_sample_analysis("crime_type_share")
    type_share["data"] = type_share.get("data", [])[:top_n]

    district = get_sample_analysis("district_comparison")
    district["data"] = district.get("data", [])[:top_n]

    return {
        "overview": get_sample_overview(),
        "quality": get_sample_quality(),
        "annual": get_sample_analysis("annual_trend"),
        "weekly": get_sample_analysis("weekly_distribution"),
        "hourly": get_sample_analysis("hourly_distribution"),
        "typeShare": type_share,
        "district": district,
        "heatmap": get_sample_analysis("day_hour_heatmap"),
        "yoy": get_sample_analysis("yoy_top_types"),
        "typeOptions": {
            **get_sample_analysis("crime_type_share"),
            "data": get_sample_analysis("crime_type_share").get("data", [])[:type_options_top_n],
        },
        "conclusions": get_sample_conclusions(),
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build static dashboard snapshot JSON for fast default page loading.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help=f"Output snapshot path, default: {DEFAULT_OUTPUT}",
    )
    parser.add_argument("--top-n", type=int, default=10, help="Top N for default charts, default 10")
    parser.add_argument(
        "--type-options-top-n",
        type=int,
        default=30,
        help="Top N for crime type dropdown options, default 30",
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Build snapshot from bundled sample data instead of querying database",
    )
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if args.sample:
        payload = _build_payload_from_sample(top_n=args.top_n, type_options_top_n=args.type_options_top_n)
        source = "sample"
    else:
        payload = _build_payload_from_db(top_n=args.top_n, type_options_top_n=args.type_options_top_n)
        source = "database"

    payload["snapshot_source"] = source
    payload["snapshot_generated_at"] = datetime.now(timezone.utc).isoformat()

    output_path.write_text(json.dumps(_to_jsonable(payload), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[snapshot] Generated: {output_path}")
    print(f"[snapshot] Source: {source}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
