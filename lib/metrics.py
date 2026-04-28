
from __future__ import annotations

import pandas as pd
import numpy as np


CHILD_EMOTION_COLUMNS = [
    "happy", "surprised", "excited", "curious", "good_inside",
    "connected_to_others", "similar_to_a_character", "brave", "kinds",
    "did_you_learn_something_new"
]

PARENT_POSITIVE_COLUMNS = [
    "watched_closely",
    "asked_questions",
    "reacted_with_comments_laughter_or_sounds",
    "smiled_laughed_or_spoke_about_something_they_enjoyed",
    "talked_positively_about_something_they_did_or_related_to",
    "tried_something_new_spoke_up_more_than_usual_or_described_themselves_positively",
    "acted_something_out_pretended_to_be_a_character_or_started_making_up_a_story",
    "commented_on_something_new_they_noticed_about_another_culture_or_perspective",
    "appeared_comfortable_or_settled",
]

TOC_TO_COLUMNS = {
    "Spark & Engagement": ["happy", "surprised", "excited", "curious"],
    "Inclusion & Belonging": ["good_inside", "connected_to_others", "similar_to_a_character"],
    "Confidence & Agency": ["brave", "kinds", "did_you_learn_something_new"],
}

DEFAULT_OKRS = {
    "Spark & Engagement": 0.80,
    "Inclusion & Belonging": 0.75,
    "Confidence & Agency": 0.70,
    "Parent Advocacy": 8.5,
}


def _present_rate(df: pd.DataFrame, columns: list[str]) -> dict[str, float]:
    out = {}
    n = len(df) if len(df) else 1
    for col in columns:
        if col in df.columns:
            out[col] = round(df[col].notna().mean(), 3)
    return out


def build_headline_metrics(kpi_summary: pd.DataFrame, child_df: pd.DataFrame, parent_df: pd.DataFrame, perf_df: pd.DataFrame) -> dict[str, float]:
    child_responses = int(len(child_df))
    parent_responses = int(len(parent_df))
    avg_star = float(child_df["star_rating"].dropna().mean()) if "star_rating" in child_df.columns else np.nan
    avg_recommend = float(parent_df["how_likely_are_you_to_recommend_a_monkey_baa_show_to_other_parents_carers_or_teachers"].dropna().mean()) if "how_likely_are_you_to_recommend_a_monkey_baa_show_to_other_parents_carers_or_teachers" in parent_df.columns else np.nan
    shows = int(child_df["show_name"].nunique()) if "show_name" in child_df.columns else int(kpi_summary["show_name"].nunique())
    performances = int(len(perf_df))
    return {
        "Child responses": child_responses,
        "Parent responses": parent_responses,
        "Avg star rating": round(avg_star, 2) if pd.notna(avg_star) else np.nan,
        "Avg recommendation": round(avg_recommend, 2) if pd.notna(avg_recommend) else np.nan,
        "Shows covered": shows,
        "Performances loaded": performances,
    }


def child_emotion_summary(child_df: pd.DataFrame) -> pd.DataFrame:
    rates = _present_rate(child_df, CHILD_EMOTION_COLUMNS)
    return pd.DataFrame({"metric": list(rates.keys()), "rate": list(rates.values())}).sort_values("rate", ascending=False)


def parent_observation_summary(parent_df: pd.DataFrame) -> pd.DataFrame:
    rates = _present_rate(parent_df, PARENT_POSITIVE_COLUMNS)
    pretty = pd.DataFrame({"metric": list(rates.keys()), "rate": list(rates.values())})
    pretty["metric"] = pretty["metric"].str.replace("_", " ").str.title()
    return pretty.sort_values("rate", ascending=False)


def toc_progress(child_df: pd.DataFrame, parent_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    child_n = len(child_df) if len(child_df) else 1
    for outcome, columns in TOC_TO_COLUMNS.items():
        present_cols = [c for c in columns if c in child_df.columns]
        actual = float(np.mean([child_df[c].notna().mean() for c in present_cols])) if present_cols else 0
        target = DEFAULT_OKRS[outcome]
        rows.append({
            "objective_area": outcome,
            "actual": round(actual, 3),
            "target": target,
            "gap": round(actual - target, 3),
            "status": "On Track" if actual >= target else "Needs Attention"
        })

    if "how_likely_are_you_to_recommend_a_monkey_baa_show_to_other_parents_carers_or_teachers" in parent_df.columns:
        actual = float(parent_df["how_likely_are_you_to_recommend_a_monkey_baa_show_to_other_parents_carers_or_teachers"].dropna().mean())
        target = DEFAULT_OKRS["Parent Advocacy"]
        rows.append({
            "objective_area": "Parent Advocacy",
            "actual": round(actual, 2),
            "target": target,
            "gap": round(actual - target, 2),
            "status": "On Track" if actual >= target else "Needs Attention"
        })
    return pd.DataFrame(rows)


def year_show_rollup(kpi_summary: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in ["survey_year", "show_name", "child_responses", "avg_star_rating"] if c in kpi_summary.columns]
    return kpi_summary[cols].copy()


def quality_summary(qa_df: pd.DataFrame) -> pd.DataFrame:
    return qa_df.copy()
