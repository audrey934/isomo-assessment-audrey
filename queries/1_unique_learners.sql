-- Q1: How many unique learners appear in each platform / assessment?
-- One row per source for clean comparison

SELECT 'typing' AS source, COUNT(DISTINCT internal_learner_id) AS learner_count
FROM typing_lesson_activity
WHERE match_route IN ('matched_exact','matched_fuzzy')

UNION ALL

SELECT 'quill', COUNT(DISTINCT internal_learner_id)
FROM quill_activity
WHERE match_route IN ('matched_exact','matched_fuzzy')

UNION ALL

SELECT 'efset', COUNT(DISTINCT internal_learner_id)
FROM efset_results

UNION ALL

SELECT 'det', COUNT(DISTINCT internal_learner_id)
FROM det_scores

UNION ALL

SELECT 'northstar', COUNT(DISTINCT internal_learner_id)
FROM northstar_results;