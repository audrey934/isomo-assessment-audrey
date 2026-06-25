# Isomo Assessment
## Project Description
This project analyzes learner engagement by comparing engagement across learning platforms (Typing and Quill) activity logs and their EFSet, Duolingo (DET), and Northstar assessment records. 

## Needed data:
- Which learners are actively engaging with the Typing and Quill learning platforms, and are the learners with the most engagement also the ones showing up in assessment records  or are there gaps?
- **Layer 1 (repo setup):** complete.
- **Layer 2 (learner & school IDs):** complete — hash-based, stable IDs; see `docs/ID_DESIGN.md`.
- **Layer 3 (cleaning & loading):** complete for all source files; see `docs/cleaning_log.md`.
- **Layer 4 (SQL analysis):** complete — 6 required queries plus 1 of my own, all in `queries/`.
- **Layer 5:** `analysis/engagement_report.md`  `analysis/school_summary.csv`,`analysis/generate_engagement_outputs.py`.
-isomo-assessment-Claude + Codex

## Repository structure

| Folder | Contents |
|---|---|
| `data/` | Cleaned datasets only — one CSV per source file, plus the learner/school ID mapping tables. Raw source files are never committed. |
| `queries/` | One `.sql` file per analysis question. |
| `analysis/` | Cleaning scripts, the learner/school matching logic, database loading, and the final engagement report. |
| `docs/` | Design decisions and process documentation. |
| `raw/` | Original source files. Gitignored; never pushed to GitHub. |

## How the data connects

None of the source files share a common ID. Learner and school IDs are generated independently `ID_LRN_######` / `ID_SCH_######`, derived from a SHA-256 hash of each learner's or school's own identifying fields rather than their row position, so IDs stay stable even if the source data is reordered or regenerated. Full rationale is in `docs/ID_DESIGN.md`.

Once IDs exist, every platform and assessment file still needs to be *linked back* to them — and none of those files share a clean identifier either. Usernames, emails, and free-text names are matched back to a known learner through a tiered process (exact full-name match, regardless of word order, finding usernames built from a first and middle name, typo-tolerant fuzzy matching, also order-invariant). Genuinely ambiguous cases — two real students sharing a name, with nothing else available to tell them apart — are explicitly flagged rather than guessed at. Details and known edge cases are in `docs/ID_DESIGN.md` and `docs/cleaning_log.md`.


**A learner counts toward any total in this report or in `queries/` if their identity is confidently resolved** (`match_route` is `matched_exact` or `matched_fuzzy`) **— regardless of whether their school is known, and counting every assessment attempt, not just a first attempt.** School-level breakdowns naturally require a known school in addition, since a learner can't be attributed to a school row otherwise — but that's a separate, additional condition layered on top of identity, not a different definition of "is this a real learner."

## Reproducing the analysis

1. Clean the source files:
```bash
   python3 analysis/reference_clean.py
   python3 analysis/quill_clean.py
   python3 analysis/typing_clean.py
   python3 analysis/assessment_clean.py
```
2. Set up a `.env` file (not committed) with `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`.
3. Load the cleaned data into PostgreSQL:
```bash
   python3 analysis/load_to_db.py
```
4. Run any query in `queries/` directly against the database, or regenerate the full report:
```bash
   python3 analysis/generate_engagement_outputs.py
```

## Key findings

Full detail and the school-by-school breakdown are in [`analysis/engagement_report.md`](analysis/engagement_report.md). Headlines:

- **847** learners are active on at least one platform (Typing or Quill); **869** appear in at least one assessment record (EFSet, DET, or Northstar).
- **68** learners are active on a platform but have no assessment record at all 
- Of the 869 assessed learners: 214 have all three assessments, 541 have exactly two, and 115 have only one.
- Northstar coverage is structurally lower than DET and EFSet: Northstar records are mostly a large school-level CSV exports with no learner identifier at all, so it's useful for school-level context but can't contribute to learner-level counts.
- A consistent set of 6 schools show high Quill Connect usage paired with below-average scores (e.g. GS Rambura Filles, Es Ruhango, ES Gikonko): these schools might be in need of targeted academic support rather than more usage prompts.
- 22 schools have at least one platform-active learner with no assessment record; the largest single-school gap is 7 learners (ENDP Karubanda, ES Juru, GS Gihundwe).

## Known limitations

- two real students sharing a first and middle name, where the available data has no other field to disambiguate them. These are flagged `ambiguous` and excluded from learner-level counts rather than guessed at.
- A majority of Northstar records are school-level aggregates with no learner identifier; these are marked `unresolvable` and used only for school-level context.
- Unmatched and ambiguous rows are never silently dropped, they're retained and flagged in every cleaned file

## AI usage

This project used an AI coding assistant throughout:  for the ID design discussion, debugging the name-matching logic, drafting and testing SQL queries, and reviewing the final repository structure. Every fix was verified against the actual data (measured before/after, not assumed) before being accepted. See `docs/ai_log.md` for the specifics, including what the AI got wrong and what had to be corrected.

