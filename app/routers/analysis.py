from copy import deepcopy
from threading import Lock
from time import time
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import AnalysisResponse, ConclusionResponse
from app.services.analysis_service import CrimeAnalysisService
from app.services.sample_data import get_sample_analysis, get_sample_conclusions, get_sample_overview, get_sample_quality

router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])
service = CrimeAnalysisService()

BUNDLE_CACHE_TTL_SECONDS = 90
BUNDLE_CACHE_MAX_ITEMS = 64
_dashboard_bundle_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_dashboard_bundle_cache_lock = Lock()


def _dashboard_bundle_cache_key(
    start_year: int | None,
    end_year: int | None,
    crime_types: list[str],
    top_n: int,
) -> str:
    normalized_crime_types = sorted({item.strip().upper() for item in crime_types if item and item.strip()})
    return f"{start_year}|{end_year}|{','.join(normalized_crime_types)}|{top_n}"


def _merge_crime_types(crime_types: list[str] | None, crime_type: str | None) -> list[str]:
    merged: list[str] = []
    if isinstance(crime_types, list):
        merged.extend(crime_types)
    if crime_type:
        merged.append(crime_type)

    normalized: list[str] = []
    seen: set[str] = set()
    for value in merged:
        item = str(value).strip()
        if not item or item in seen:
            continue
        seen.add(item)
        normalized.append(item)

    return normalized


def _get_cached_dashboard_bundle(cache_key: str) -> dict[str, Any] | None:
    with _dashboard_bundle_cache_lock:
        cached = _dashboard_bundle_cache.get(cache_key)
        if not cached:
            return None
        created_at, payload = cached
        if time() - created_at > BUNDLE_CACHE_TTL_SECONDS:
            _dashboard_bundle_cache.pop(cache_key, None)
            return None
        return deepcopy(payload)


def _set_cached_dashboard_bundle(cache_key: str, payload: dict[str, Any]) -> None:
    with _dashboard_bundle_cache_lock:
        if len(_dashboard_bundle_cache) >= BUNDLE_CACHE_MAX_ITEMS:
            expired_keys = [
                key
                for key, (created_at, _) in _dashboard_bundle_cache.items()
                if time() - created_at > BUNDLE_CACHE_TTL_SECONDS
            ]
            for key in expired_keys:
                _dashboard_bundle_cache.pop(key, None)

        if len(_dashboard_bundle_cache) >= BUNDLE_CACHE_MAX_ITEMS:
            oldest_key = min(_dashboard_bundle_cache.items(), key=lambda item: item[1][0])[0]
            _dashboard_bundle_cache.pop(oldest_key, None)

        _dashboard_bundle_cache[cache_key] = (time(), deepcopy(payload))


