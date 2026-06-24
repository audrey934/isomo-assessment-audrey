# Cleaning Log

## master_student.csv
- Rows: 1,002
- The raw file had `learner_id` and `school_id` columns but both were completely empty. Fixed `learner_id` by matching each student to the mapping table built using their name and class combination. Every single student got an ID.
- `school_id` is still empty for everyone. master_student just doesn't say which school each student belongs to there's no school column to work with. This will befixed after cleaning the typing and quill files, which have school names.
- 3 students have no class combination listed. There is a flag column to mark them instead of removing them. They're real students, just missing that one detail.
- Column names cleaned up (lowercase, underscores).

## master_school.csv
- Rows: 40
- Also had empty IDs. fixed by matching on school name from the mapping table. All 40 schools got their ID.
