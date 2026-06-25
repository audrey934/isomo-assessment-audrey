from pathlib import Path
import re

import pandas as pd


DATA_DIR = Path("data")
OUT_DIR = Path("analysis")
RESOLVED_ROUTES = {"matched_exact", "matched_fuzzy"}


def read_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / name)


def resolved_platform(df: pd.DataFrame) -> pd.DataFrame:
    mask = df["match_route"].isin(RESOLVED_ROUTES)
    mask &= df["internal_learner_id"].notna()
    mask &= df["resolved_school_id"].notna()
    return df.loc[mask].copy()


def resolved_learners(df: pd.DataFrame) -> pd.DataFrame:
    mask = df["match_route"].isin(RESOLVED_ROUTES)
    mask &= df["internal_learner_id"].notna()
    return df.loc[mask].copy()



def normalise_school_name(value) -> str:
    if pd.isna(value):
        return ""
    return re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()


def learner_set(df: pd.DataFrame) -> set:
    return set(df["internal_learner_id"].dropna().astype(str))


def group_nunique(df: pd.DataFrame, value_col: str, out_col: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["school_id", out_col])
    return (
        df.groupby("resolved_school_id")[value_col]
        .nunique()
        .rename(out_col)
        .reset_index()
        .rename(columns={"resolved_school_id": "school_id"})
    )


def group_size(df: pd.DataFrame, out_col: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["school_id", out_col])
    return (
        df.groupby("resolved_school_id")
        .size()
        .rename(out_col)
        .reset_index()
        .rename(columns={"resolved_school_id": "school_id"})
    )


def school_learner_sets(df: pd.DataFrame) -> dict[str, set]:
    if df.empty:
        return {}
    return (
        df.groupby("resolved_school_id")["internal_learner_id"]
        .apply(lambda s: set(s.dropna().astype(str)))
        .to_dict()
    )


def markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No schools met this condition._"
    rows = df.copy()
    rows = rows.fillna("")
    headers = [str(col) for col in rows.columns]
    aligns = ["---:" if pd.api.types.is_numeric_dtype(rows[col]) else "---" for col in rows.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(aligns) + " |",
    ]
    for _, row in rows.iterrows():
        values = []
        for value in row.tolist():
            if isinstance(value, float):
                values.append(f"{value:.1f}")
            elif isinstance(value, int):
                values.append(f"{value:,}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def plural(n: int, noun: str) -> str:
    return f"{n:,} {noun}" if n == 1 else f"{n:,} {noun}s"


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)

    schools = read_csv("master_school_clean.csv")[["school_id", "canonical_name"]].copy()
    schools = schools.rename(columns={"canonical_name": "school_name"})
    school_lookup = {
        normalise_school_name(row.school_name): row.school_id
        for row in schools.itertuples(index=False)
    }
    school_name_lookup = {
        row.school_id: row.school_name
        for row in schools.itertuples(index=False)
    }

    typing_all = read_csv("typing_lesson_activity_clean.csv")
    quill_all = read_csv("quill_activity_clean.csv")
    quill_sessions_all = read_csv("quill_connect_sessions_clean.csv")
    typing = resolved_platform(typing_all)
    quill = resolved_platform(quill_all)
    quill_sessions = resolved_platform(quill_sessions_all)

    typing_identity = resolved_learners(typing_all)
    quill_identity = resolved_learners(quill_all)


    raw_school_maps = []
    if "source_school_id" in typing_all.columns:
        raw_school_maps.append(typing_all[["source_school_id", "resolved_school_id"]].rename(columns={"source_school_id": "raw_school_id"}))
    if "school_id" in quill_all.columns:
        raw_school_maps.append(quill_all[["school_id", "resolved_school_id"]].rename(columns={"school_id": "raw_school_id"}))
    if "school_id" in quill_sessions_all.columns:
        raw_school_maps.append(quill_sessions_all[["school_id", "resolved_school_id"]].rename(columns={"school_id": "raw_school_id"}))
    raw_school_lookup = {}
    if raw_school_maps:
        raw_school_df = pd.concat(raw_school_maps, ignore_index=True).dropna()
        raw_school_lookup = (
            raw_school_df.drop_duplicates()
            .sort_values(["raw_school_id", "resolved_school_id"])
            .drop_duplicates("raw_school_id")
            .set_index("raw_school_id")["resolved_school_id"]
            .to_dict()
        )

    northstar_all = read_csv("northstar_results_clean.csv")
    if "school_folder" in northstar_all.columns:
        missing_school = northstar_all["resolved_school_id"].isna()
        mapped_school = northstar_all.loc[missing_school, "school_folder"].map(
            lambda value: school_lookup.get(normalise_school_name(value), pd.NA)
        )
        northstar_all.loc[missing_school, "resolved_school_id"] = mapped_school
    if "extracted_school" in northstar_all.columns and raw_school_lookup:
        missing_school = northstar_all["resolved_school_id"].isna()
        mapped_school = northstar_all.loc[missing_school, "extracted_school"].map(raw_school_lookup)
        northstar_all.loc[missing_school, "resolved_school_id"] = mapped_school
    missing_school = northstar_all["canonical_school_name"].isna()
    northstar_all.loc[missing_school, "canonical_school_name"] = northstar_all.loc[
        missing_school, "resolved_school_id"
    ].map(school_name_lookup)
    northstar = resolved_learners(northstar_all)
    northstar_school = northstar.loc[northstar["resolved_school_id"].notna()].copy()
    

    det_all = read_csv("det_scores_clean.csv")
    det = det_all.loc[det_all["internal_learner_id"].notna()].copy()
    det["internal_learner_id"] = det["internal_learner_id"].astype(str)

    efset_all = read_csv("efset_results_clean.csv")
    efset = efset_all.loc[efset_all["internal_learner_id"].notna()].copy()
    efset["internal_learner_id"] = efset["internal_learner_id"].astype(str)

    for df in (typing, quill, quill_sessions, northstar):
        df["internal_learner_id"] = df["internal_learner_id"].astype(str)

    # DET and EFSet have learner IDs but no school ID. Assign each learner to the
    # school with the strongest resolved school evidence in the listed files.
    school_evidence = pd.concat(
        [
            typing[["internal_learner_id", "resolved_school_id"]],
            quill[["internal_learner_id", "resolved_school_id"]],
            quill_sessions[["internal_learner_id", "resolved_school_id"]],
            northstar_school[["internal_learner_id", "resolved_school_id"]],
        ],
        ignore_index=True,
    ).dropna()
    learner_school = (
        school_evidence.groupby(["internal_learner_id", "resolved_school_id"])
        .size()
        .rename("evidence_rows")
        .reset_index()
        .sort_values(["internal_learner_id", "evidence_rows", "resolved_school_id"], ascending=[True, False, True])
        .drop_duplicates("internal_learner_id")
    )

    det_school = det.merge(learner_school, on="internal_learner_id", how="inner")
    efset_school = efset.merge(learner_school, on="internal_learner_id", how="inner")

    summary = schools.copy()
    aggregations = [
        group_nunique(typing, "internal_learner_id", "typing_learners"),
        group_size(typing, "typing_lessons"),
        group_nunique(quill, "internal_learner_id", "quill_learners"),
        group_size(quill_sessions, "quill_sessions"),
        (
            quill_sessions.groupby("resolved_school_id")["score_pct"]
            .mean()
            .round(1)
            .rename("quill_avg_score")
            .reset_index()
            .rename(columns={"resolved_school_id": "school_id"})
            if not quill_sessions.empty
            else pd.DataFrame(columns=["school_id", "quill_avg_score"])
        ),
        group_nunique(det_school, "internal_learner_id", "det_learners"),
        group_nunique(efset_school, "internal_learner_id", "efset_learners"),
        group_nunique(northstar_school, "internal_learner_id", "northstar_learners"),
    ]
    for agg in aggregations:
        summary = summary.merge(agg, on="school_id", how="left")

    typing_sets = school_learner_sets(typing)
    quill_sets = school_learner_sets(quill)
    assessment_ids = learner_set(det) | learner_set(efset) | learner_set(northstar)

    platform_counts = []
    for school_id in summary["school_id"]:
        platform = typing_sets.get(school_id, set()) | quill_sets.get(school_id, set())
        with_assessment = platform & assessment_ids
        without_assessment = platform - assessment_ids
        platform_counts.append(
            {
                "school_id": school_id,
                "platform_learners": len(platform),
                "learners_with_assessment": len(with_assessment),
                "learners_without_assessment": len(without_assessment),
            }
        )
    summary = summary.merge(pd.DataFrame(platform_counts), on="school_id", how="left")

    required_cols = [
        "school_id",
        "school_name",
        "typing_learners",
        "typing_lessons",
        "quill_learners",
        "quill_sessions",
        "quill_avg_score",
        "det_learners",
        "efset_learners",
        "northstar_learners",
        "platform_learners",
        "learners_with_assessment",
        "learners_without_assessment",
    ]
    summary = summary[required_cols].fillna(0)
    int_cols = [c for c in required_cols if c not in {"school_id", "school_name", "quill_avg_score"}]
    summary[int_cols] = summary[int_cols].astype(int)
    summary["quill_avg_score"] = summary["quill_avg_score"].astype(float).round(1)
    summary.to_csv(OUT_DIR / "school_summary.csv", index=False)

    typing_ids = learner_set(typing_identity)
    quill_ids = learner_set(quill_identity)
    det_ids = learner_set(det)
    efset_ids = learner_set(efset)
    northstar_ids = learner_set(northstar)
    platform_ids = typing_ids | quill_ids
    all_assessment_ids = det_ids | efset_ids | northstar_ids
    platform_without_assessment = platform_ids - all_assessment_ids

    overall = pd.DataFrame(
        [
            {"source": "Typing", "unique resolved learners": len(typing_ids)},
            {"source": "Quill", "unique resolved learners": len(quill_ids)},
            {"source": "DET baseline", "unique resolved learners": len(det_ids)},
            {"source": "EFSet baseline", "unique resolved learners": len(efset_ids)},
            {"source": "Northstar", "unique resolved learners": len(northstar_ids)},
        ]
    )

    assessment_depth = pd.DataFrame({"internal_learner_id": sorted(all_assessment_ids)})
    assessment_depth["assessment_count"] = assessment_depth["internal_learner_id"].map(
        lambda learner_id: int(learner_id in det_ids)
        + int(learner_id in efset_ids)
        + int(learner_id in northstar_ids)
    )
    depth_counts = assessment_depth["assessment_count"].value_counts().to_dict()

    northstar_csv_no_id = northstar_all.loc[
        (northstar_all["record_source"] == "csv")
        & northstar_all["internal_learner_id"].isna()
    ]
    northstar_csv_pct = 0.0 if len(northstar_all) == 0 else len(northstar_csv_no_id) / len(northstar_all) * 100

    typing_top = (
        typing.groupby("canonical_school_name")
        .agg(
            **{
                "unique learners": ("internal_learner_id", "nunique"),
                "total lesson activities": ("internal_learner_id", "size"),
            }
        )
        .reset_index()
        .rename(columns={"canonical_school_name": "school"})
        .sort_values(["total lesson activities", "unique learners", "school"], ascending=[False, False, True])
        .head(10)
    )

    active_quill_school_scores = summary.loc[summary["quill_sessions"] > 0].copy()
    median_sessions = float(active_quill_school_scores["quill_sessions"].median()) if not active_quill_school_scores.empty else 0.0
    mean_avg_score = float(active_quill_school_scores["quill_avg_score"].mean()) if not active_quill_school_scores.empty else 0.0
    quill_concern = (
        active_quill_school_scores.loc[
            (active_quill_school_scores["quill_sessions"] > median_sessions)
            & (active_quill_school_scores["quill_avg_score"] < mean_avg_score),
            ["school_name", "quill_sessions", "quill_avg_score"],
        ]
        .rename(columns={"school_name": "school", "quill_sessions": "sessions", "quill_avg_score": "avg score"})
        .sort_values(["sessions", "avg score", "school"], ascending=[False, True, True])
    )

    gap_by_school = (
        summary.loc[summary["learners_without_assessment"] > 0, ["school_name", "learners_without_assessment"]]
        .rename(columns={"school_name": "school"})
        .sort_values(["learners_without_assessment", "school"], ascending=[False, True])
    )

    typing_learner_counts = (
        typing.groupby(["resolved_school_id", "internal_learner_id"])
        .size()
        .rename("typing lessons")
        .reset_index()
    )
    quill_learner_counts = (
        quill_sessions.groupby(["resolved_school_id", "internal_learner_id"])
        .size()
        .rename("quill sessions")
        .reset_index()
    )
    learner_follow_up = pd.concat(
        [
            typing[["resolved_school_id", "internal_learner_id"]],
            quill[["resolved_school_id", "internal_learner_id"]],
        ],
        ignore_index=True,
    ).drop_duplicates()
    learner_follow_up = learner_follow_up.loc[
        learner_follow_up["internal_learner_id"].isin(platform_without_assessment)
    ].copy()
    learner_follow_up["school"] = learner_follow_up["resolved_school_id"].map(school_name_lookup)
    learner_follow_up = learner_follow_up.merge(
        typing_learner_counts, on=["resolved_school_id", "internal_learner_id"], how="left"
    )
    learner_follow_up = learner_follow_up.merge(
        quill_learner_counts, on=["resolved_school_id", "internal_learner_id"], how="left"
    )
    learner_follow_up[["typing lessons", "quill sessions"]] = learner_follow_up[
        ["typing lessons", "quill sessions"]
    ].fillna(0).astype(int)
    learner_follow_up["total platform activity"] = (
        learner_follow_up["typing lessons"] + learner_follow_up["quill sessions"]
    )
    learner_follow_up = learner_follow_up[
        ["school", "internal_learner_id", "typing lessons", "quill sessions", "total platform activity"]
    ].sort_values(["school", "total platform activity", "internal_learner_id"], ascending=[True, False, True])

    report = f"""# Learner Engagement And Assessment Coverage Report

## 1. Overall numbers

{markdown_table(overall)}

Total learners active on at least one learning platform: **{len(platform_ids):,}**.

Total learners found in at least one assessment record: **{len(all_assessment_ids):,}**.

Learners active on Typing or Quill but with no assessment record: **{len(platform_without_assessment):,}**.

## 2. Assessment depth

Of the {plural(len(all_assessment_ids), "learner")} with at least one assessment record:

| Assessment coverage | Learners |
|---|---:|
| All 3 assessments | {depth_counts.get(3, 0):,} |
| Exactly 2 assessments | {depth_counts.get(2, 0):,} |
| Exactly 1 assessment | {depth_counts.get(1, 0):,} |

Northstar coverage is lower than DET and EFSet because many Northstar source rows cannot be tied back to individual learners. In this cleaned file, {northstar_csv_pct:.0f}% of Northstar records are CSV rows with no learner identifier, so they are useful for school-level context but must be excluded from learner-level counts.

## 3. Most active schools on Typing

{markdown_table(typing_top)}

## 4. Quill: high volume, low scores

Median Quill Connect session count among schools with sessions: **{median_sessions:.1f}**.

Mean school average Quill Connect score among schools with sessions: **{mean_avg_score:.1f}%**.

{markdown_table(quill_concern)}

These schools have heavier-than-typical Quill Connect use, but their average scores are below the programme-wide school average. That pattern suggests learners are doing the practice, but these schools may need targeted support on the skills covered in Quill Connect rather than more reminders to log in.

## 5. Assessment gap by school

{markdown_table(gap_by_school)}

These are the platform-active learners who need assessment follow-up. The table has {len(platform_without_assessment):,} unique learners and {len(learner_follow_up):,} school-linked rows because a small number of learners have platform activity attached to more than one school.

{markdown_table(learner_follow_up)}

## 6. Conclusions and recommended actions

- Follow up first with the {len(platform_without_assessment):,} learners who are active on Typing or Quill but have no DET, EFSet, or resolved Northstar learner record.
- Prioritise assessment clean-up at the {len(gap_by_school):,} schools with platform-active learners missing assessment records; the largest single school gap is {int(gap_by_school.iloc[0]["learners_without_assessment"]) if not gap_by_school.empty else 0:,} learners.
- Use the Typing activity leaders as engagement examples: the top 10 schools generated {int(typing_top["total lesson activities"].sum()) if not typing_top.empty else 0:,} resolved lesson activities across {int(typing_top["unique learners"].sum()) if not typing_top.empty else 0:,} school-level learner counts.
- Give targeted academic support to the {len(quill_concern):,} high-volume, below-average Quill schools before increasing Quill assignment volume further.
"""

    (OUT_DIR / "engagement_report.md").write_text(report, encoding="utf-8")

    print("Wrote analysis/school_summary.csv")
    print("Wrote analysis/engagement_report.md")
    print(f"Platform learners: {len(platform_ids):,}")
    print(f"Assessed learners: {len(all_assessment_ids):,}")
    print(f"Platform but not assessed: {len(platform_without_assessment):,}")


if __name__ == "__main__":
    main()
