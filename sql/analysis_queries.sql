-- SQL analysis examples on crimes_clean (at least 10 analysis angles)
USE chicago_crime;

-- 1) Annual trend (all crimes)
SELECT year_num, COUNT(*) AS crime_count
FROM crimes_clean
WHERE year_num IS NOT NULL
GROUP BY year_num
ORDER BY year_num;

-- 2) Annual trend (specific type: THEFT)
SELECT year_num, COUNT(*) AS crime_count
FROM crimes_clean
WHERE year_num IS NOT NULL
  AND primary_type = 'THEFT'
GROUP BY year_num
ORDER BY year_num;

-- 3) Weekday distribution (Mon-Sun)
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
  END AS weekday_name,
  COUNT(*) AS crime_count
FROM crimes_clean
WHERE weekday_num IS NOT NULL
GROUP BY weekday_num
ORDER BY weekday_num;

-- 4) Hourly distribution (0-23)
SELECT hour_num, COUNT(*) AS crime_count
FROM crimes_clean
WHERE hour_num IS NOT NULL
GROUP BY hour_num
ORDER BY hour_num;

-- 5) Crime type share (Top 10)
SELECT
  primary_type,
  COUNT(*) AS crime_count,
  ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct
FROM crimes_clean
WHERE primary_type IS NOT NULL
GROUP BY primary_type
ORDER BY crime_count DESC
LIMIT 10;

-- 6) District comparison
SELECT district, COUNT(*) AS crime_count
FROM crimes_clean
WHERE district IS NOT NULL
GROUP BY district
ORDER BY crime_count DESC
LIMIT 20;

-- 7) Community area comparison
SELECT community_area, COUNT(*) AS crime_count
FROM crimes_clean
WHERE community_area IS NOT NULL
GROUP BY community_area
ORDER BY crime_count DESC
LIMIT 20;

-- 8) Monthly seasonality
SELECT month_num, COUNT(*) AS crime_count
FROM crimes_clean
WHERE month_num IS NOT NULL
GROUP BY month_num
ORDER BY month_num;

-- 9) Arrest rate by year
SELECT
  year_num,
  SUM(CASE WHEN arrest = 1 THEN 1 ELSE 0 END) AS arrested_count,
  COUNT(*) AS total_count,
  ROUND(100 * SUM(CASE WHEN arrest = 1 THEN 1 ELSE 0 END) / COUNT(*), 2) AS arrest_rate
FROM crimes_clean
WHERE year_num IS NOT NULL
GROUP BY year_num
ORDER BY year_num;

-- 10) Domestic incident rate by year
SELECT
  year_num,
  SUM(CASE WHEN domestic = 1 THEN 1 ELSE 0 END) AS domestic_count,
  COUNT(*) AS total_count,
  ROUND(100 * SUM(CASE WHEN domestic = 1 THEN 1 ELSE 0 END) / COUNT(*), 2) AS domestic_rate
FROM crimes_clean
WHERE year_num IS NOT NULL
GROUP BY year_num
ORDER BY year_num;

-- 11) Year-over-year trend for top 5 crime types
WITH top_types AS (
  SELECT primary_type
  FROM crimes_clean
  WHERE primary_type IS NOT NULL
  GROUP BY primary_type
  ORDER BY COUNT(*) DESC
  LIMIT 5
)
SELECT
  c.year_num,
  c.primary_type,
  COUNT(*) AS crime_count
FROM crimes_clean c
INNER JOIN top_types t ON c.primary_type = t.primary_type
WHERE c.year_num IS NOT NULL
GROUP BY c.year_num, c.primary_type
ORDER BY c.year_num, crime_count DESC;

-- 12) Top high-risk blocks
SELECT block_name, COUNT(*) AS crime_count
FROM crimes_clean
WHERE block_name IS NOT NULL
  AND block_name <> ''
GROUP BY block_name
ORDER BY crime_count DESC
LIMIT 20;

-- 13) Weekday-hour heatmap source data
SELECT
  weekday_num,
  hour_num,
  COUNT(*) AS crime_count
FROM crimes_clean
WHERE weekday_num IS NOT NULL
  AND hour_num IS NOT NULL
GROUP BY weekday_num, hour_num
ORDER BY weekday_num, hour_num;
