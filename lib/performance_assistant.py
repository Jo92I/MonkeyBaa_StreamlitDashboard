from __future__ import annotations

import os
from datetime import datetime
import pandas as pd
from openai import OpenAI


def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get("OPENAI_API_KEY")
        except Exception:
            api_key = None

    if not api_key:
        return None

    return OpenAI(api_key=api_key)


def load_survey_data(file_paths: list[str]) -> pd.DataFrame:
    frames = []

    for path in file_paths:
        if path.endswith(".csv"):
            df = pd.read_csv(path)
        elif path.endswith(".xlsx"):
            df = pd.read_excel(path)
        else:
            continue

        df["source_file"] = path
        frames.append(df)

    if not frames:
        return pd.DataFrame()

    return pd.concat(frames, ignore_index=True)


def prepare_dates(df: pd.DataFrame) -> pd.DataFrame:
    date_columns = [
        "Submit Date (UTC)",
        "Start Date (UTC)",
        "Date",
        "date",
        "submission_date",
        "event_date",
    ]

    date_col = None
    for col in date_columns:
        if col in df.columns:
            date_col = col
            break

    if date_col is None:
        return df

    df["analysis_date"] = pd.to_datetime(df[date_col], errors="coerce", dayfirst=True)
    df = df.dropna(subset=["analysis_date"])

    df["year"] = df["analysis_date"].dt.year
    df["quarter"] = df["analysis_date"].dt.to_period("Q").astype(str)

    return df


def get_last_quarter_label() -> str:
    today = pd.Timestamp.today()
    current_quarter = today.to_period("Q")
    last_quarter = current_quarter - 1
    return str(last_quarter)


def calculate_performance_summary(df: pd.DataFrame) -> dict:
    last_quarter = get_last_quarter_label()

    if "quarter" not in df.columns:
        return {
            "error": "No date or quarter column found. The assistant needs a date column to answer last-quarter questions."
        }

    qdf = df[df["quarter"] == last_quarter].copy()

    if qdf.empty:
        return {
            "error": f"No survey records found for last quarter: {last_quarter}."
        }

    metrics = {}

    possible_metrics = {
        "show_rating": "How many stars would you give the show?",
        "like_show": "How much did you like the show?",
        "recommendation_score": "How likely are you to recommend a Monkey Baa show to other parents, carers or teachers? ",
        "young_people_attended": "How many young people did you attend with?",
        "young_people_attended_today": "How many young people did you attend with today?",
    }

    for metric_name, col in possible_metrics.items():
        if col in qdf.columns:
            values = pd.to_numeric(qdf[col], errors="coerce").dropna()
            if not values.empty:
                metrics[metric_name] = {
                    "average": round(values.mean(), 2),
                    "count": int(values.count()),
                    "max": float(values.max()),
                    "min": float(values.min()),
                }

    show_breakdown = {}
    if "What show did you see?" in qdf.columns:
        show_breakdown = (
            qdf["What show did you see?"]
            .dropna()
            .value_counts()
            .head(10)
            .to_dict()
        )

    return {
        "quarter": last_quarter,
        "total_survey_responses": int(len(qdf)),
        "metrics": metrics,
        "top_shows": show_breakdown,
    }


def generate_business_performance_answer(summary: dict, user_question: str) -> str:
    if "error" in summary:
        return summary["error"]

    client = get_openai_client()

    if client is None:
        return (
            "OpenAI API key not found. Based on the available data, "
            f"there were {summary['total_survey_responses']} survey responses in {summary['quarter']}. "
            f"Performance metrics found: {summary['metrics']}."
        )

    prompt = f"""
You are an AI impact analyst for Monkey Baa Theatre Company.

The user asked:
{user_question}

Use the structured data below to answer clearly and professionally.

Data summary:
{summary}

Write the response in this structure:
1. Overall performance summary
2. Key evidence from the data
3. What this means for the organisation
4. Recommendation

Do not invent data. If something is missing, say it clearly.
"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
    )

    return response.output_text


def answer_business_performance_question(user_question: str, file_paths: list[str]) -> str:
    df = load_survey_data(file_paths)
    df = prepare_dates(df)
    summary = calculate_performance_summary(df)
    return generate_business_performance_answer(summary, user_question)