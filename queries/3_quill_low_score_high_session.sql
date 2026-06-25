-- Q3: Which schools have learners on Quill with high session counts but low average scores?
--
-- Design notes:
--   - Source table: quill_connect_sessions (one row per session, score_pct per session)
--   - "High session count": school is in the top 50% by total sessions (>= median)
--   - "Low average score": school avg score is below the cross-school mean (~95.4%)
--   - Score distribution is heavily right-skewed (median session score = 100%), so we
--     compare to the cross-school mean rather than median to surface underperformers.
--   - Rows without a resolved school ID are excluded (no_school_info tier).

WITH school_stats AS (
    SELECT
        resolved_school_id,
        canonical_school_name,
        COUNT(*)                                AS session_count,
        COUNT(DISTINCT internal_learner_id)     AS unique_learners,
        ROUND(AVG(score_pct)::numeric, 1)       AS avg_score_pct
    FROM quill_connect_sessions
    WHERE resolved_school_id IS NOT NULL
    GROUP BY resolved_school_id, canonical_school_name
),

thresholds AS (
    SELECT
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY session_count) AS high_session_threshold,
        AVG(avg_score_pct)                                          AS low_score_threshold
    FROM school_stats
)

SELECT
    s.resolved_school_id,
    s.canonical_school_name,
    s.session_count,
    s.unique_learners,
    s.avg_score_pct,
    ROUND(t.low_score_threshold::numeric, 1) AS mean_score_across_schools
FROM school_stats s
CROSS JOIN thresholds t
WHERE
    s.session_count  >= t.high_session_threshold
    AND s.avg_score_pct < t.low_score_threshold
ORDER BY s.avg_score_pct ASC;