@router.get("/dashboard-bundle")
def dashboard_bundle(
    start_year: int | None = Query(default=None, ge=2001, le=2100),
    end_year: int | None = Query(default=None, ge=2001, le=2100),
    crime_types: list[str] | None = Query(default=None),
    crime_type: str | None = Query(default=None, include_in_schema=False),
    top_n: int = Query(default=10, ge=3, le=30),
    sample: bool = Query(default=False, description="Return sample data"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if sample:
        type_share = get_sample_analysis("crime_type_share")
        type_share["data"] = type_share.get("data", [])[:top_n]

        district = get_sample_analysis("district_comparison")
        district["data"] = district.get("data", [])[:top_n]

        type_options = get_sample_analysis("crime_type_share")
        type_options["data"] = type_options.get("data", [])[:30]

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
            "typeOptions": type_options,
            "conclusions": get_sample_conclusions(),
        }

    selected_crime_types = _merge_crime_types(crime_types=crime_types, crime_type=crime_type)

    cache_key = _dashboard_bundle_cache_key(
        start_year=start_year,
        end_year=end_year,
        crime_types=selected_crime_types,
        top_n=top_n,
    )
    cached = _get_cached_dashboard_bundle(cache_key)
    if cached is not None:
        return cached

    payload = service.dashboard_bundle(
        db,
        start_year=start_year,
        end_year=end_year,
        crime_types=selected_crime_types,
        top_n=top_n,
        type_options_top_n=30,
    )
    _set_cached_dashboard_bundle(cache_key, payload)
    return payload


@router.get("/annual-trend", response_model=AnalysisResponse)
def annual_trend(
    start_year: int | None = Query(default=None, ge=2001, le=2100),
    end_year: int | None = Query(default=None, ge=2001, le=2100),
    crime_types: list[str] | None = Query(default=None),
    crime_type: str | None = Query(default=None, include_in_schema=False),
    sample: bool = Query(default=False, description="Return sample data"),
    db: Session = Depends(get_db),
) -> AnalysisResponse:
    if sample:
        return get_sample_analysis("annual_trend")
    selected_crime_types = _merge_crime_types(crime_types=crime_types, crime_type=crime_type)
    return service.annual_trend(db, start_year=start_year, end_year=end_year, crime_types=selected_crime_types)


@router.get("/weekly-distribution", response_model=AnalysisResponse)
def weekly_distribution(
    start_year: int | None = Query(default=None, ge=2001, le=2100),
    end_year: int | None = Query(default=None, ge=2001, le=2100),
    crime_types: list[str] | None = Query(default=None),
    crime_type: str | None = Query(default=None, include_in_schema=False),
    sample: bool = Query(default=False, description="Return sample data"),
    db: Session = Depends(get_db),
) -> AnalysisResponse:
    if sample:
        return get_sample_analysis("weekly_distribution")
    selected_crime_types = _merge_crime_types(crime_types=crime_types, crime_type=crime_type)
    return service.weekly_distribution(db, start_year=start_year, end_year=end_year, crime_types=selected_crime_types)


@router.get("/hourly-distribution", response_model=AnalysisResponse)
def hourly_distribution(
    start_year: int | None = Query(default=None, ge=2001, le=2100),
    end_year: int | None = Query(default=None, ge=2001, le=2100),
    crime_types: list[str] | None = Query(default=None),
    crime_type: str | None = Query(default=None, include_in_schema=False),
    sample: bool = Query(default=False, description="Return sample data"),
    db: Session = Depends(get_db),
) -> AnalysisResponse:
    if sample:
        return get_sample_analysis("hourly_distribution")
    selected_crime_types = _merge_crime_types(crime_types=crime_types, crime_type=crime_type)
    return service.hourly_distribution(db, start_year=start_year, end_year=end_year, crime_types=selected_crime_types)


@router.get("/crime-type-share", response_model=AnalysisResponse)
def crime_type_share(
    year_num: int | None = Query(default=None, ge=2001, le=2100),
    top_n: int = Query(default=10, ge=3, le=30),
    sample: bool = Query(default=False, description="Return sample data"),
    db: Session = Depends(get_db),
) -> AnalysisResponse:
    if sample:
        return get_sample_analysis("crime_type_share")
    return service.crime_type_share(db, year_num=year_num, top_n=top_n)


@router.get("/district-comparison", response_model=AnalysisResponse)
def district_comparison(
    start_year: int | None = Query(default=None, ge=2001, le=2100),
    end_year: int | None = Query(default=None, ge=2001, le=2100),
    top_n: int = Query(default=15, ge=5, le=50),
    sample: bool = Query(default=False, description="Return sample data"),
    db: Session = Depends(get_db),
) -> AnalysisResponse:
    if sample:
        return get_sample_analysis("district_comparison")
    return service.district_comparison(db, start_year=start_year, end_year=end_year, top_n=top_n)




@router.get("/day-hour-heatmap", response_model=AnalysisResponse)
def day_hour_heatmap(
    start_year: int | None = Query(default=None, ge=2001, le=2100),
    end_year: int | None = Query(default=None, ge=2001, le=2100),
    crime_types: list[str] | None = Query(default=None),
    crime_type: str | None = Query(default=None, include_in_schema=False),
    sample: bool = Query(default=False, description="Return sample data"),
    db: Session = Depends(get_db),
) -> AnalysisResponse:
    if sample:
        return get_sample_analysis("day_hour_heatmap")
    selected_crime_types = _merge_crime_types(crime_types=crime_types, crime_type=crime_type)
    return service.day_hour_heatmap(db, start_year=start_year, end_year=end_year, crime_types=selected_crime_types)


@router.get("/yoy-top-types", response_model=AnalysisResponse)
def yoy_top_types(
    start_year: int | None = Query(default=None, ge=2001, le=2100),
    end_year: int | None = Query(default=None, ge=2001, le=2100),
    top_n: int = Query(default=5, ge=3, le=10),
    sample: bool = Query(default=False, description="Return sample data"),
    db: Session = Depends(get_db),
) -> AnalysisResponse:
    if sample:
        return get_sample_analysis("yoy_top_types")
    return service.yoy_top_types(db, start_year=start_year, end_year=end_year, top_n=top_n)


@router.get("/conclusions", response_model=ConclusionResponse)
def conclusions(
    start_year: int | None = Query(default=None, ge=2001, le=2100),
    end_year: int | None = Query(default=None, ge=2001, le=2100),
    sample: bool = Query(default=False, description="Return sample data"),
    db: Session = Depends(get_db),
) -> ConclusionResponse:
    if sample:
        return get_sample_conclusions()
    return service.conclusions(db, start_year=start_year, end_year=end_year)


