-- Q4: Learners in platforms but missing all assessments

WITH platform_learners AS (
    SELECT DISTINCT internal_learner_id FROM typing_lesson_activity
    UNION
    SELECT DISTINCT internal_learner_id FROM quill_activity
),
assessed AS (
    SELECT DISTINCT internal_learner_id FROM efset_results
    UNION
    SELECT DISTINCT internal_learner_id FROM det_scores
    UNION
    SELECT DISTINCT internal_learner_id FROM northstar_results
)

SELECT p.internal_learner_id
FROM platform_learners p
LEFT JOIN assessed a ON p.internal_learner_id = a.internal_learner_id
WHERE a.internal_learner_id IS NULL
  AND p.internal_learner_id IS NOT NULL  -- add this line
ORDER BY p.internal_learner_id;