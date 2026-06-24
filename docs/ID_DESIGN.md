# Learner and School ID Design

## Reason

In the provided source files, there is no common identifier. Names would be the only way to link fields and this becomes a big problem when students have identical names. 
example: in `master_student.csv`s ("Uwase Sandrine" and "Irakoze Diane" both appear twice). 

## What the IDs look like

`ID_LRN_######` for learners, `ID_SCH_######` for schools — a 6-digit number produced by hashing the learner's own identifying fields, not their
position in the file.

The process: normalize the text (lowercase, punctuation → spaces, collapse whitespace), hash with SHA-256, take mod 1,000,000, zero-pad to 6 digits.

**What goes into the hash:**
- Learner: `canonical_name` + `combinations` (their class/subject track).
  Since names were identical for the identified pairs, adding combinations could make a difference. 
- School: `canonical_name` only. All 40 names in `master_school.csv` are
  already unique, so one field is enough.

## Other considered Option

**Numbering sequentially:** This would mean numbers would be assigned according to the row number of each student. I decided to not use it due to the risk of the order changing. `master_student.csv` does not have an alphabetical row order, which suggests it's
just whatever order the database query returned. If by any chance, another person creates a different sort or inserts some data in the middle of the list, every person's id would change due to the shift in row positions. 

A hash-based ID only depends on the learner's own name and class. Re-run the script on a reordered or expanded file and every existing learner keeps the same ID automatically.


## Matching school names across files

Two problems came up when I looked at the crosswalk alongside the actual platform files:

**Problem 1 — variants the crosswalk doesn't cover.** Typing uses
`"Fawe Girls School - Gahini"`, but none of the six approved crosswalk
spellings for that school match it exactly.

**Problem 2 — similar names that are actually different schools.** Three
schools all have "Mubuga" in their name: `ES Mubuga`, `Gs Mubuga Gakenke`,
and `GS Mubuga N`. A string similarity approach could easily pick the wrong
one and look completely confident doing it.

So I built a four-step matcher that tries each approach in order and stops at
the first match:

1. Exact match against the canonical school name
2. Exact match against a known crosswalk spelling (approved entries only)
3. Normalized match — case, punctuation, and whitespace-insensitive — against
   either of the above. This alone handles the Fawe Girls hyphen and
   correctly separates the three Mubuga schools without guessing.
4. If nothing matches: fuzzy similarity is computed but **never automatically
   applied**. It logs the closest candidate and a similarity score for a
   human to confirm — specifically because the Mubuga case shows how a
   confident-looking fuzzy match can be confidently wrong.

Blank or `"NA"` school names are flagged as "no school info" and left
unmatched rather than guessed at.

Tested against all 13,306 rows of `typing_lesson_activity.csv`: 10,385
matched exactly, 214 matched via normalization (including both problem cases
above), 2,707 correctly flagged as no school info, and zero rows needed the
fuzzy step at all.

## What happens when a new cohort arrives

Learners: re-run the script on the combined student list. Everyone already in the system keeps their current ID. New learners get IDs the same way.

## Possible Risks
If two different students share both the same name and the same class combination, they'd end up with the same ID. In the current cohort, there is no such case, but it might happen in future cohorts. An idea to fix this would be adding the intake period or admission year. 

