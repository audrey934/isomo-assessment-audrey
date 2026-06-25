# AI Usage Log

I used Claude and codex throughout this project, mostly as a thinking partner for the harder design decisions and as a second pair of eyes on bugs I'd already half-found myself. This log is my honest account of what actually happened — including the parts where I had to push back on what it gave me.

---

## Layer 2 — ID generation and school matching

I asked it to help me design a learner and school ID system, and write the matching logic to link messy school names across files back to a single canonical ID.

The ID format itself (hash-based, not sequential) was right from the first pass, and I liked the reasoning behind it. WHile for sequential IDs break the moment someone reorders or inserts a row, and a hash of the learner's own name and class doesn't have that problem.

The first version of the school matcher had a real bug, though: a stray `return` statement sitting before the actual matching tiers ran, so every single school silently resolved to `None`. The output CSV looked completely normal but had nothing useful in them. I only caught it because I happened to check the Quill output closely instead of trusting that "no errors" meant "it worked." 

It also assumed `master_student.csv` had an email column to match on. It doesn't, I had to redirect it toward name-based matching instead, which became the actual hard part of this whole assignment.

What I did to check it: removed the dead `return`, then manually spot-checked about 10 school names against the crosswalk myself before trusting the rest.

## Layer 3 — cleaning all the source files, and apply name matching

This is where most of my actual time went, and where the back-and-forth with the AI was most useful.

The `LearnerResolver` logic (matching a raw username or email back to a real learner) went through several real rounds of fixes, not just the first pass:

- The original fallback strategy for reconstructing a name from a username only ever checked the *first two* tokens of a person's full name. So a username built from a first name and a *middle* name (skipping the surname entirely) — like `xaviosezerano` for "Sezerano Dominique Xavio" — failed outright. I found this by noticing the pattern myself in real unmatched rows, not because the tool flagged it.
- Fixing that by checking every possible pair of tokens fixed that case, but I made sure to actually measure the blast radius before trusting it — and it introduced new false collisions where a complete two-word name started getting reinterpreted as a fragment of someone else's three-word name. I caught this by re-running the new logic against every file and diffing the before/after match routes, not just trusting that "more matches" meant "better."
- Fixed *that* by checking for an exact full-name match before ever falling back to partial-token guessing — order of operations mattered more than I expected here.
- Separately, I found a typo case (`annabellamutara` for "Mutara Anabella" — note the extra `n`) that the fuzzy-matching tier missed entirely, because it was comparing against the name in its *written* order (surname-first) instead of the order the username actually used. Fixing the fuzzy comparison to check both orderings caught this and about 270 other previously-unmatched names across every file, with zero new false matches introduced — the one fix in this whole chain that was a clean win with no tradeoff.

I want to be upfront that I verified every one of these fixes with real before/after numbers across the actual dataset before committing to them, rather than assuming a fix that worked on one example was safe everywhere. A couple of the "improvements" weren't free — they traded a small number of new genuine ambiguities for a much larger number of real fixes, and I made sure I could see and explain that tradeoff rather than just taking the bigger number at face value.

Separately from the name-matching saga: the first version of `typing_clean.py` checked whether the raw `learner_id` column was non-null to decide if a row had matched — but that column is empty for every row in the typing source, so everything came back `unmatched` no matter what. Had to redirect toward actually reconstructing names from `username_raw` instead. `assessment_clean.py` also broke on DET specifically, because that file has two overlapping column sets (an original export plus what looks like a pre-processed version) that both became `email` after lowercasing the headers — fixed by dropping the duplicate schema before standardising. The Northstar filename regex needed two passes before it handled all the spacing variants around dashes that show up in the actual filenames.

One more thing worth recording here: partway through cleaning, I noticed every raw source file — not just one — already came with its own pre-filled `learner_id`/`school_id`/`match_route` columns, using prefixes (`IS_CIR_`, `IS_SCH_`) that look exactly like Paccy's internal pipeline output, not a raw export. I didn't drop or overwrite these — I renamed them to `source_*_raw` so they're preserved for reference without colliding with my own resolved IDs.

## Layer 4 — SQL queries

I asked for six required queries plus one of my own choosing.

Q2 (top schools by Typing activity) and Q5 (assessment coverage per learner) were right on the first attempt. The general shape of Q6 — building school-level totals via separate CTEs per source, then joining them all back to the master school list — was also the right structure from the start.

Q3 was the one that needed real rework. The first version tried to detect "low performance" by string-matching activity *names* for the word "incorrect" — but that column holds lesson titles, not outcome labels, so nothing ever matched. The real signal (`score_pct` per session) lives in `quill_connect_sessions`, not `quill_activity`, and that version was also referencing the raw platform-supplied `learner_id` instead of my created `internal_learner_id`. 

A few queries also needed explicit guards added to exclude unresolved rows properly, and Q6's logic for counting learners with no assessment had a subtle bug — it checked for a NULL assessment count in a CTE that had already filtered NULLs out earlier, so that branch could never actually fire. Rewrote that part with a proper LEFT JOIN and CASE statement instead.

## Layer 5 — final output

For the final report, I didn't have the AI write the report content directly. Instead I used it to first cross-check that all the clean data files agreed with what the SQL queries were producing, and then to help me draft a clear prompt for a separate coding agent (Codex) to actually generate the report and CSV summary from the clean data, keeping the report generation itself reproducible and auditable rather than hand-written prose I'd have to re-verify from scratch.

The generated reports were great, but they had a slight mismatch with how to categorize learners who were on platforms, but didn't have records in assignments. It first checked whether the learner had a first attempt, which is different from the logic in queries which checks whether learner has any record at all. 

## What I'd do differently next time

I shouldn't assume clean-looking output means correct output.Run a schema/sanity check immediately after every cleaning script something small that just asserts the expected columns exist, that no row claiming a successful match actually has a null ID, and that date columns parsed the way I expect. Three separate bugs in this project (the dead return in the school matcher, the duplicate DET columns, the always-empty learner_id check in the old typing script) all would have surfaced the moment they happened instead of several steps later when a query quietly returned zero rows. I was checking outputs by eye each time, which works, but it's slower and easier to miss something than just having the check run automatically. That's become a bit of a theme for me on this 