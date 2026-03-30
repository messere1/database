# Crime Analytics Backend API

## 1. Overview

This API serves structured crime analysis data for dashboard frontends.

- Base URL: `http://127.0.0.1:8000`
- Protocol: HTTP JSON
- Auth: none (coursework environment)
- Data source table: `chicago_crime.crimes_clean`

## 2. Standard Response Patterns

### 2.1 Analysis Response

```json
{
  "analysis_id": "annual_trend",
  "title": "Annual Crime Trend",
  "description": "Yearly total crime count trend.",
  "chart_type": "line",
  "dimensions": ["year_num"],
  "metrics": ["crime_count"],
  "data": [
    {"year_num": 2019, "crime_count": 261998},
    {"year_num": 2020, "crime_count": 211772}
  ],
  "insight": "Peak year is ..."
}
```

### 2.2 Conclusions Response

```json
{
  "total": 12,
  "conclusions": [
    {
      "rank": 1,
      "title": "Dataset scale",
      "conclusion": "Within selected range ...",
      "evidence": {
        "min_year": 2001,
        "max_year": 2024,
        "total_rows": 7784664
      }
    }
  ]
}
```

### 2.3 Error Response

```json
{
  "detail": "Error message"
}
```

## 3. System and Metadata APIs

### 3.1 Health Check

- Method: `GET`
- Path: `/api/v1/system/health`
- Purpose: check API and DB connectivity

### 3.2 Field Dictionary

- Method: `GET`
- Path: `/api/v1/meta/fields`
- Purpose: return source fields, clean types, and semantic descriptions

### 3.3 Data Overview

- Method: `GET`
- Path: `/api/v1/meta/overview`
- Purpose: total rows, time range, distinct counts

### 3.4 Data Quality Summary

- Method: `GET`
- Path: `/api/v1/meta/quality`
- Purpose: null or missing counts for key analysis columns

## 4. Analysis APIs (9 Endpoints)

Common filters:

- `start_year` optional integer, range lower bound
- `end_year` optional integer, range upper bound
- `crime_types` optional repeated string params for one or more crime categories (for example `crime_types=THEFT&crime_types=BATTERY`)
- `top_n` optional integer limit for ranking endpoints
- `sample` optional boolean, when true returns built-in sample data without querying database

### 4.1 Endpoint List

1. `GET /api/v1/analysis/dashboard-bundle`
Description: one-shot payload for dashboard dynamic refresh, including overview, quality, chart datasets, and lightweight conclusions.
Params: `start_year`, `end_year`, `crime_types`, `top_n`, `sample`.
Recommended usage: primary endpoint for frontend refresh to reduce request fan-out.

2. `GET /api/v1/analysis/annual-trend`
Description: annual trend.
Params: `start_year`, `end_year`, `crime_types`.
Recommended chart: line.

3. `GET /api/v1/analysis/weekly-distribution`
Description: weekday distribution.
Params: `start_year`, `end_year`, `crime_types`.
Recommended chart: bar.

4. `GET /api/v1/analysis/hourly-distribution`
Description: 24-hour distribution.
Params: `start_year`, `end_year`, `crime_types`.
Recommended chart: bar.

5. `GET /api/v1/analysis/crime-type-share`
Description: crime type share.
Params: `year_num`, `top_n`.
Recommended chart: pie.

6. `GET /api/v1/analysis/district-comparison`
Description: district comparison.
Params: `start_year`, `end_year`, `top_n`.
Recommended chart: bar.

7. `GET /api/v1/analysis/day-hour-heatmap`
Description: weekday-hour joint density.
Params: `start_year`, `end_year`, `crime_types`.
Recommended chart: heatmap.

8. `GET /api/v1/analysis/yoy-top-types`
Description: year-over-year trend for top types.
Params: `start_year`, `end_year`, `top_n`.
Recommended chart: multi-line.

9. `GET /api/v1/analysis/conclusions`
Description: textual conclusions bundle.
Params: `start_year`, `end_year`, `sample`.
Recommended display: cards or list.

## 5. Frontend Integration Guide

### 5.1 Page Load Sequence

1. Call `/api/v1/system/health`.
2. Call `/api/v1/analysis/dashboard-bundle` once.
3. Render KPI, charts, and conclusions from bundle payload.

### 5.2 Filter Interaction Contract

When user changes global filters (year range, one or more crime types):

1. Re-request affected endpoints with query params.
2. Keep chart configs fixed, replace only `data`.
3. Show endpoint-specific `insight` under each chart.

### 5.3 Chart Mapping Recommendations

- `chart_type=line`: line chart with `dimensions[0]` as x-axis.
- `chart_type=bar`: category bar chart.
- `chart_type=pie`: use `primary_type` and `percentage`.
- `chart_type=heatmap`: x=`hour_num`, y=`weekday_num`, value=`crime_count`.

## 6. Example Calls

### 6.1 Annual Trend (All Crimes)

```bash
curl "http://127.0.0.1:8000/api/v1/analysis/annual-trend?start_year=2015&end_year=2024"
```

### 6.2 Annual Trend (Specific Types)

```bash
curl "http://127.0.0.1:8000/api/v1/analysis/annual-trend?crime_types=THEFT&crime_types=BATTERY"
```

### 6.3 Crime Type Share

```bash
curl "http://127.0.0.1:8000/api/v1/analysis/crime-type-share?top_n=8"
```

### 6.4 Text Conclusions Bundle

```bash
curl "http://127.0.0.1:8000/api/v1/analysis/conclusions?start_year=2018&end_year=2024"
```

### 6.5 Annual Trend Sample Data (No DB)

```bash
curl "http://127.0.0.1:8000/api/v1/analysis/annual-trend?sample=true"
```

### 6.6 Metadata Overview Sample Data (No DB)

```bash
curl "http://127.0.0.1:8000/api/v1/meta/overview?sample=true"
```

## 7. Backend-Frontend Data Contract Notes

- Numeric fields are returned as JSON numbers when possible.
- Empty query result returns `data: []` and a fallback `insight`.
- CORS is open by default (`APP_CORS_ORIGINS=*`), configurable via `.env`.
- For production, add authentication and stricter CORS.
