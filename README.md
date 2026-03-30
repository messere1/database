# Crime Analytics Backend (FastAPI + openGauss)

This project provides a Python backend for the Chicago Crimes dataset task.

It covers:

- dataset structure understanding via metadata API
- relational storage workflow (raw table to clean typed table)
- at least 10 independent SQL analysis angles
- frontend-ready API contract for charts and text conclusions

## 1. Project Structure

```text
crime_analytics_backend/
  app/
    core/
      config.py
    routers/
      analysis.py
      metadata.py
      system.py
    services/
      analysis_service.py
    db.py
    main.py
    schemas.py
  docs/
    API.md
  scripts/
    build_dashboard_snapshot.py
    opengauss_import.py
    opengauss_prepare_clean.py
  sql/
    prepare_clean_table.sql
    analysis_queries.sql
  requirements.txt
  start_server.py
  .env.example
```

## 2. Prerequisites

- Python 3.10+
- Huawei Cloud openGauss
- Existing raw import table: `crimes_raw`

## 3. Setup

### 3.0 Quick Start (No Extra Config)

After cloning, you can run directly:

```bash
cd d:/database/crime_analytics_backend
python start_server.py --host 127.0.0.1 --port 8016
```

The project will auto-install dependencies and use built-in openGauss defaults.

### 3.1 Install Dependencies (Optional)

```bash
cd d:/database/crime_analytics_backend
C:/Users/73110/AppData/Local/Microsoft/WindowsApps/python3.11.exe -m pip install -r requirements.txt
```

The project now provides an auto-bootstrap launcher. If dependencies are missing or version-mismatched, it will install them automatically on startup. So manual install can be skipped.

### 3.2 Configure Environment

Optional: copy `.env.example` to `.env` if you want to override default openGauss connection settings.

### 3.3 Build Clean Analysis Table

```bash
cd d:/database/crime_analytics_backend
python scripts/opengauss_prepare_clean.py
```

### 3.4 Start Backend

```bash
cd d:/database/crime_analytics_backend
python start_server.py --host 127.0.0.1 --port 8016
```

After startup, browser auto-opens `/dashboard` by default.

If you want to disable auto-open:

```bash
python start_server.py --host 127.0.0.1 --port 8016 --no-open-browser
```

Service URLs:

- API docs: `http://127.0.0.1:8016/docs`
- Dashboard: `http://127.0.0.1:8016/dashboard`

Stop service with `Ctrl + C` in the same terminal.

### 3.5 Build Static Dashboard Snapshot (Recommended for large datasets)

When data volume is very large, default dashboard queries can be slow. You can pre-build a static snapshot so the first screen loads from local JSON instead of querying all analysis endpoints.

```bash
cd d:/database/crime_analytics_backend
python scripts/build_dashboard_snapshot.py
```

This generates:

```text
app/static/dashboard_snapshot.json
```

Dashboard behavior after this change:

- default view (no filters + topN=10): uses static snapshot for fast loading
- filtered view (year/type changed): still uses live API queries

If database is unavailable, you can generate a sample snapshot:

```bash
python scripts/build_dashboard_snapshot.py --sample
```

### 3.6 Import Data to Huawei Cloud openGauss

1. Fill `OG_PASSWORD` in `.env`.
2. Run importer script:

```bash
cd d:/database/crime_analytics_backend
python scripts/opengauss_import.py
```

Then build analysis table (`crimes_clean`) used by API:

```bash
python scripts/opengauss_prepare_clean.py
```

If the user does not have permission on `public` schema, use:

```bash
python scripts/opengauss_import.py --schema testuser
```

Quick verification with partial data:

```bash
python scripts/opengauss_import.py --schema testuser --max-rows 10000
```

The script will:

- connect to openGauss server
- create schema/table if not exists
- truncate target table by default
- bulk import CSV using `COPY`

Optional arguments:

- `--no-truncate`: keep existing rows and append
- `--table crimes_raw_new`: import to another table name
- `--max-rows 10000`: import only first N rows for connectivity check
- `--password your_password`: pass password from CLI (less secure than `.env`)

## 4. API Docs

- Swagger UI: `http://127.0.0.1:8016/docs`
- ReDoc: `http://127.0.0.1:8016/redoc`
- Frontend integration contract: `docs/API.md`

## 5. Analysis Coverage (9 Endpoints)

1. Dashboard bundle (recommended for frontend dynamic refresh)
2. Annual trend
3. Weekly distribution
4. Hourly distribution
5. Crime type share
6. District comparison
7. Day-hour heatmap
8. YoY trend of top crime types
9. Text conclusions bundle (10+ statements)

## 6. Notes

- `sql/analysis_queries.sql` contains standalone SQL examples for report writing.
- Most analysis and metadata APIs support `sample=true` for frontend demo without database dependency.
- `start_server.py` checks dependency versions against `requirements.txt` and auto-installs missing items before server startup.
- For production deployment, add authentication, tighter CORS, and caching.
