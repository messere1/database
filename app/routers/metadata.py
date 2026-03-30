from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import DataQualityResponse, DatasetMetaResponse, DatasetOverviewResponse, FieldDefinition
from app.services.sample_data import get_sample_overview, get_sample_quality

router = APIRouter(prefix="/api/v1/meta", tags=["metadata"])


def _format_datetime_string(value: object) -> str | None:
    if value is None:
        return None
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    text_value = str(value)
    return text_value[:19] if len(text_value) >= 19 else text_value

FIELD_DEFINITIONS = [
    FieldDefinition(field_name="ID", source_type="string", clean_type="BIGINT(source_id)", description="Unique case identifier"),
    FieldDefinition(field_name="Case Number", source_type="string", clean_type="VARCHAR(32)", description="Case number"),
    FieldDefinition(field_name="Date", source_type="string", clean_type="DATETIME(occurred_at)", description="Occurrence datetime"),
    FieldDefinition(field_name="Block", source_type="string", clean_type="VARCHAR(128)", description="Street block"),
    FieldDefinition(field_name="IUCR", source_type="string", clean_type="VARCHAR(16)", description="Illinois offense code"),
    FieldDefinition(field_name="Primary Type", source_type="string", clean_type="VARCHAR(64)", description="Primary crime category"),
    FieldDefinition(field_name="Description", source_type="string", clean_type="VARCHAR(255)", description="Crime detail description"),
    FieldDefinition(field_name="Location Description", source_type="string", clean_type="VARCHAR(128)", description="Location type"),
    FieldDefinition(field_name="Arrest", source_type="boolean(string)", clean_type="TINYINT(1)", description="Whether an arrest was made"),
    FieldDefinition(field_name="Domestic", source_type="boolean(string)", clean_type="TINYINT(1)", description="Whether domestic related"),
    FieldDefinition(field_name="Beat", source_type="string/integer", clean_type="INT", description="Police beat"),
    FieldDefinition(field_name="District", source_type="string/integer", clean_type="INT", description="Police district"),
    FieldDefinition(field_name="Ward", source_type="string/integer", clean_type="INT", description="Ward"),
    FieldDefinition(field_name="Community Area", source_type="string/integer", clean_type="INT", description="Community area code"),
    FieldDefinition(field_name="FBI Code", source_type="string", clean_type="VARCHAR(16)", description="FBI category code"),
    FieldDefinition(field_name="X Coordinate", source_type="string/integer", clean_type="INT", description="Projected X coordinate"),
    FieldDefinition(field_name="Y Coordinate", source_type="string/integer", clean_type="INT", description="Projected Y coordinate"),
    FieldDefinition(field_name="Year", source_type="string/integer", clean_type="SMALLINT(year_num)", description="Occurrence year"),
    FieldDefinition(field_name="Updated On", source_type="string", clean_type="DATETIME(updated_on)", description="Last update time"),
    FieldDefinition(field_name="Latitude", source_type="string/decimal", clean_type="DECIMAL(10,8)", description="Latitude"),
    FieldDefinition(field_name="Longitude", source_type="string/decimal", clean_type="DECIMAL(11,8)", description="Longitude"),
    FieldDefinition(field_name="Location", source_type="string", clean_type="POINT(location)", description="Text location and optional geospatial point"),
]


@router.get("/fields", response_model=DatasetMetaResponse)
def get_fields() -> DatasetMetaResponse:
    return DatasetMetaResponse(
        dataset_name="Chicago Crimes 2001 to Present",
        source_table="crimes_raw",
        analysis_table="crimes_clean",
        field_count=len(FIELD_DEFINITIONS),
        fields=FIELD_DEFINITIONS,
    )


@router.get("/overview", response_model=DatasetOverviewResponse)
def get_overview(
    sample: bool = Query(default=False, description="Return sample data"),
    db: Session = Depends(get_db),
) -> DatasetOverviewResponse:
    if sample:
        return DatasetOverviewResponse(**get_sample_overview())

    sql = """
    SELECT
        COUNT(*) AS total_rows,
        MIN(occurred_at) AS min_occurrence_time,
        MAX(occurred_at) AS max_occurrence_time,
        COUNT(DISTINCT primary_type) AS distinct_crime_types,
        COUNT(DISTINCT district) AS distinct_districts,
        COUNT(DISTINCT community_area) AS distinct_community_areas
    FROM crimes_clean
    """

    try:
        row = db.execute(text(sql)).mappings().first()
        if not row:
            return DatasetOverviewResponse(
                total_rows=0,
                min_occurrence_time=None,
                max_occurrence_time=None,
                distinct_crime_types=0,
                distinct_districts=0,
                distinct_community_areas=0,
            )
        row_dict = dict(row)
        row_dict["min_occurrence_time"] = _format_datetime_string(row_dict.get("min_occurrence_time"))
        row_dict["max_occurrence_time"] = _format_datetime_string(row_dict.get("max_occurrence_time"))
        return DatasetOverviewResponse(**row_dict)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to query overview: {exc}") from exc


@router.get("/quality", response_model=DataQualityResponse)
def get_quality(
    sample: bool = Query(default=False, description="Return sample data"),
    db: Session = Depends(get_db),
) -> DataQualityResponse:
    if sample:
        return DataQualityResponse(**get_sample_quality())

    sql = """
    SELECT
        COUNT(*) AS total_rows,
        SUM(CASE WHEN source_id IS NULL THEN 1 ELSE 0 END) AS missing_source_id,
        SUM(CASE WHEN occurred_at IS NULL THEN 1 ELSE 0 END) AS missing_occurred_at,
        SUM(CASE WHEN primary_type IS NULL OR primary_type = '' THEN 1 ELSE 0 END) AS missing_primary_type,
        SUM(CASE WHEN district IS NULL THEN 1 ELSE 0 END) AS missing_district,
        SUM(CASE WHEN community_area IS NULL THEN 1 ELSE 0 END) AS missing_community_area,
        SUM(CASE WHEN latitude IS NULL THEN 1 ELSE 0 END) AS missing_latitude,
        SUM(CASE WHEN longitude IS NULL THEN 1 ELSE 0 END) AS missing_longitude,
        SUM(CASE WHEN arrest IS NULL THEN 1 ELSE 0 END) AS missing_arrest,
        SUM(CASE WHEN domestic IS NULL THEN 1 ELSE 0 END) AS missing_domestic
    FROM crimes_clean
    """

    try:
        row = db.execute(text(sql)).mappings().first()
        if not row:
            return DataQualityResponse(total_rows=0, missing_counts={})

        row_dict = dict(row)
        total_rows = row_dict.pop("total_rows", 0)
        return DataQualityResponse(total_rows=total_rows, missing_counts={key: int(value or 0) for key, value in row_dict.items()})
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to query quality: {exc}") from exc
