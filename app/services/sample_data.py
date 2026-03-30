from copy import deepcopy
from typing import Any

SAMPLE_OVERVIEW: dict[str, Any] = {
    "total_rows": 7784664,
    "min_occurrence_time": "2001-01-01 00:00:00",
    "max_occurrence_time": "2025-12-31 23:59:59",
    "distinct_crime_types": 36,
    "distinct_districts": 25,
    "distinct_community_areas": 77,
}

SAMPLE_QUALITY: dict[str, Any] = {
    "total_rows": 7784664,
    "missing_counts": {
        "missing_source_id": 0,
        "missing_occurred_at": 127,
        "missing_primary_type": 0,
        "missing_district": 8818,
        "missing_community_area": 8643,
        "missing_latitude": 79524,
        "missing_longitude": 79524,
        "missing_arrest": 0,
        "missing_domestic": 0,
    },
}

SAMPLE_ANALYSIS: dict[str, dict[str, Any]] = {
    "annual_trend": {
        "analysis_id": "annual_trend",
        "title": "Annual Crime Trend",
        "description": "Yearly total crime count trend. Optionally filter by crime type.",
        "chart_type": "line",
        "dimensions": ["year_num"],
        "metrics": ["crime_count"],
        "data": [
            {"year_num": 2020, "crime_count": 212020},
            {"year_num": 2021, "crime_count": 209540},
            {"year_num": 2022, "crime_count": 238490},
            {"year_num": 2023, "crime_count": 265370},
            {"year_num": 2024, "crime_count": 273860},
        ],
        "insight": "Sample: crime count has increased in recent years.",
    },
    "weekly_distribution": {
        "analysis_id": "weekly_distribution",
        "title": "Crime Distribution by Weekday",
        "description": "Compare total crime counts from Monday to Sunday.",
        "chart_type": "bar",
        "dimensions": ["weekday_name"],
        "metrics": ["crime_count"],
        "data": [
            {"weekday_num": 1, "weekday_name": "Mon", "crime_count": 1095000},
            {"weekday_num": 2, "weekday_name": "Tue", "crime_count": 1082000},
            {"weekday_num": 3, "weekday_name": "Wed", "crime_count": 1097000},
            {"weekday_num": 4, "weekday_name": "Thu", "crime_count": 1113000},
            {"weekday_num": 5, "weekday_name": "Fri", "crime_count": 1159000},
            {"weekday_num": 6, "weekday_name": "Sat", "crime_count": 1181000},
            {"weekday_num": 7, "weekday_name": "Sun", "crime_count": 1066664},
        ],
        "insight": "Sample: Friday and Saturday are relatively higher-risk days.",
    },
    "hourly_distribution": {
        "analysis_id": "hourly_distribution",
        "title": "Crime Distribution by Hour",
        "description": "Crime distribution across the 24 hours of a day.",
        "chart_type": "bar",
        "dimensions": ["hour_num"],
        "metrics": ["crime_count"],
        "data": [
            {"hour_num": 0, "crime_count": 345210},
            {"hour_num": 1, "crime_count": 298540},
            {"hour_num": 8, "crime_count": 271920},
            {"hour_num": 12, "crime_count": 401870},
            {"hour_num": 17, "crime_count": 488340},
            {"hour_num": 20, "crime_count": 512740},
            {"hour_num": 23, "crime_count": 372500},
        ],
        "insight": "Sample: evening hours show a clear concentration.",
    },
    "crime_type_share": {
        "analysis_id": "crime_type_share",
        "title": "Crime Type Share",
        "description": "Top crime types and their percentage share.",
        "chart_type": "pie",
        "dimensions": ["primary_type"],
        "metrics": ["crime_count", "percentage"],
        "data": [
            {"primary_type": "THEFT", "crime_count": 1654300, "percentage": 21.25},
            {"primary_type": "BATTERY", "crime_count": 1431200, "percentage": 18.38},
            {"primary_type": "CRIMINAL DAMAGE", "crime_count": 887500, "percentage": 11.4},
            {"primary_type": "NARCOTICS", "crime_count": 801240, "percentage": 10.29},
            {"primary_type": "ASSAULT", "crime_count": 652100, "percentage": 8.38},
        ],
        "insight": "Sample: theft and battery account for a large share.",
    },
    "district_comparison": {
        "analysis_id": "district_comparison",
        "title": "District Crime Comparison",
        "description": "Compare crime counts across police districts.",
        "chart_type": "bar",
        "dimensions": ["district"],
        "metrics": ["crime_count"],
        "data": [
            {"district": 8, "crime_count": 422100},
            {"district": 11, "crime_count": 410550},
            {"district": 6, "crime_count": 399430},
            {"district": 25, "crime_count": 394800},
            {"district": 7, "crime_count": 389670},
        ],
        "insight": "Sample: District 8 ranks highest in this sample output.",
    },
    "day_hour_heatmap": {
        "analysis_id": "day_hour_heatmap",
        "title": "Weekday-Hour Heatmap",
        "description": "Joint distribution of weekday and hour.",
        "chart_type": "heatmap",
        "dimensions": ["weekday_num", "hour_num"],
        "metrics": ["crime_count"],
        "data": [
            {"weekday_num": 5, "hour_num": 20, "crime_count": 31540},
            {"weekday_num": 6, "hour_num": 21, "crime_count": 32920},
            {"weekday_num": 6, "hour_num": 22, "crime_count": 33410},
            {"weekday_num": 7, "hour_num": 1, "crime_count": 28020},
            {"weekday_num": 1, "hour_num": 18, "crime_count": 29480},
        ],
        "insight": "Sample: weekend evenings are visibly denser.",
    },
    "yoy_top_types": {
        "analysis_id": "yoy_top_types",
        "title": "Year-over-Year Trend of Top Crime Types",
        "description": "Compare annual trends for the most common crime categories.",
        "chart_type": "line",
        "dimensions": ["year_num", "primary_type"],
        "metrics": ["crime_count"],
        "data": [
            {"year_num": 2022, "primary_type": "THEFT", "crime_count": 52120},
            {"year_num": 2023, "primary_type": "THEFT", "crime_count": 54880},
            {"year_num": 2022, "primary_type": "BATTERY", "crime_count": 46200},
            {"year_num": 2023, "primary_type": "BATTERY", "crime_count": 47150},
            {"year_num": 2023, "primary_type": "CRIMINAL DAMAGE", "crime_count": 31890},
        ],
        "insight": "Sample: top categories remain relatively stable year-over-year.",
    },
}

