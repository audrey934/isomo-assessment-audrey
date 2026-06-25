-- Q7: Which schools have the highest proportion of unresolved records across platforms?
-- This identifies data quality issues in school matching and folder mapping.

WITH all_records AS (
    SELECT resolved_school_id FROM typing_lesson_activity
    UNION ALL
    SELECT resolved_school_id FROM quill_activity
),

school_counts AS (
    SELECT
        COALESCE(resolved_school_id, 'UNKNOWN') AS school_id,
        COUNT(*) AS total_records
    FROM all_records
    GROUP BY COALESCE(resolved_school_id, 'UNKNOWN')
)

SELECT *
FROM school_counts
WHERE school_id = 'UNKNOWN'
   OR total_records > 100
ORDER BY total_records DESC;