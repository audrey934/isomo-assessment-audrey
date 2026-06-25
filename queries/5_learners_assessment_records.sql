-- Q5: Which learners have records in all three assessments?
-- and which have only one?

WITH all_assessments AS (
    SELECT internal_learner_id, 'efset' AS src FROM efset_results
    UNION ALL
    SELECT internal_learner_id, 'det' FROM det_scores
    UNION ALL
    SELECT internal_learner_id, 'northstar' FROM northstar_results
),

counts AS (
    SELECT
        internal_learner_id,
        COUNT(DISTINCT src) AS assessment_count
    FROM all_assessments
    GROUP BY internal_learner_id
)

SELECT
    internal_learner_id,
    assessment_count,
    CASE
        WHEN assessment_count = 3 THEN 'all_three_assessments'
        WHEN assessment_count = 2 THEN 'two_assessments'
        WHEN assessment_count = 1 THEN 'one_assessment'
        ELSE 'unknown'
    END AS category
FROM counts
ORDER BY assessment_count DESC;