SAMPLE_CONCLUSIONS: dict[str, Any] = {
    "total": 10,
    "conclusions": [
        {
            "rank": 1,
            "title": "Dataset scale",
            "conclusion": "Sample: total records are 7,784,664 from 2001 to 2025.",
            "evidence": {"total_rows": 7784664, "min_year": 2001, "max_year": 2025},
        },
        {
            "rank": 2,
            "title": "Peak annual crime",
            "conclusion": "Sample: annual volume peaks in 2024 in this sample output.",
            "evidence": {"year_num": 2024, "crime_count": 273860},
        },
        {
            "rank": 3,
            "title": "Peak weekday",
            "conclusion": "Sample: Saturday has the highest weekly crime count.",
            "evidence": {"weekday_name": "Sat", "crime_count": 1181000},
        },
        {
            "rank": 4,
            "title": "Peak hour",
            "conclusion": "Sample: 20:00 is the highest-risk hour.",
            "evidence": {"hour_num": 20, "crime_count": 512740},
        },
        {
            "rank": 5,
            "title": "Top crime type",
            "conclusion": "Sample: THEFT has the largest share among all categories.",
            "evidence": {"primary_type": "THEFT", "percentage": 21.25},
        },
        {
            "rank": 6,
            "title": "Top district",
            "conclusion": "Sample: District 8 has the highest total volume.",
            "evidence": {"district": 8, "crime_count": 422100},
        },
        {
            "rank": 7,
            "title": "Top community area",
            "conclusion": "Sample: Community area 25 ranks first in this sample.",
            "evidence": {"community_area": 25, "crime_count": 221430},
        },
        {
            "rank": 8,
            "title": "Arrest rate change",
            "conclusion": "Sample: arrest rate trends downward from 2020 to 2023.",
            "evidence": {"start_rate": 21.7, "end_rate": 18.98},
        },
        {
            "rank": 9,
            "title": "Domestic burden",
            "conclusion": "Sample: domestic incident share stays around low 20%.",
            "evidence": {"domestic_rate_range": "21.37%-22.74%"},
        },
        {
            "rank": 10,
            "title": "Hotspot block",
            "conclusion": "Sample: 001XX N STATE ST appears as a top hotspot block.",
            "evidence": {"block_name": "001XX N STATE ST", "crime_count": 8420},
        },
    ],
}

def get_sample_analysis(analysis_id: str) -> dict[str, Any]:
    if analysis_id not in SAMPLE_ANALYSIS:
        raise KeyError(f"Unknown sample analysis id: {analysis_id}")
    return deepcopy(SAMPLE_ANALYSIS[analysis_id])


def get_sample_overview() -> dict[str, Any]:
    return deepcopy(SAMPLE_OVERVIEW)


def get_sample_quality() -> dict[str, Any]:
    return deepcopy(SAMPLE_QUALITY)


def get_sample_conclusions() -> dict[str, Any]:
    return deepcopy(SAMPLE_CONCLUSIONS)
