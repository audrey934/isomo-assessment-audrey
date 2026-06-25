-- Q2: Which schools have the most active learners on Typing?

SELECT
    resolved_school_id,
    canonical_school_name,
    COUNT(DISTINCT internal_learner_id) AS active_learners,
    COUNT(*) AS total_lesson_activities
FROM typing_lesson_activity
WHERE school_match_tier != 'no_school_info'
GROUP BY resolved_school_id, canonical_school_name
ORDER BY total_lesson_activities DESC;