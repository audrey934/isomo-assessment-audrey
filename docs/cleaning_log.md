#Cleaning Log

## Reference data

### master_student.csv
- Rows: 1,002
- The raw file had `learner_id` and `school_id` columns but both were completely empty. Fixed `learner_id` by matching each student to the mapping table built using their name and class combination. Every single student got an ID.
- `school_id` is still empty for everyone. master_student just doesn't say which school each student belongs to there's no school column to work with. This will befixed after cleaning the typing and quill files, which have school names.
- 3 students have no class combination listed. There is a flag column to mark them instead of removing them. They're real students, just missing that one detail.
- Column names cleaned up (lowercase, underscores).

### master_school.csv
- Rows: 40
- Also had empty IDs. fixed by matching on school name from the mapping table. All 40 schools got their ID.

## Platform files

### typing_lesson_activity.csv

-13,306 rows
-no learner IDs in source (only usernames / emails depending on row)
-used username-based matching via LearnerResolver
-school matched using school_name when available
-dates converted into standard ISO format (date only, time dropped)
-added: internal_learner_id, resolved_school_id, match_route, confidence
-quite a few rows (around 30%) have missing school info — kept them, just flagged

### typing_test_attempts.csv
-14,533 rows
-same identity limitations as lesson activity
-learner resolution same pipeline (username-based matching)
-date format was inconsistent (DD/MM vs ISO), normalized during cleaning
-kept repeated attempts since they’re meaningful for progress tracking

### quill_activity_long.csv
- Rows: 12,311
- Learner identifiers were inconsistent (names, external Quill IDs, missing emails).
- Applied 3-tier matching: email, external ID, fuzzy name matching against master_student.
- Rows matched to internal learner IDs; unmatched rows were retained and flagged.
- Columns were standardized (lowercase, underscores), timestamps normalized

### quill_connect_sessions.csv
- Rows: 11,715
- Same raw identity issues as activity data (Quill IDs, learner names, inconsistent identifiers).
- Applied identical learner resolution pipeline to assign internal_learner_id.
- Session-level fields (activity type, tool, completion status, time spent, scores) were standardized for consistency.
- Date formatting and boolean fields were normalized to ensure uniform structure across records.

## Assessments

### det_scores_long.csv
- 891 rows
- raw file had duplicate column structures (two exports merged together)
- cleaned by dropping duplicate schema and standardizing column names
- learner resolution done using email prefix matching
- surname column was messy (mixed IDs, numbers, corrupted values) so it was left for audit only
- duplicate attempts kept since they’re valid test retakes

### efset_results_long.csv
- 957 rows
- learner matched using email prefix
- some emails had typos or wrong domains but were not corrected (only flagged)
- repeated attempts kept
- dates normalized to ISO format

### northstar_results_long.csv
- 2,131 rows
- mixed structure:
- PDF extracts → learner-level data (name-based matching works)
- CSV exports → school-level only (no learner info at all)
- CSV rows cannot be linked to individuals, so they’re explicitly marked unresolvable
- PDF rows parsed from filenames and matched using fuzzy name matching
- this dataset is partly individual-level, partly aggregate-level by design

