from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


class CrimeAnalysisService:
    def _fetch_all(self, db: Session, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        result = db.execute(text(sql), params or {})
        return [dict(row._mapping) for row in result]

    def _fetch_one(self, db: Session, sql: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        row = db.execute(text(sql), params or {}).mappings().first()
        return dict(row) if row else None

    def _build_analysis(
        self,
        analysis_id: str,
        title: str,
        description: str,
        chart_type: str,
        dimensions: list[str],
        metrics: list[str],
        data: list[dict[str, Any]],
        insight: str,
    ) -> dict[str, Any]:
        return {
            "analysis_id": analysis_id,
            "title": title,
            "description": description,
            "chart_type": chart_type,
            "dimensions": dimensions,
            "metrics": metrics,
            "data": data,
            "insight": insight,
        }

    @staticmethod
    def _safe_pct(numerator: float, denominator: float) -> float:
        if denominator == 0:
            return 0.0
        return round((numerator / denominator) * 100.0, 2)

    @staticmethod
    def _normalize_crime_types(
        crime_types: list[str] | None = None,
        crime_type: str | None = None,
    ) -> list[str]:
        raw_values: list[str] = []

        if isinstance(crime_types, list):
            raw_values.extend([str(item) for item in crime_types])
        if crime_type is not None:
            raw_values.append(str(crime_type))

        normalized: list[str] = []
        seen: set[str] = set()
        for value in raw_values:
            item = value.strip()
            if not item or item in seen:
                continue
            seen.add(item)
            normalized.append(item)

        return normalized

    @staticmethod
    def _build_crime_type_clause(crime_types: list[str], prefix: str = "crime_type") -> tuple[str, dict[str, Any]]:
        if not crime_types:
            return "1=1", {}

        placeholders: list[str] = []
        params: dict[str, Any] = {}
        for idx, value in enumerate(crime_types):
            key = f"{prefix}_{idx}"
            placeholders.append(f":{key}")
            params[key] = value

        return f"primary_type IN ({', '.join(placeholders)})", params

    @staticmethod
    def _format_datetime_string(value: Any) -> str | None:
        if value is None:
            return None
        if hasattr(value, "strftime"):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        text_value = str(value)
        return text_value[:19] if len(text_value) >= 19 else text_value

    def _dataset_overview(self, db: Session) -> dict[str, Any]:
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
        row = self._fetch_one(db, sql) or {}
        return {
            "total_rows": int(row.get("total_rows") or 0),
            "min_occurrence_time": self._format_datetime_string(row.get("min_occurrence_time")),
            "max_occurrence_time": self._format_datetime_string(row.get("max_occurrence_time")),
            "distinct_crime_types": int(row.get("distinct_crime_types") or 0),
            "distinct_districts": int(row.get("distinct_districts") or 0),
            "distinct_community_areas": int(row.get("distinct_community_areas") or 0),
        }

    def _dataset_quality(self, db: Session) -> dict[str, Any]:
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
        row = self._fetch_one(db, sql) or {}
        missing_keys = [
            "missing_source_id",
            "missing_occurred_at",
            "missing_primary_type",
            "missing_district",
            "missing_community_area",
            "missing_latitude",
            "missing_longitude",
            "missing_arrest",
            "missing_domestic",
        ]
        return {
            "total_rows": int(row.get("total_rows") or 0),
            "missing_counts": {key: int(row.get(key) or 0) for key in missing_keys},
        }

    def _quick_conclusions(
        self,
        db: Session,
        start_year: int | None,
        end_year: int | None,
        annual: list[dict[str, Any]],
        weekly: list[dict[str, Any]],
        hourly: list[dict[str, Any]],
        type_share: list[dict[str, Any]],
        district: list[dict[str, Any]],
    ) -> dict[str, Any]:
        period = self._fetch_one(
            db,
            """
            SELECT
                MIN(year_num) AS min_year,
                MAX(year_num) AS max_year,
                COUNT(*) AS total_rows
            FROM crimes_clean
            WHERE (:start_year IS NULL OR year_num >= :start_year)
              AND (:end_year IS NULL OR year_num <= :end_year)
            """,
            {"start_year": start_year, "end_year": end_year},
        ) or {"min_year": None, "max_year": None, "total_rows": 0}

        conclusions: list[dict[str, Any]] = []

        conclusions.append(
            {
                "rank": 1,
                "title": "Dataset scale",
                "conclusion": (
                    f"Within selected range, total records are {period['total_rows']} "
                    f"from {period['min_year']} to {period['max_year']}."
                ),
                "evidence": period,
            }
        )

        if annual:
            peak_year = max(annual, key=lambda item: item["crime_count"])
            low_year = min(annual, key=lambda item: item["crime_count"])
            conclusions.append(
                {
                    "rank": 2,
                    "title": "Peak annual crime",
                    "conclusion": f"Peak annual volume is in {peak_year['year_num']} with {peak_year['crime_count']} cases.",
                    "evidence": peak_year,
                }
            )
            conclusions.append(
                {
                    "rank": 3,
                    "title": "Lowest annual crime",
                    "conclusion": f"Lowest annual volume is in {low_year['year_num']} with {low_year['crime_count']} cases.",
                    "evidence": low_year,
                }
            )
        else:
            conclusions.append(
                {
                    "rank": 2,
                    "title": "Peak annual crime",
                    "conclusion": "No annual data available.",
                    "evidence": {},
                }
            )
            conclusions.append(
                {
                    "rank": 3,
                    "title": "Lowest annual crime",
                    "conclusion": "No annual data available.",
                    "evidence": {},
                }
            )

        if weekly:
            peak_weekday = max(weekly, key=lambda item: item["crime_count"])
            conclusions.append(
                {
                    "rank": 4,
                    "title": "Peak weekday",
                    "conclusion": (
                        f"Weekday {peak_weekday['weekday_name']} is the highest-crime day "
                        f"with {peak_weekday['crime_count']} cases."
                    ),
                    "evidence": peak_weekday,
                }
            )
        else:
            conclusions.append(
                {
                    "rank": 4,
                    "title": "Peak weekday",
                    "conclusion": "No weekday distribution data available.",
                    "evidence": {},
                }
            )

        if hourly:
            peak_hour = max(hourly, key=lambda item: item["crime_count"])
            conclusions.append(
                {
                    "rank": 5,
                    "title": "Peak hour",
                    "conclusion": (
                        f"Hour {peak_hour['hour_num']} is the peak crime hour "
                        f"with {peak_hour['crime_count']} cases."
                    ),
                    "evidence": peak_hour,
                }
            )
        else:
            conclusions.append(
                {
                    "rank": 5,
                    "title": "Peak hour",
                    "conclusion": "No hourly distribution data available.",
                    "evidence": {},
                }
            )

        if type_share:
            top_type = type_share[0]
            conclusions.append(
                {
                    "rank": 6,
                    "title": "Top crime type",
                    "conclusion": (
                        f"Top crime type is {top_type['primary_type']} with {top_type['crime_count']} cases "
                        f"({top_type['percentage']}%)."
                    ),
                    "evidence": top_type,
                }
            )
        else:
            conclusions.append(
                {
                    "rank": 6,
                    "title": "Top crime type",
                    "conclusion": "No crime-type share data available.",
                    "evidence": {},
                }
            )

        if district:
            conclusions.append(
                {
                    "rank": 7,
                    "title": "Top district",
                    "conclusion": (
                        f"District {district[0]['district']} ranks first with "
                        f"{district[0]['crime_count']} cases."
                    ),
                    "evidence": district[0],
                }
            )
        else:
            conclusions.append(
                {
                    "rank": 7,
                    "title": "Top district",
                    "conclusion": "No district comparison data available.",
                    "evidence": {},
                }
            )

        return {
            "total": len(conclusions),
            "conclusions": conclusions,
        }

    def dashboard_bundle(
        self,
        db: Session,
        start_year: int | None = None,
        end_year: int | None = None,
        crime_types: list[str] | None = None,
        crime_type: str | None = None,
        top_n: int = 10,
        type_options_top_n: int = 30,
    ) -> dict[str, Any]:
        normalized_crime_types = self._normalize_crime_types(crime_types=crime_types, crime_type=crime_type)

        annual = self.annual_trend(db, start_year=start_year, end_year=end_year, crime_types=normalized_crime_types)
        weekly = self.weekly_distribution(db, start_year=start_year, end_year=end_year, crime_types=normalized_crime_types)
        hourly = self.hourly_distribution(db, start_year=start_year, end_year=end_year, crime_types=normalized_crime_types)
        type_share = self.crime_type_share(db, year_num=end_year, top_n=top_n)
        district = self.district_comparison(db, start_year=start_year, end_year=end_year, top_n=top_n)
        heatmap = self.day_hour_heatmap(db, start_year=start_year, end_year=end_year, crime_types=normalized_crime_types)
        yoy = self.yoy_top_types(db, start_year=start_year, end_year=end_year, top_n=min(top_n, 8))
        type_options = self.crime_type_share(db, year_num=None, top_n=type_options_top_n)

        conclusions = self._quick_conclusions(
            db,
            start_year=start_year,
            end_year=end_year,
            annual=annual.get("data", []),
            weekly=weekly.get("data", []),
            hourly=hourly.get("data", []),
            type_share=type_share.get("data", []),
            district=district.get("data", []),
        )

        return {
            "overview": self._dataset_overview(db),
            "quality": self._dataset_quality(db),
            "annual": annual,
            "weekly": weekly,
            "hourly": hourly,
            "typeShare": type_share,
            "district": district,
            "heatmap": heatmap,
            "yoy": yoy,
            "typeOptions": type_options,
            "conclusions": conclusions,
        }

    def annual_trend(
        self,
        db: Session,
        start_year: int | None = None,
        end_year: int | None = None,
        crime_types: list[str] | None = None,
        crime_type: str | None = None,
    ) -> dict[str, Any]:
        normalized_crime_types = self._normalize_crime_types(crime_types=crime_types, crime_type=crime_type)
        crime_clause, crime_params = self._build_crime_type_clause(normalized_crime_types, prefix="annual_crime_type")

        sql = f"""
        SELECT
            year_num,
            COUNT(*) AS crime_count
        FROM crimes_clean
        WHERE year_num IS NOT NULL
          AND (:start_year IS NULL OR year_num >= :start_year)
          AND (:end_year IS NULL OR year_num <= :end_year)
          AND ({crime_clause})
        GROUP BY year_num
        ORDER BY year_num
        """
        params = {
            "start_year": start_year,
            "end_year": end_year,
            **crime_params,
        }
        rows = self._fetch_all(db, sql, params)
        if not rows:
            insight = "No data available under current filters."
        else:
            peak = max(rows, key=lambda item: item["crime_count"])
            first_count = rows[0]["crime_count"]
            last_count = rows[-1]["crime_count"]
            change_pct = self._safe_pct(last_count - first_count, first_count) if first_count else 0.0
            insight = (
                f"Peak year is {peak['year_num']} with {peak['crime_count']} cases. "
                f"From {rows[0]['year_num']} to {rows[-1]['year_num']}, change is {change_pct}%.")

        title = "Annual Crime Trend"
        if len(normalized_crime_types) == 1:
            title = f"Annual Crime Trend ({normalized_crime_types[0]})"
        elif len(normalized_crime_types) > 1:
            title = f"Annual Crime Trend ({len(normalized_crime_types)} types)"

        return self._build_analysis(
            analysis_id="annual_trend",
            title=title,
            description="Yearly total crime count trend. Optionally filter by crime type.",
            chart_type="line",
            dimensions=["year_num"],
            metrics=["crime_count"],
            data=rows,
            insight=insight,
        )

    def weekly_distribution(
        self,
        db: Session,
        start_year: int | None = None,
        end_year: int | None = None,
        crime_types: list[str] | None = None,
        crime_type: str | None = None,
    ) -> dict[str, Any]:
        normalized_crime_types = self._normalize_crime_types(crime_types=crime_types, crime_type=crime_type)
        crime_clause, crime_params = self._build_crime_type_clause(normalized_crime_types, prefix="weekly_crime_type")

        sql = f"""
        SELECT
            weekday_num,
            CASE weekday_num
                WHEN 1 THEN 'Mon'
                WHEN 2 THEN 'Tue'
                WHEN 3 THEN 'Wed'
                WHEN 4 THEN 'Thu'
                WHEN 5 THEN 'Fri'
                WHEN 6 THEN 'Sat'
                WHEN 7 THEN 'Sun'
                ELSE 'Unknown'
            END AS weekday_name,
            COUNT(*) AS crime_count
        FROM crimes_clean
        WHERE weekday_num IS NOT NULL
          AND (:start_year IS NULL OR year_num >= :start_year)
          AND (:end_year IS NULL OR year_num <= :end_year)
                    AND ({crime_clause})
        GROUP BY weekday_num
        ORDER BY weekday_num
                """
        params = {
            "start_year": start_year,
            "end_year": end_year,
                        **crime_params,
        }
        rows = self._fetch_all(db, sql, params)

        if rows:
            peak = max(rows, key=lambda item: item["crime_count"])
            insight = f"{peak['weekday_name']} is the highest-crime day with {peak['crime_count']} cases."
        else:
            insight = "No data available under current filters."

        return self._build_analysis(
            analysis_id="weekly_distribution",
            title="Crime Distribution by Weekday",
            description="Compare total crime counts from Monday to Sunday.",
            chart_type="bar",
            dimensions=["weekday_name"],
            metrics=["crime_count"],
            data=rows,
            insight=insight,
        )

    def hourly_distribution(
        self,
        db: Session,
        start_year: int | None = None,
        end_year: int | None = None,
        crime_types: list[str] | None = None,
        crime_type: str | None = None,
    ) -> dict[str, Any]:
        normalized_crime_types = self._normalize_crime_types(crime_types=crime_types, crime_type=crime_type)
        crime_clause, crime_params = self._build_crime_type_clause(normalized_crime_types, prefix="hourly_crime_type")

        sql = f"""
        SELECT
            hour_num,
            COUNT(*) AS crime_count
        FROM crimes_clean
        WHERE hour_num IS NOT NULL
          AND (:start_year IS NULL OR year_num >= :start_year)
          AND (:end_year IS NULL OR year_num <= :end_year)
          AND ({crime_clause})
        GROUP BY hour_num
        ORDER BY hour_num
        """
        params = {
            "start_year": start_year,
            "end_year": end_year,
            **crime_params,
        }
        rows = self._fetch_all(db, sql, params)

        if rows:
            peak = max(rows, key=lambda item: item["crime_count"])
            insight = f"Hour {peak['hour_num']} is the highest-crime hour with {peak['crime_count']} cases."
        else:
            insight = "No data available under current filters."

        return self._build_analysis(
            analysis_id="hourly_distribution",
            title="Crime Distribution by Hour",
            description="Crime distribution across the 24 hours of a day.",
            chart_type="bar",
            dimensions=["hour_num"],
            metrics=["crime_count"],
            data=rows,
            insight=insight,
        )

    def crime_type_share(
        self,
        db: Session,
        year_num: int | None = None,
        top_n: int = 10,
    ) -> dict[str, Any]:
        sql_top = """
        SELECT
            primary_type,
            COUNT(*) AS crime_count
        FROM crimes_clean
        WHERE primary_type IS NOT NULL
          AND (:year_num IS NULL OR year_num = :year_num)
        GROUP BY primary_type
        ORDER BY crime_count DESC
        LIMIT :top_n
        """

        sql_total = """
        SELECT COUNT(*) AS total_count
        FROM crimes_clean
        WHERE primary_type IS NOT NULL
          AND (:year_num IS NULL OR year_num = :year_num)
        """

        params = {"year_num": year_num, "top_n": top_n}
        rows = self._fetch_all(db, sql_top, params)
        total_row = self._fetch_one(db, sql_total, {"year_num": year_num}) or {"total_count": 0}
        total_count = total_row["total_count"] or 0

        for row in rows:
            row["percentage"] = self._safe_pct(row["crime_count"], total_count)

        if rows:
            top_item = rows[0]
            insight = (
                f"Top crime type is {top_item['primary_type']} with {top_item['crime_count']} cases "
                f"({top_item['percentage']}% of all selected cases)."
            )
        else:
            insight = "No data available under current filters."

        return self._build_analysis(
            analysis_id="crime_type_share",
            title="Crime Type Share",
            description="Top crime types and their percentage share.",
            chart_type="pie",
            dimensions=["primary_type"],
            metrics=["crime_count", "percentage"],
            data=rows,
            insight=insight,
        )

    def district_comparison(
        self,
        db: Session,
        start_year: int | None = None,
        end_year: int | None = None,
        top_n: int = 15,
    ) -> dict[str, Any]:
        sql = """
        SELECT
            district,
            COUNT(*) AS crime_count
        FROM crimes_clean
        WHERE district IS NOT NULL
          AND (:start_year IS NULL OR year_num >= :start_year)
          AND (:end_year IS NULL OR year_num <= :end_year)
        GROUP BY district
        ORDER BY crime_count DESC
        LIMIT :top_n
        """

        rows = self._fetch_all(
            db,
            sql,
            {"start_year": start_year, "end_year": end_year, "top_n": top_n},
        )

        if rows:
            top_item = rows[0]
            insight = f"District {top_item['district']} has the highest count: {top_item['crime_count']} cases."
        else:
            insight = "No data available under current filters."

        return self._build_analysis(
            analysis_id="district_comparison",
            title="District Crime Comparison",
            description="Compare crime counts across police districts.",
            chart_type="bar",
            dimensions=["district"],
            metrics=["crime_count"],
            data=rows,
            insight=insight,
        )

    def community_area_comparison(
        self,
        db: Session,
        start_year: int | None = None,
        end_year: int | None = None,
        top_n: int = 20,
    ) -> dict[str, Any]:
        sql = """
        SELECT
            community_area,
            COUNT(*) AS crime_count
        FROM crimes_clean
        WHERE community_area IS NOT NULL
          AND (:start_year IS NULL OR year_num >= :start_year)
          AND (:end_year IS NULL OR year_num <= :end_year)
        GROUP BY community_area
        ORDER BY crime_count DESC
        LIMIT :top_n
        """

        rows = self._fetch_all(
            db,
            sql,
            {"start_year": start_year, "end_year": end_year, "top_n": top_n},
        )

        if rows:
            top_item = rows[0]
            insight = (
                f"Community area {top_item['community_area']} has the highest count: "
                f"{top_item['crime_count']} cases."
            )
        else:
            insight = "No data available under current filters."

        return self._build_analysis(
            analysis_id="community_area_comparison",
            title="Community Area Crime Comparison",
            description="Compare crime counts across community areas.",
            chart_type="bar",
            dimensions=["community_area"],
            metrics=["crime_count"],
            data=rows,
            insight=insight,
        )

    def monthly_seasonality(
        self,
        db: Session,
        start_year: int | None = None,
        end_year: int | None = None,
        crime_types: list[str] | None = None,
        crime_type: str | None = None,
    ) -> dict[str, Any]:
        normalized_crime_types = self._normalize_crime_types(crime_types=crime_types, crime_type=crime_type)
        crime_clause, crime_params = self._build_crime_type_clause(normalized_crime_types, prefix="monthly_crime_type")

        sql = f"""
        SELECT
            month_num,
            COUNT(*) AS crime_count
        FROM crimes_clean
        WHERE month_num IS NOT NULL
          AND (:start_year IS NULL OR year_num >= :start_year)
          AND (:end_year IS NULL OR year_num <= :end_year)
          AND ({crime_clause})
        GROUP BY month_num
        ORDER BY month_num
        """

        rows = self._fetch_all(
            db,
            sql,
            {"start_year": start_year, "end_year": end_year, **crime_params},
        )

        if rows:
            peak = max(rows, key=lambda item: item["crime_count"])
            insight = f"Month {peak['month_num']} is the peak month with {peak['crime_count']} cases."
        else:
            insight = "No data available under current filters."

        return self._build_analysis(
            analysis_id="monthly_seasonality",
            title="Monthly Crime Seasonality",
            description="Seasonal distribution by month.",
            chart_type="line",
            dimensions=["month_num"],
            metrics=["crime_count"],
            data=rows,
            insight=insight,
        )

    def arrest_rate_by_year(
        self,
        db: Session,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> dict[str, Any]:
        sql = """
        SELECT
            year_num,
            SUM(CASE WHEN arrest = 1 THEN 1 ELSE 0 END) AS arrested_count,
            COUNT(*) AS total_count,
            ROUND(100 * SUM(CASE WHEN arrest = 1 THEN 1 ELSE 0 END) / COUNT(*), 2) AS arrest_rate
        FROM crimes_clean
        WHERE year_num IS NOT NULL
          AND (:start_year IS NULL OR year_num >= :start_year)
          AND (:end_year IS NULL OR year_num <= :end_year)
        GROUP BY year_num
        ORDER BY year_num
        """

        rows = self._fetch_all(db, sql, {"start_year": start_year, "end_year": end_year})

        if len(rows) >= 2:
            start_rate = rows[0]["arrest_rate"]
            end_rate = rows[-1]["arrest_rate"]
            delta = round(end_rate - start_rate, 2)
            insight = (
                f"Arrest rate changed from {start_rate}% in {rows[0]['year_num']} "
                f"to {end_rate}% in {rows[-1]['year_num']} (delta {delta} pp)."
            )
        elif rows:
            insight = f"Arrest rate in {rows[0]['year_num']} is {rows[0]['arrest_rate']}%."
        else:
            insight = "No data available under current filters."

        return self._build_analysis(
            analysis_id="arrest_rate_by_year",
            title="Arrest Rate by Year",
            description="Yearly arrest rate trend.",
            chart_type="line",
            dimensions=["year_num"],
            metrics=["arrest_rate", "arrested_count", "total_count"],
            data=rows,
            insight=insight,
        )

    def domestic_rate_by_year(
        self,
        db: Session,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> dict[str, Any]:
        sql = """
        SELECT
            year_num,
            SUM(CASE WHEN domestic = 1 THEN 1 ELSE 0 END) AS domestic_count,
            COUNT(*) AS total_count,
            ROUND(100 * SUM(CASE WHEN domestic = 1 THEN 1 ELSE 0 END) / COUNT(*), 2) AS domestic_rate
        FROM crimes_clean
        WHERE year_num IS NOT NULL
          AND (:start_year IS NULL OR year_num >= :start_year)
          AND (:end_year IS NULL OR year_num <= :end_year)
        GROUP BY year_num
        ORDER BY year_num
        """

        rows = self._fetch_all(db, sql, {"start_year": start_year, "end_year": end_year})

        if rows:
            peak = max(rows, key=lambda item: item["domestic_rate"])
            insight = (
                f"Highest domestic incident rate is {peak['domestic_rate']}% "
                f"in year {peak['year_num']}."
            )
        else:
            insight = "No data available under current filters."

        return self._build_analysis(
            analysis_id="domestic_rate_by_year",
            title="Domestic Incident Rate by Year",
            description="Yearly domestic incident proportion trend.",
            chart_type="line",
            dimensions=["year_num"],
            metrics=["domestic_rate", "domestic_count", "total_count"],
            data=rows,
            insight=insight,
        )

    def day_hour_heatmap(
        self,
        db: Session,
        start_year: int | None = None,
        end_year: int | None = None,
        crime_types: list[str] | None = None,
        crime_type: str | None = None,
    ) -> dict[str, Any]:
        normalized_crime_types = self._normalize_crime_types(crime_types=crime_types, crime_type=crime_type)
        crime_clause, crime_params = self._build_crime_type_clause(normalized_crime_types, prefix="heatmap_crime_type")

        sql = f"""
        SELECT
            weekday_num,
            hour_num,
            COUNT(*) AS crime_count
        FROM crimes_clean
        WHERE weekday_num IS NOT NULL
          AND hour_num IS NOT NULL
          AND (:start_year IS NULL OR year_num >= :start_year)
          AND (:end_year IS NULL OR year_num <= :end_year)
                    AND ({crime_clause})
        GROUP BY weekday_num, hour_num
        ORDER BY weekday_num, hour_num
                """

        rows = self._fetch_all(
            db,
            sql,
                        {"start_year": start_year, "end_year": end_year, **crime_params},
        )

        if rows:
            peak = max(rows, key=lambda item: item["crime_count"])
            insight = (
                f"Peak slot is weekday {peak['weekday_num']}, hour {peak['hour_num']} "
                f"with {peak['crime_count']} cases."
            )
        else:
            insight = "No data available under current filters."

        return self._build_analysis(
            analysis_id="day_hour_heatmap",
            title="Weekday-Hour Heatmap",
            description="Joint distribution of weekday and hour.",
            chart_type="heatmap",
            dimensions=["weekday_num", "hour_num"],
            metrics=["crime_count"],
            data=rows,
            insight=insight,
        )

    def top_blocks(
        self,
        db: Session,
        start_year: int | None = None,
        end_year: int | None = None,
        top_n: int = 20,
    ) -> dict[str, Any]:
        sql = """
        SELECT
            block_name,
            COUNT(*) AS crime_count
        FROM crimes_clean
        WHERE block_name IS NOT NULL
          AND block_name <> ''
          AND (:start_year IS NULL OR year_num >= :start_year)
          AND (:end_year IS NULL OR year_num <= :end_year)
        GROUP BY block_name
        ORDER BY crime_count DESC
        LIMIT :top_n
        """

        rows = self._fetch_all(
            db,
            sql,
            {"start_year": start_year, "end_year": end_year, "top_n": top_n},
        )

        if rows:
            top_item = rows[0]
            insight = f"Top hotspot block is {top_item['block_name']} with {top_item['crime_count']} cases."
        else:
            insight = "No data available under current filters."

        return self._build_analysis(
            analysis_id="top_blocks",
            title="Top Crime Blocks",
            description="Top blocks with highest number of cases.",
            chart_type="bar",
            dimensions=["block_name"],
            metrics=["crime_count"],
            data=rows,
            insight=insight,
        )

    def yoy_top_types(
        self,
        db: Session,
        start_year: int | None = None,
        end_year: int | None = None,
        top_n: int = 5,
    ) -> dict[str, Any]:
        sql = """
        WITH top_types AS (
            SELECT primary_type
            FROM crimes_clean
            WHERE primary_type IS NOT NULL
              AND (:start_year IS NULL OR year_num >= :start_year)
              AND (:end_year IS NULL OR year_num <= :end_year)
            GROUP BY primary_type
            ORDER BY COUNT(*) DESC
            LIMIT :top_n
        )
        SELECT
            c.year_num,
            c.primary_type,
            COUNT(*) AS crime_count
        FROM crimes_clean c
        INNER JOIN top_types t ON c.primary_type = t.primary_type
        WHERE c.year_num IS NOT NULL
          AND (:start_year IS NULL OR c.year_num >= :start_year)
          AND (:end_year IS NULL OR c.year_num <= :end_year)
        GROUP BY c.year_num, c.primary_type
        ORDER BY c.year_num, crime_count DESC
        """

        rows = self._fetch_all(
            db,
            sql,
            {"start_year": start_year, "end_year": end_year, "top_n": top_n},
        )

        insight = "Track yearly trend among the most frequent crime types."
        if not rows:
            insight = "No data available under current filters."

        return self._build_analysis(
            analysis_id="yoy_top_types",
            title="Year-over-Year Trend of Top Crime Types",
            description="Compare annual trends for the most common crime categories.",
            chart_type="line",
            dimensions=["year_num", "primary_type"],
            metrics=["crime_count"],
            data=rows,
            insight=insight,
        )

    def conclusions(
        self,
        db: Session,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> dict[str, Any]:
        annual = self.annual_trend(db, start_year=start_year, end_year=end_year, crime_type=None)["data"]
        weekly = self.weekly_distribution(db, start_year=start_year, end_year=end_year, crime_type=None)["data"]
        hourly = self.hourly_distribution(db, start_year=start_year, end_year=end_year, crime_type=None)["data"]
        type_share = self.crime_type_share(db, year_num=None, top_n=10)["data"]
        district_top = self.district_comparison(db, start_year=start_year, end_year=end_year, top_n=1)["data"]
        community_top = self.community_area_comparison(db, start_year=start_year, end_year=end_year, top_n=1)["data"]
        arrest_trend = self.arrest_rate_by_year(db, start_year=start_year, end_year=end_year)["data"]
        domestic_trend = self.domestic_rate_by_year(db, start_year=start_year, end_year=end_year)["data"]
        monthly = self.monthly_seasonality(db, start_year=start_year, end_year=end_year, crime_type=None)["data"]
        top_blocks = self.top_blocks(db, start_year=start_year, end_year=end_year, top_n=1)["data"]

        period = self._fetch_one(
            db,
            """
            SELECT
                MIN(year_num) AS min_year,
                MAX(year_num) AS max_year,
                COUNT(*) AS total_rows
            FROM crimes_clean
            WHERE (:start_year IS NULL OR year_num >= :start_year)
              AND (:end_year IS NULL OR year_num <= :end_year)
            """,
            {"start_year": start_year, "end_year": end_year},
        ) or {"min_year": None, "max_year": None, "total_rows": 0}

        conclusions: list[dict[str, Any]] = []

        conclusions.append(
            {
                "rank": 1,
                "title": "Dataset scale",
                "conclusion": (
                    f"Within selected range, total records are {period['total_rows']} "
                    f"from {period['min_year']} to {period['max_year']}."
                ),
                "evidence": period,
            }
        )

        if annual:
            peak_year = max(annual, key=lambda item: item["crime_count"])
            low_year = min(annual, key=lambda item: item["crime_count"])
            conclusions.append(
                {
                    "rank": 2,
                    "title": "Peak annual crime",
                    "conclusion": f"Peak annual volume is in {peak_year['year_num']} with {peak_year['crime_count']} cases.",
                    "evidence": peak_year,
                }
            )
            conclusions.append(
                {
                    "rank": 3,
                    "title": "Lowest annual crime",
                    "conclusion": f"Lowest annual volume is in {low_year['year_num']} with {low_year['crime_count']} cases.",
                    "evidence": low_year,
                }
            )
        else:
            conclusions.append(
                {
                    "rank": 2,
                    "title": "Peak annual crime",
                    "conclusion": "No annual data available.",
                    "evidence": {},
                }
            )
            conclusions.append(
                {
                    "rank": 3,
                    "title": "Lowest annual crime",
                    "conclusion": "No annual data available.",
                    "evidence": {},
                }
            )

        if weekly:
            peak_weekday = max(weekly, key=lambda item: item["crime_count"])
            conclusions.append(
                {
                    "rank": 4,
                    "title": "Peak weekday",
                    "conclusion": (
                        f"Weekday {peak_weekday['weekday_name']} is the highest-crime day "
                        f"with {peak_weekday['crime_count']} cases."
                    ),
                    "evidence": peak_weekday,
                }
            )
        else:
            conclusions.append(
                {
                    "rank": 4,
                    "title": "Peak weekday",
                    "conclusion": "No weekday distribution data available.",
                    "evidence": {},
                }
            )

        if hourly:
            peak_hour = max(hourly, key=lambda item: item["crime_count"])
            conclusions.append(
                {
                    "rank": 5,
                    "title": "Peak hour",
                    "conclusion": (
                        f"Hour {peak_hour['hour_num']} is the peak crime hour "
                        f"with {peak_hour['crime_count']} cases."
                    ),
                    "evidence": peak_hour,
                }
            )
        else:
            conclusions.append(
                {
                    "rank": 5,
                    "title": "Peak hour",
                    "conclusion": "No hourly distribution data available.",
                    "evidence": {},
                }
            )

        if type_share:
            top_type = type_share[0]
            conclusions.append(
                {
                    "rank": 6,
                    "title": "Top crime type",
                    "conclusion": (
                        f"Top crime type is {top_type['primary_type']} with {top_type['crime_count']} cases "
                        f"({top_type['percentage']}%)."
                    ),
                    "evidence": top_type,
                }
            )
        else:
            conclusions.append(
                {
                    "rank": 6,
                    "title": "Top crime type",
                    "conclusion": "No crime-type share data available.",
                    "evidence": {},
                }
            )

        if district_top:
            conclusions.append(
                {
                    "rank": 7,
                    "title": "Top district",
                    "conclusion": (
                        f"District {district_top[0]['district']} ranks first with "
                        f"{district_top[0]['crime_count']} cases."
                    ),
                    "evidence": district_top[0],
                }
            )
        else:
            conclusions.append(
                {
                    "rank": 7,
                    "title": "Top district",
                    "conclusion": "No district comparison data available.",
                    "evidence": {},
                }
            )

        if community_top:
            conclusions.append(
                {
                    "rank": 8,
                    "title": "Top community area",
                    "conclusion": (
                        f"Community area {community_top[0]['community_area']} ranks first with "
                        f"{community_top[0]['crime_count']} cases."
                    ),
                    "evidence": community_top[0],
                }
            )
        else:
            conclusions.append(
                {
                    "rank": 8,
                    "title": "Top community area",
                    "conclusion": "No community-area comparison data available.",
                    "evidence": {},
                }
            )

        if len(arrest_trend) >= 2:
            first = arrest_trend[0]
            last = arrest_trend[-1]
            conclusions.append(
                {
                    "rank": 9,
                    "title": "Arrest rate change",
                    "conclusion": (
                        f"Arrest rate changed from {first['arrest_rate']}% in {first['year_num']} "
                        f"to {last['arrest_rate']}% in {last['year_num']}."
                    ),
                    "evidence": {"first": first, "last": last},
                }
            )
        elif arrest_trend:
            conclusions.append(
                {
                    "rank": 9,
                    "title": "Arrest rate level",
                    "conclusion": (
                        f"Arrest rate in {arrest_trend[0]['year_num']} is "
                        f"{arrest_trend[0]['arrest_rate']}%."
                    ),
                    "evidence": arrest_trend[0],
                }
            )
        else:
            conclusions.append(
                {
                    "rank": 9,
                    "title": "Arrest rate change",
                    "conclusion": "No arrest trend data available.",
                    "evidence": {},
                }
            )

        if domestic_trend:
            peak_domestic = max(domestic_trend, key=lambda item: item["domestic_rate"])
            conclusions.append(
                {
                    "rank": 10,
                    "title": "Domestic incident burden",
                    "conclusion": (
                        f"Highest domestic incident rate is {peak_domestic['domestic_rate']}% "
                        f"in {peak_domestic['year_num']}."
                    ),
                    "evidence": peak_domestic,
                }
            )
        else:
            conclusions.append(
                {
                    "rank": 10,
                    "title": "Domestic incident burden",
                    "conclusion": "No domestic trend data available.",
                    "evidence": {},
                }
            )

        if monthly:
            peak_month = max(monthly, key=lambda item: item["crime_count"])
            conclusions.append(
                {
                    "rank": 11,
                    "title": "Peak month",
                    "conclusion": (
                        f"Month {peak_month['month_num']} has the highest seasonal volume "
                        f"with {peak_month['crime_count']} cases."
                    ),
                    "evidence": peak_month,
                }
            )

        if top_blocks:
            conclusions.append(
                {
                    "rank": 12,
                    "title": "Highest-risk block",
                    "conclusion": (
                        f"Top block is {top_blocks[0]['block_name']} with "
                        f"{top_blocks[0]['crime_count']} cases."
                    ),
                    "evidence": top_blocks[0],
                }
            )

        return {
            "total": len(conclusions),
            "conclusions": conclusions,
        }
