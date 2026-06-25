-- Q6: School-level summary across ALL platforms + assessments
-- Learners are linked via internal_learner_id → school inferred from platform data

WITH learner_school AS (
    SELECT DISTINCT internal_learner_id, resolved_school_id
    FROM typing_lesson_activity
    WHERE internal_learner_id IS NOT NULL

    UNION

    SELECT DISTINCT internal_learner_id, resolved_school_id
    FROM quill_activity
    WHERE internal_learner_id IS NOT NULL
),

typing AS (
    SELECT resolved_school_id, COUNT(DISTINCT internal_learner_id) AS typing_learners
    FROM typing_lesson_activity
    GROUP BY resolved_school_id
),

quill AS (
    SELECT resolved_school_id, COUNT(DISTINCT internal_learner_id) AS quill_learners
    FROM quill_activity
    GROUP BY resolved_school_id
),

efset AS (
    SELECT ls.resolved_school_id,
           COUNT(DISTINCT e.internal_learner_id) AS efset_learners
    FROM efset_results e
    JOIN learner_school ls USING (internal_learner_id)
    GROUP BY ls.resolved_school_id
),

det AS (
    SELECT ls.resolved_school_id,
           COUNT(DISTINCT d.internal_learner_id) AS det_learners
    FROM det_scores d
    JOIN learner_school ls USING (internal_learner_id)
    GROUP BY ls.resolved_school_id
),

northstar AS (
    SELECT ls.resolved_school_id,
           COUNT(DISTINCT n.internal_learner_id) AS northstar_learners
    FROM northstar_results n
    JOIN learner_school ls USING (internal_learner_id)
    GROUP BY ls.resolved_school_id
),

assessment_presence AS (
    SELECT internal_learner_id,
           COUNT(DISTINCT source) AS assessment_count
    FROM (
        SELECT internal_learner_id, 'efset' AS source FROM efset_results
        UNION ALL
        SELECT internal_learner_id, 'det' FROM det_scores
        UNION ALL
        SELECT internal_learner_id, 'northstar' FROM northstar_results
    ) x
    GROUP BY internal_learner_id
),

assessment_by_school AS (
    SELECT ls.resolved_school_id,
           COUNT(CASE WHEN a.assessment_count >= 1 THEN 1 END) AS learners_with_any_assessment,
           COUNT(CASE WHEN a.assessment_count IS NULL THEN 1 END) AS learners_with_no_assessment
    FROM learner_school ls
    LEFT JOIN assessment_presence a USING (internal_learner_id)
    GROUP BY ls.resolved_school_id
)

SELECT
    ms.school_id,
    ms.canonical_name,

    COALESCE(t.typing_learners, 0) AS typing_learners,
    COALESCE(q.quill_learners, 0) AS quill_learners,
    COALESCE(e.efset_learners, 0) AS efset_learners,
    COALESCE(d.det_learners, 0) AS det_learners,
    COALESCE(n.northstar_learners, 0) AS northstar_learners,

    COALESCE(a.learners_with_any_assessment, 0) AS learners_with_assessment,
    COALESCE(a.learners_with_no_assessment, 0) AS learners_without_assessment

FROM master_school ms
LEFT JOIN typing t ON ms.school_id = t.resolved_school_id
LEFT JOIN quill q ON ms.school_id = q.resolved_school_id
LEFT JOIN efset e ON ms.school_id = e.resolved_school_id
LEFT JOIN det d ON ms.school_id = d.resolved_school_id
LEFT JOIN northstar n ON ms.school_id = n.resolved_school_id
LEFT JOIN assessment_by_school a ON ms.school_id = a.resolved_school_id
ORDER BY ms.canonical_name;