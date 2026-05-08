import streamlit as st
import pandas as pd
import re
import plotly.graph_objects as go
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from lib.data_store import list_datasets, load_dataset
from lib.ai_config import get_openai_client

try:
    from openai import OpenAI
except Exception:
    OpenAI = None



# -------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------
st.set_page_config(
    page_title="Monkey Baa - Impact Framework Analysis",
    page_icon="🎯",
    layout="wide"
)
from lib.style import inject_css, render_sidebar_nav, require_login

inject_css()
render_sidebar_nav()
require_login()

# -------------------------------------------------
# LOGIN PROTECTION
# -------------------------------------------------
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("Please login first from the Home page.")
    st.stop()


# -------------------------------------------------
# OPENAI API KEY
# -------------------------------------------------
OPENAI_API_KEY, api_key_error = get_openai_client()


# -------------------------------------------------
# CSS
# -------------------------------------------------
st.markdown("""
<style>
:root {
    --card-bg: rgba(255,255,255,0.94);
    --text-main: #1f2937;
    --text-soft: #4b5563;
    --accent: #b83280;
    --accent-red: #FF4B4B;
    --blue-soft: #e3f2fd;
    --blue-border: #2196f3;
    --border: #f3d1e3;
}
@media (prefers-color-scheme: dark) {
    :root {
        --card-bg: rgba(31,41,55,0.94);
        --text-main: #f9fafb;
        --text-soft: #d1d5db;
        --accent: #f9a8d4;
        --accent-red: #ff7b7b;
        --blue-soft: rgba(33,150,243,0.18);
        --blue-border: #90caf9;
        --border: rgba(249,168,212,0.35);
    }
}
.hero-card {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 26px;
    padding: 28px;
    margin-bottom: 24px;
    box-shadow: 0 10px 28px rgba(0,0,0,0.08);
}
.hero-title {
    color: var(--text-main);
    font-size: 36px;
    font-weight: 800;
}
.hero-text {
    color: var(--text-soft);
    font-size: 17px;
    line-height: 1.6;
}
.okr-card {
    background: var(--card-bg);
    border-radius: 18px;
    padding: 24px;
    border-left: 10px solid var(--accent-red);
    box-shadow: 2px 2px 12px rgba(0,0,0,0.10);
    margin-bottom: 22px;
}
.okr-card h2 {
    color: var(--text-main);
}
.okr-card p {
    color: var(--text-soft);
}
.ai-insight {
    background-color: var(--blue-soft);
    border-radius: 14px;
    padding: 16px;
    border-left: 6px solid var(--blue-border);
    color: var(--text-main);
    margin-top: 10px;
}
</style>
""", unsafe_allow_html=True)


# -------------------------------------------------
# HEADER
# -------------------------------------------------
st.markdown("""
<div class="hero-card">
    <div class="hero-title">🎯 Monkey Baa Impact Framework Analysis</div>
    <div class="hero-text">
        Select saved files from the Data Library to analyse OKRs, KPIs, Theory of Change outcomes,
        generate AI insights, and download one complete impact report with results and graphics.
    </div>
</div>
""", unsafe_allow_html=True)


# -------------------------------------------------
# FUNCTIONS
# -------------------------------------------------
def clean_text(text):
    if pd.isna(text):
        return ""

    return (
        " ".join(
            str(text)
            .replace("â€™", "'")
            .replace("’", "'")
            .split()
        )
        .strip()
    )


def find_column(name, column_list):
    n = clean_text(name)

    if n in column_list:
        return n

    for c in column_list:
        c_text = clean_text(c)
        if n.lower() in c_text.lower() or c_text.lower() in n.lower():
            return c

    return None


def total_countifs(fragment, df):
    matches = re.findall(r'Survey\[(.*?)\]\s*,\s*"(.*?)"', str(fragment))
    points = 0

    for col_name, criteria in matches:
        target = find_column(col_name, df.columns)

        if target:
            if criteria == "<>":
                points += df[target].notnull().sum()
            else:
                crit = clean_text(criteria).lower()
                points += (
                    df[target]
                    .astype(str)
                    .apply(clean_text)
                    .str.lower()
                    == crit
                ).sum()

    return points


def calculate_kpi(formula, data):
    try:
        f = clean_text(formula).replace("=", "")

        if "AVERAGE" in f.upper():
            m = re.search(r'AVERAGE\(Survey\[(.*?)\]\)', f, re.IGNORECASE)

            if m:
                col = find_column(m.group(1), data.columns)

                if col:
                    return pd.to_numeric(data[col], errors="coerce").mean()

            return 0

        if "/" in f:
            parts = f.rsplit("/", 1)
            numerator = total_countifs(parts[0], data)

            multiplier = 1
            m_mult = re.search(r'(\d+)\s*\*|/\s*(\d+)', f)

            if m_mult:
                multiplier = int(m_mult.group(1) or m_mult.group(2))

            valid_rows = len(data.dropna(how="all"))
            denominator = valid_rows * multiplier

            return (numerator / denominator * 100) if denominator > 0 else 0

        return total_countifs(f, data)

    except Exception:
        return 0


def fix_expected_value(value):
    n = pd.to_numeric(value, errors="coerce")

    if pd.isna(n):
        return 0

    if 0 < n <= 1:
        return n * 100

    return n




# -------------------------------------------------
# FLEXIBLE FRAMEWORK READER FUNCTIONS
# -------------------------------------------------
def normalise_key(value):
    return re.sub(r"[^a-z0-9]", "", clean_text(value).lower())


def detect_framework_columns(df):
    """Detect framework meaning even when Excel headers are different."""
    aliases = {
        "objective": [
            "objective", "goal", "outcome", "theoryofchangeoutcome",
            "tocoutcome", "impactoutcome", "strategicoutcome"
        ],
        "key_result": [
            "keyresult", "kr", "kpi", "indicator", "measure",
            "metric", "successmeasure", "performanceindicator"
        ],
        "formula": [
            "formula", "excelformula", "exampleexcelformula",
            "calculationlogic", "calculation", "logic", "method", "measurementmethod"
        ],
        "expected": [
            "expected", "target", "suggestedtarget", "benchmark",
            "goalvalue", "expectedtarget", "threshold"
        ],
        "outcome_area": [
            "outcomearea", "area", "impactarea", "dimension",
            "theoryofchangedimension", "domain"
        ],
        "theme": ["theme", "stream", "pillar"],
        "survey_columns": [
            "surveycolumnsused", "surveycolumns", "surveyfields",
            "questions", "surveyquestionsfields", "datafields"
        ],
    }

    normalised_cols = {normalise_key(c): c for c in df.columns}
    detected = {}

    for role, names in aliases.items():
        detected[role] = None
        for name in names:
            if name in normalised_cols:
                detected[role] = normalised_cols[name]
                break

    # Fallback: use the first text-heavy column as objective if missing
    if not detected["objective"]:
        text_cols = [c for c in df.columns if df[c].astype(str).str.len().mean() > 20]
        if text_cols:
            detected["objective"] = text_cols[0]

    # Fallback: use a second text-heavy column as key result/KPI if missing
    if not detected["key_result"]:
        text_cols = [c for c in df.columns if c != detected["objective"] and df[c].astype(str).str.len().mean() > 15]
        if text_cols:
            detected["key_result"] = text_cols[0]

    return detected


def extract_number(value):
    """Convert 70%, 0.7, 'Target 70%' or 4.5/5 into a comparable number."""
    text = clean_text(value)
    if not text:
        return 0

    rating = re.search(r"(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)", text)
    if rating:
        top = float(rating.group(1))
        bottom = float(rating.group(2))
        return (top / bottom * 100) if bottom else 0

    pct = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
    if pct:
        return float(pct.group(1))

    n = pd.to_numeric(value, errors="coerce")
    if pd.isna(n):
        found = re.findall(r"\d+(?:\.\d+)?", text)
        return float(found[0]) if found else 0

    return float(n * 100) if 0 < float(n) <= 1 else float(n)


def split_candidate_columns(value):
    text = clean_text(value)
    if not text:
        return []
    parts = re.split(r",|;|\||\n| and | / ", text, flags=re.IGNORECASE)
    return [clean_text(p) for p in parts if clean_text(p)]


def fuzzy_find_column(name, data_columns):
    """Find a survey/data column even when wording is not exactly the same."""
    if not name:
        return None

    target_key = normalise_key(name)
    col_keys = {c: normalise_key(c) for c in data_columns}

    for c, key in col_keys.items():
        if target_key == key:
            return c

    for c, key in col_keys.items():
        if target_key in key or key in target_key:
            return c

    # token overlap fallback
    target_words = set(re.findall(r"[a-z0-9]+", clean_text(name).lower()))
    best_col, best_score = None, 0
    for c in data_columns:
        words = set(re.findall(r"[a-z0-9]+", clean_text(c).lower()))
        if not words:
            continue
        score = len(target_words & words) / max(len(target_words), 1)
        if score > best_score:
            best_col, best_score = c, score

    return best_col if best_score >= 0.45 else None


def score_series(series, hint_text=""):
    """Turn a survey column into a 0-100 result using common survey patterns."""
    s = series.dropna()
    if s.empty:
        return None

    numeric = pd.to_numeric(s, errors="coerce")
    if numeric.notna().mean() >= 0.60:
        mean_value = numeric.mean()
        max_value = numeric.max()
        if max_value <= 5:
            return mean_value / 5 * 100
        if max_value <= 10:
            return mean_value / 10 * 100
        if max_value <= 100:
            return mean_value
        return mean_value

    text = s.astype(str).apply(clean_text).str.lower()
    hint = clean_text(hint_text).lower()

    positive_words = [
        "yes", "true", "agree", "strongly agree", "happy", "excited", "proud",
        "good", "brave", "included", "confident", "creative", "inspired",
        "first", "enjoy", "excellent", "very good", "positive"
    ]
    negative_words = ["no", "false", "disagree", "not", "none", "poor", "bad", "negative"]

    # If the KPI asks for first-time attendance, count first/yes responses as positive.
    if "first" in hint:
        mask = text.str.contains("yes|first|first-time|first time", regex=True, na=False)
        return mask.mean() * 100

    positive_mask = text.apply(lambda x: any(w in x for w in positive_words) and not any(w == x for w in negative_words))
    return positive_mask.mean() * 100


def unique_clean_columns(columns):
    """Clean column names and keep duplicates usable by adding .2, .3 etc."""
    seen = {}
    cleaned = []
    for c in columns:
        base = clean_text(c)
        if base not in seen:
            seen[base] = 1
            cleaned.append(base)
        else:
            seen[base] += 1
            cleaned.append(f"{base}.{seen[base]}")
    return cleaned


def column_matches_any(column_name, terms):
    text = clean_text(column_name).lower()
    return any(term.lower() in text for term in terms)


def get_matching_columns(data, include_terms, exclude_terms=None):
    """Return all survey columns whose names contain any include term and no exclude term."""
    exclude_terms = exclude_terms or []
    cols = []
    for c in data.columns:
        c_lower = clean_text(c).lower()
        if any(t.lower() in c_lower for t in include_terms) and not any(x.lower() in c_lower for x in exclude_terms):
            cols.append(c)
    return cols


def percentage_any_response(data, columns, positive_contains=None):
    """
    Percentage of rows where at least one of the selected columns has a meaningful response.
    This works well for checkbox-style survey exports where selected answers are stored as text.
    """
    if not columns:
        return None

    valid_data = data.dropna(how="all")
    if valid_data.empty:
        return 0

    selected = valid_data[columns].fillna("").astype(str).map(clean_text)

    if positive_contains:
        pattern = "|".join([re.escape(x) for x in positive_contains])
        bool_df = selected.apply(lambda col: col.str.contains(pattern, case=False, regex=True, na=False))
    else:
        bool_df = selected.apply(lambda col: col.str.strip().ne(""))

    return bool_df.any(axis=1).mean() * 100


def percentage_text_match(data, columns, match_terms):
    if not columns:
        return None

    valid_data = data.dropna(how="all")
    selected = valid_data[columns].fillna("").astype(str).map(clean_text)
    pattern = "|".join([re.escape(x) for x in match_terms])
    bool_df = selected.apply(lambda col: col.str.contains(pattern, case=False, regex=True, na=False))
    return bool_df.any(axis=1).mean() * 100


def average_numeric_score(data, columns, scale=10):
    if not columns:
        return None

    values = []
    for col in columns:
        numeric = pd.to_numeric(data[col], errors="coerce")
        values.append(numeric)

    combined = pd.concat(values, axis=0).dropna()
    if combined.empty:
        return None

    return combined.mean() / scale * 100


def calculate_from_kpi_keywords(row, data, detected):
    """
    Backup calculator for flexible KPI / Theory of Change frameworks when Formula is blank.
    It reads the KPI wording and maps it to common Monkey Baa survey fields.
    """
    key_col = detected.get("key_result")
    objective_col = detected.get("objective")

    kpi_text = clean_text(row.get(key_col, "")) if key_col else ""
    objective_text = clean_text(row.get(objective_col, "")) if objective_col else ""
    hint = f"{kpi_text} {objective_text}".lower()

    matched_cols = []
    result = None

    # 1. Positive emotional responses: Happy, Excited, Proud, Curious, Good inside, Surprised.
    if any(w in hint for w in ["positive emotional", "joy", "wonder", "inspiration", "happy", "positive after"]):
        matched_cols = get_matching_columns(
            data,
            ["happy", "excited", "proud", "curious", "good inside", "surprised"],
            ["sad", "bored", "angry", "confused", "scared"]
        )
        result = percentage_any_response(data, matched_cols)

    # 2. Identification / representation / validation.
    elif any(w in hint for w in ["identify with characters", "feel represented", "see themselves", "validated", "similar to a character"]):
        matched_cols = get_matching_columns(
            data,
            ["similar to a character", "feel a bit like you", "recognised something", "own life"]
        )
        result = percentage_any_response(data, matched_cols, ["yes", "similar", "recognised", "own life"])

    # 3. First-time theatre attendance.
    elif any(w in hint for w in ["first-time", "first time", "first live theatre"]):
        matched_cols = get_matching_columns(data, ["first live theatre"])
        result = percentage_text_match(data, matched_cols, ["yes"])

    # 4. Empathy / emotional connection / understanding.
    elif any(w in hint for w in ["empathy", "emotional connection", "understanding", "connection"]):
        matched_cols = get_matching_columns(
            data,
            ["connected to others", "talked positively", "recognised something", "culture", "perspective"]
        )
        result = percentage_any_response(data, matched_cols)

    # 5. Confidence / bravery / self-esteem.
    elif any(w in hint for w in ["confidence", "bravery", "self-esteem", "brave"]):
        matched_cols = get_matching_columns(data, ["brave", "spoke up", "positively"])
        result = percentage_any_response(data, matched_cols)

    # 6. Equity / diverse communities / regional / CALD / First Nations / low SES.
    elif any(w in hint for w in ["regional", "cald", "first nations", "low ses", "diverse communities", "equity"]):
        matched_cols = get_matching_columns(
            data,
            [
                "regional or remote", "culturally or linguistically", "aboriginal",
                "torres strait", "financial situation", "language other than english",
                "refugee", "disability", "neurodivergent", "out-of-home"
            ]
        )
        result = percentage_text_match(
            data,
            matched_cols,
            [
                "lives in a regional", "culturally", "aboriginal", "torres",
                "finding it hard", "language other than english", "yes",
                "refugee", "disability", "neurodivergent", "out-of-home"
            ]
        )

    # 7. Creative activities / curiosity / engagement.
    elif any(w in hint for w in ["creative activities", "creative theatre", "curiosity", "engagement", "interest in creative"]):
        matched_cols = get_matching_columns(
            data,
            [
                "draw", "make a story", "sing", "perform", "learn something",
                "think about the story", "act", "make some art", "share ideas",
                "ask questions", "try something new", "watched closely", "reacted"
            ]
        )
        result = percentage_any_response(data, matched_cols)

    # 8. Audience satisfaction / rating out of 10.
    elif any(w in hint for w in ["satisfaction", "rating", "8 out of 10", "liked the show", "stars"]):
        matched_cols = get_matching_columns(data, ["how much did you like", "stars would you give", "recommend"])
        result = average_numeric_score(data, matched_cols, scale=10)

    # 9. Learning something new / cultural literacy / openness.
    elif any(w in hint for w in ["learning something new", "learn something new", "cultural literacy", "openness"]):
        matched_cols = get_matching_columns(
            data,
            ["did you learn something new", "learn something new", "culture", "perspective"]
        )
        result = percentage_text_match(data, matched_cols, ["yes", "learn something new", "culture", "perspective"])

    # 10. Repeat attendance / future attendance.
    elif any(w in hint for w in ["repeat", "return", "future monkey baa", "lifelong arts"]):
        matched_cols = get_matching_columns(data, ["attended a monkey baa show before", "recommend"])
        # Previous attendance = Yes OR high recommendation score as a proxy for likely future engagement.
        prev = percentage_text_match(data, get_matching_columns(data, ["attended a monkey baa show before"]), ["yes"])
        rec_cols = get_matching_columns(data, ["recommend"])
        rec = None
        if rec_cols:
            rec_numeric = pd.to_numeric(data[rec_cols[0]], errors="coerce")
            if rec_numeric.notna().any():
                rec = (rec_numeric >= 8).mean() * 100
        vals = [v for v in [prev, rec] if v is not None]
        result = sum(vals) / len(vals) if vals else None
        matched_cols = list(dict.fromkeys(matched_cols + rec_cols))

    # 11. Australian storytelling diversified / schools / community participation.
    elif any(w in hint for w in ["storytelling", "diversified", "communities and schools", "participation from diverse"]):
        matched_cols = get_matching_columns(
            data,
            ["relationship with the young person", "culturally", "aboriginal", "regional", "language other than english"]
        )
        result = percentage_any_response(data, matched_cols)

    if result is None:
        return None, []

    return max(0, min(float(result), 100)), matched_cols


def infer_kpi_from_row(row, data, detected, return_details=False):
    """Calculate Actual even if formula is blank by using formula, optional mapping columns, or KPI wording."""
    formula_col = detected.get("formula")
    survey_cols_col = detected.get("survey_columns")
    key_col = detected.get("key_result")
    objective_col = detected.get("objective")

    formula = row.get(formula_col, "") if formula_col else ""

    # 1. Use original OKR structured formulas when available.
    if clean_text(formula) and clean_text(formula).lower() not in ["nan", "none"]:
        calculated = calculate_kpi(formula, data)
        if calculated != 0:
            if return_details:
                return calculated, "Formula", []
            return calculated

    candidate_names = []
    if survey_cols_col:
        candidate_names += split_candidate_columns(row.get(survey_cols_col, ""))

    hint_text = " ".join([
        str(row.get(key_col, "")) if key_col else "",
        str(row.get(objective_col, "")) if objective_col else "",
        str(formula)
    ])

    # 2. Use optional Survey Columns Used column if present.
    scores = []
    used_cols = []
    for name in candidate_names:
        col = fuzzy_find_column(name, data.columns)
        if col and col not in used_cols:
            result = score_series(data[col], hint_text)
            if result is not None:
                scores.append(result)
                used_cols.append(col)

    if scores:
        final_score = sum(scores) / len(scores)
        if return_details:
            return final_score, "Survey Columns Used", used_cols
        return final_score

    # 3. Use keyword mapping for KPI / Theory of Change frameworks with blank formulas.
    keyword_result, matched_cols = calculate_from_kpi_keywords(row, data, detected)
    if keyword_result is not None:
        if return_details:
            return keyword_result, "Keyword mapping", matched_cols
        return keyword_result

    # 4. Last fallback: try fuzzy matching from KPI/objective wording.
    fallback_names = re.findall(r"[A-Za-z][A-Za-z ]{3,}", hint_text)
    for name in fallback_names:
        col = fuzzy_find_column(name, data.columns)
        if col and col not in used_cols:
            result = score_series(data[col], hint_text)
            if result is not None:
                scores.append(result)
                used_cols.append(col)

    if scores:
        final_score = sum(scores) / len(scores)
        if return_details:
            return final_score, "Fuzzy text match", used_cols
        return final_score

    if return_details:
        return 0, "No matching formula or survey column found", []
    return 0


def prepare_flexible_framework(df_framework):
    df = df_framework.dropna(how="all").copy()
    df.columns = [clean_text(c) for c in df.columns]
    detected = detect_framework_columns(df)

    missing = []
    if not detected.get("objective"):
        missing.append("Objective / Outcome")
    if not detected.get("key_result"):
        missing.append("Key Result / KPI / Indicator")
    if not detected.get("expected"):
        missing.append("Expected / Target / Suggested Target")

    return df, detected, missing



def get_framework_labels(active_framework_type):
    """Return dynamic wording for normal OKR files or Theory of Change / KPI frameworks."""
    framework_text = clean_text(active_framework_type).lower()

    if "flexible" in framework_text or "theory" in framework_text or "impact" in framework_text:
        return {
            "page_title": "Theory of Change KPI Analysis",
            "page_label": "Theory of Change KPI",
            "objective_label": "Outcome",
            "objective_plural": "Outcomes",
            "key_result_label": "KPI / Indicator",
            "key_result_plural": "KPIs / Indicators",
            "group_label": "Outcome Area",
            "benchmark_title": "Actual vs Target KPI Benchmarking",
            "report_title": "Monkey Baa Theory of Change KPI AI Analysis Report",
            "download_name": "monkey_baa_theory_of_change_kpi_report.pdf",
            "button_label": "Run Theory of Change KPI Analysis",
            "spinner": "Calculating Theory of Change KPI metrics and generating AI insights...",
            "summary_objective": "Overall Theory of Change KPI performance",
        }

    return {
        "page_title": "OKR Analysis",
        "page_label": "OKR",
        "objective_label": "Objective",
        "objective_plural": "Objectives",
        "key_result_label": "Key Result",
        "key_result_plural": "Key Results",
        "group_label": "Outcome Area",
        "benchmark_title": "Actual vs Target OKR Benchmarking",
        "report_title": "Monkey Baa OKR AI Analysis Report",
        "download_name": "monkey_baa_ai_okr_report.pdf",
        "button_label": "Run OKR Analysis",
        "spinner": "Calculating OKR impact metrics and generating AI insights...",
        "summary_objective": "Overall OKR performance",
    }

def generate_ai_okr_analysis(objective, actual, target, variance, framework_type="OKR Framework"):
    if not OPENAI_API_KEY:
        return (
            "AI insight could not be generated because the OpenAI API key was not found. "
            "Add OPENAI_API_KEY to your .env file or deployment environment variables."
        )

    if OpenAI is None:
        return (
            "AI insight could not be generated because the OpenAI package is not installed. "
            "Run: python -m pip install openai"
        )

    labels = get_framework_labels(framework_type)
    framework_name = labels["page_label"]
    objective_label = labels["objective_label"]
    key_result_label = labels["key_result_label"]

    try:
        client = OpenAI(api_key=OPENAI_API_KEY)

        response = client.responses.create(
            model="gpt-4.1-mini",
            input=f"""
            You are an AI social impact analyst for Monkey Baa Theatre Company.

            Analyse this {framework_name} result and provide a practical recommendation.

            {objective_label}:
            {objective}

            Actual result:
            {actual:.1f}%

            Target:
            {target:.1f}%

            Variance:
            {variance:.1f}%

            Write the response in this exact structure:

            1. Insight:
            Explain what the result means in relation to Monkey Baa's Theory of Change and impact goals.

            2. Likely reason:
            Explain the possible reason why the result is above or below target.

            3. Suggested solution:
            Give a practical recommendation to improve or maintain the result.

            4. Next action:
            Give one clear action Monkey Baa staff could take next.

            Keep the full response under 160 words.
            Use professional but simple language.
            Use the wording "{objective_label}" and "{key_result_label}" where relevant.
            """
        )

        return response.output_text

    except Exception as e:
        return f"AI insight could not be generated. Details: {e}"


def safe_load_saved_dataset(item):
    try:
        df = load_dataset(item["filename"])

        if df.empty:
            return None, "This saved dataset is empty."

        return df, None

    except Exception as e:
        return None, f"Could not read saved dataset: {e}"


def create_pdf_report(
    results_df,
    col_objective,
    col_key_result,
    col_outcome_area,
    selected_survey_name,
    ai_summary,
    objective_ai_map,
    framework_type="OKR Framework"
):
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=32,
        leftMargin=32,
        topMargin=32,
        bottomMargin=32
    )

    styles = getSampleStyleSheet()

    title_style = styles["Title"]
    heading_style = styles["Heading2"]
    body_style = styles["BodyText"]

    small_style = ParagraphStyle(
        "SmallText",
        parent=styles["BodyText"],
        fontSize=8,
        leading=10
    )

    ai_style = ParagraphStyle(
        "AIStyle",
        parent=styles["BodyText"],
        fontSize=9,
        leading=12,
        backColor=colors.HexColor("#E3F2FD"),
        borderColor=colors.HexColor("#2196F3"),
        borderWidth=1,
        borderPadding=6,
        spaceAfter=10
    )

    labels = get_framework_labels(framework_type)
    page_label = labels["page_label"]
    objective_label = labels["objective_label"]
    objective_plural = labels["objective_plural"]
    key_result_label = labels["key_result_label"]
    key_result_plural = labels["key_result_plural"]
    report_title = labels["report_title"]

    story = []

    story.append(Paragraph(report_title, title_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph(
        f"<b>Survey/Data file used:</b> {selected_survey_name}",
        body_style
    ))

    story.append(Spacer(1, 8))

    story.append(Paragraph(
        "This report summarises Monkey Baa's impact framework performance using the selected survey/data file. "
        "It includes KPI results, AI-generated insights, suggested solutions, and practical next actions "
        "to support Theory of Change reporting and social impact decision-making.",
        body_style
    ))

    story.append(Spacer(1, 16))

    avg_actual = results_df["Actual"].mean()
    avg_target = results_df["Expected_Num"].mean()
    avg_variance = avg_actual - avg_target

    summary_table_data = [
        ["Metric", "Value"],
        [f"Total {objective_plural}", str(results_df[col_objective].nunique())],
        [f"Total {key_result_plural}", str(results_df[col_key_result].nunique())],
        ["Average Actual", f"{avg_actual:.1f}%"],
        ["Average Target", f"{avg_target:.1f}%"],
        ["Average Variance", f"{avg_variance:.1f}%"]
    ]

    summary_table = Table(summary_table_data, colWidths=[170, 250])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#B83280")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))

    story.append(Paragraph("Executive Summary", heading_style))
    story.append(summary_table)
    story.append(Spacer(1, 12))

    story.append(Paragraph("<b>AI Summary:</b>", body_style))
    story.append(Paragraph(ai_summary.replace("\n", "<br/>"), ai_style))
    story.append(Spacer(1, 12))

    story.append(Paragraph(f"{page_label} Benchmarking Table", heading_style))

    table_data = [[objective_label, key_result_label, "Actual", "Target", "Variance"]]

    for _, row in results_df.iterrows():
        actual = row.get("Actual", 0)
        target = row.get("Expected_Num", 0)
        variance = actual - target

        table_data.append([
            Paragraph(str(row.get(col_objective, ""))[:70], small_style),
            Paragraph(str(row.get(col_key_result, ""))[:80], small_style),
            f"{actual:.1f}%",
            f"{target:.1f}%",
            f"{variance:.1f}%"
        ])

    table = Table(
        table_data,
        repeatRows=1,
        colWidths=[115, 155, 55, 55, 60]
    )

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#B83280")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))

    story.append(table)
    story.append(PageBreak())

    story.append(Paragraph(f"{objective_label}-Level AI Insights and Suggestions", heading_style))
    story.append(Spacer(1, 8))

    if col_outcome_area and col_outcome_area in results_df.columns:
        group_fields = [col_outcome_area, col_objective]
    else:
        group_fields = [col_objective]

    grouped = results_df.groupby(group_fields, dropna=False)

    for group_key, df_obj in grouped:
        if isinstance(group_key, tuple):
            area = group_key[0]
            objective = group_key[1]
        else:
            area = "All Outcome Areas"
            objective = group_key

        obj_actual = df_obj["Actual"].mean()
        obj_target = df_obj["Expected_Num"].mean()
        obj_variance = obj_actual - obj_target

        story.append(Paragraph(f"Outcome Area: {area}", styles["Heading3"]))
        story.append(Paragraph(f"{objective_label}: {objective}", styles["Heading3"]))

        mini_table_data = [
            ["Actual", "Target", "Variance", key_result_plural],
            [f"{obj_actual:.1f}%", f"{obj_target:.1f}%", f"{obj_variance:.1f}%", str(len(df_obj))]
        ]

        mini_table = Table(mini_table_data, colWidths=[90, 90, 90, 110])
        mini_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FF4B4B")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]))

        story.append(mini_table)
        story.append(Spacer(1, 8))

        ai_text = objective_ai_map.get(str(objective), "AI insight not available.")
        story.append(Paragraph("<b>AI insight and recommendation:</b>", body_style))
        story.append(Paragraph(ai_text.replace("\n", "<br/>"), ai_style))

        kr_table_data = [[key_result_label, "Actual", "Target", "Status"]]

        for _, row in df_obj.iterrows():
            actual = row.get("Actual", 0)
            target = row.get("Expected_Num", 0)
            status = "On / above target" if actual >= target else "Below target"

            kr_table_data.append([
                Paragraph(str(row.get(col_key_result, ""))[:90], small_style),
                f"{actual:.1f}%",
                f"{target:.1f}%",
                status
            ])

        kr_table = Table(kr_table_data, repeatRows=1, colWidths=[230, 60, 60, 100])
        kr_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#B83280")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))

        story.append(kr_table)
        story.append(Spacer(1, 16))

    story.append(Spacer(1, 12))

    story.append(Paragraph(
        "Note: This report includes AI-generated interpretation and suggested actions. "
        "Final decisions should be validated by Monkey Baa staff and stakeholders.",
        body_style
    ))

    doc.build(story)
    buffer.seek(0)

    return buffer


# -------------------------------------------------
# LOAD DATASETS FROM DATA LIBRARY
# -------------------------------------------------
datasets = list_datasets()

if not datasets:
    st.warning("No saved datasets found. Please upload and save files in the Data Library first.")
    st.stop()


st.subheader("📚 Select Files from Data Library")

framework_options = [
    item for item in datasets
    if item.get("dataset_type") in ["Framework Dictionary", "Other"]
]

survey_options = [
    item for item in datasets
    if item.get("dataset_type") in [
        "Survey Data",
        "Audience Data",
        "Dashboard Data",
        "Performance Information",
        "Other"
    ]
]

if not framework_options:
    st.error("No Framework Dictionary found. Upload it in Data Library and select dataset type: Framework Dictionary.")
    st.stop()

if not survey_options:
    st.error("No survey/data file found. Upload survey data in Data Library and select dataset type: Survey Data.")
    st.stop()


col_a, col_b = st.columns(2)

with col_a:
    selected_framework_name = st.selectbox(
        "Select Framework Dictionary",
        [item["dataset_name"] for item in framework_options]
    )

with col_b:
    selected_survey_name = st.selectbox(
        "Select Survey / Data File",
        [item["dataset_name"] for item in survey_options]
    )


framework_item = next(
    item for item in framework_options
    if item["dataset_name"] == selected_framework_name
)

survey_item = next(
    item for item in survey_options
    if item["dataset_name"] == selected_survey_name
)


df_framework, framework_error = safe_load_saved_dataset(framework_item)
df_survey, survey_error = safe_load_saved_dataset(survey_item)

if framework_error:
    st.error(framework_error)
    st.stop()

if survey_error:
    st.error(survey_error)
    st.stop()


df_survey = df_survey.dropna(how="all")
df_survey.columns = unique_clean_columns(df_survey.columns)

st.success("Files loaded successfully from Data Library.")

# -------------------------------------------------
# FRAMEWORK READING MODE
# -------------------------------------------------
framework_mode = st.selectbox(
    "Framework reading mode",
    [
        "Auto detect (recommended)",
        "Strict OKR only",
        "Flexible KPI / Theory of Change / Impact Framework"
    ],
    help=(
        "Use Auto detect to read your normal OKR file first, then fall back to flexible KPI/Theory of Change detection. "
        "Use Strict OKR only when you want the original OKR structure to be enforced."
    )
)

if OPENAI_API_KEY:
    st.caption("AI connection active: API key loaded.")
else:
    st.error(api_key_error)


# -------------------------------------------------
# FRAMEWORK COLUMN DETECTION
# -------------------------------------------------
df_framework = df_framework.dropna(how="all").copy()
df_framework.columns = [clean_text(c) for c in df_framework.columns]

# First try the original OKR structure exactly. This keeps your existing OKR file working properly.
framework_cols = {str(col).lower().replace(" ", "").replace("_", "").replace("-", ""): col for col in df_framework.columns}
okr_detected = {
    "objective": framework_cols.get("objective"),
    "key_result": framework_cols.get("keyresult"),
    "formula": framework_cols.get("formula"),
    "expected": framework_cols.get("expected"),
    "outcome_area": framework_cols.get("outcomearea"),
    "survey_columns": framework_cols.get("surveycolumnsused"),
}

okr_required_ok = all([
    okr_detected.get("objective"),
    okr_detected.get("key_result"),
    okr_detected.get("formula"),
    okr_detected.get("expected"),
])

if framework_mode == "Strict OKR only":
    detected_cols = okr_detected
    missing_cols = []
    if not okr_detected.get("objective"):
        missing_cols.append("Objective")
    if not okr_detected.get("key_result"):
        missing_cols.append("Key Result")
    if not okr_detected.get("formula"):
        missing_cols.append("Formula")
    if not okr_detected.get("expected"):
        missing_cols.append("Expected")
    active_framework_type = "Strict OKR"
elif framework_mode == "Flexible KPI / Theory of Change / Impact Framework":
    df_framework, detected_cols, missing_cols = prepare_flexible_framework(df_framework)
    active_framework_type = "Flexible Framework"
else:
    if okr_required_ok:
        detected_cols = okr_detected
        missing_cols = []
        active_framework_type = "OKR Framework"
    else:
        df_framework, detected_cols, missing_cols = prepare_flexible_framework(df_framework)
        active_framework_type = "Auto-detected Flexible Framework"

col_objective = detected_cols.get("objective")
col_key_result = detected_cols.get("key_result")
col_formula = detected_cols.get("formula")
col_expected = detected_cols.get("expected")
col_outcome_area = detected_cols.get("outcome_area")
col_survey_columns = detected_cols.get("survey_columns")

if missing_cols:
    st.error(
        "The framework file could not be analysed because these required columns were not found: "
        + ", ".join(missing_cols)
        + ". For OKR files use Objective, Key Result, Formula and Expected. "
        + "For KPI/Theory of Change files use equivalent columns such as Outcome, KPI/Indicator, Target and Calculation Logic or Survey Columns Used."
    )
    st.stop()

st.info(f"Detected framework type: **{active_framework_type}**")

with st.expander("Detected framework structure"):
    st.write({
        "Framework Type": active_framework_type,
        "Objective / Outcome": col_objective,
        "Key Result / KPI / Indicator": col_key_result,
        "Formula / Calculation Logic": col_formula,
        "Expected / Target": col_expected,
        "Outcome Area": col_outcome_area,
        "Survey Columns Used": col_survey_columns,
    })

# Dynamic page wording for OKR vs Theory of Change / KPI
labels = get_framework_labels(active_framework_type)
page_label = labels["page_label"]
objective_label = labels["objective_label"]
objective_plural = labels["objective_plural"]
key_result_label = labels["key_result_label"]
key_result_plural = labels["key_result_plural"]
benchmark_title = labels["benchmark_title"]
download_report_name = labels["download_name"]

st.markdown(f"""
<div class="hero-card">
    <div class="hero-title">🎯 Monkey Baa {labels["page_title"]}</div>
    <div class="hero-text">
        This page is currently reading the selected file as a <strong>{page_label}</strong> framework.
        Results are grouped by outcome area or theme where available, calculated against the selected survey/data file,
        and interpreted through AI-supported impact analysis.
    </div>
</div>
""", unsafe_allow_html=True)


# -------------------------------------------------
# RUN ANALYSIS BUTTON
# -------------------------------------------------
if st.button(labels["button_label"]):
    with st.spinner(labels["spinner"]):
        df_results = df_framework.copy()

        analysis_details = df_results.apply(
            lambda row: infer_kpi_from_row(row, df_survey, detected_cols, return_details=True),
            axis=1
        )

        df_results["Actual"] = analysis_details.apply(lambda x: x[0])
        df_results["Calculation_Method"] = analysis_details.apply(lambda x: x[1])
        df_results["Matched_Data_Columns"] = analysis_details.apply(lambda x: ", ".join(x[2]) if x[2] else "")

        df_results["Expected_Num"] = df_results[col_expected].apply(
            extract_number
        )

    st.session_state["okr_results"] = df_results
    st.session_state["okr_columns"] = {
        "objective": col_objective,
        "key_result": col_key_result,
        "outcome_area": col_outcome_area,
        "survey_name": selected_survey_name,
        "framework_type": active_framework_type,
        "labels": labels
    }

    st.success("Framework analysis completed.")


if "okr_results" not in st.session_state:
    st.info("Click **Run Framework Analysis** to generate results.")
    st.stop()


df_results = st.session_state["okr_results"]
col_objective = st.session_state["okr_columns"]["objective"]
col_key_result = st.session_state["okr_columns"]["key_result"]
col_outcome_area = st.session_state["okr_columns"]["outcome_area"]
selected_survey_name = st.session_state["okr_columns"]["survey_name"]
active_framework_type = st.session_state["okr_columns"].get("framework_type", "OKR Framework")
labels = st.session_state["okr_columns"].get("labels", get_framework_labels(active_framework_type))
page_label = labels["page_label"]
objective_label = labels["objective_label"]
objective_plural = labels["objective_plural"]
key_result_label = labels["key_result_label"]
key_result_plural = labels["key_result_plural"]
benchmark_title = labels["benchmark_title"]
download_report_name = labels["download_name"]


# -------------------------------------------------
# SUMMARY
# -------------------------------------------------
st.subheader(f"📊 Overall {page_label} Performance")

st.caption(f"Analysis based on selected survey/data file: **{selected_survey_name}**")

total_objectives = df_results[col_objective].nunique()
total_key_results = df_results[col_key_result].nunique()
avg_actual = df_results["Actual"].mean()
avg_target = df_results["Expected_Num"].mean()
avg_variance = avg_actual - avg_target

m1, m2, m3, m4 = st.columns(4)

m1.metric(objective_plural, total_objectives)
m2.metric(key_result_plural, total_key_results)
m3.metric("Average Actual", f"{avg_actual:.1f}%")
m4.metric("Average Target", f"{avg_target:.1f}%", f"{avg_variance:.1f}%")

overall_ai = generate_ai_okr_analysis(
    labels["summary_objective"],
    avg_actual,
    avg_target,
    avg_variance,
    active_framework_type
)

st.markdown(f"""
<div class="ai-insight">
    <strong>🤖 AI Summary:</strong><br>
    {overall_ai}
</div>
""", unsafe_allow_html=True)


# -------------------------------------------------
# GROUPED OBJECTIVE VIEW
# -------------------------------------------------
if col_outcome_area:
    outcome_areas = df_results[col_outcome_area].dropna().unique()
else:
    outcome_areas = ["All Outcome Areas"]
    df_results["Outcome Area"] = "All Outcome Areas"
    col_outcome_area = "Outcome Area"


chart_counter = 0
objective_ai_map = {}

for area in outcome_areas:
    st.divider()
    st.header(f"📍 {labels['group_label']}: {area}")

    df_area = df_results[df_results[col_outcome_area] == area]

    for objective in df_area[col_objective].dropna().unique():
        df_objective = df_area[df_area[col_objective] == objective]

        objective_actual = df_objective["Actual"].mean()
        objective_target = df_objective["Expected_Num"].mean()
        variance = objective_actual - objective_target

        st.markdown(f"""
        <div class="okr-card">
            <h2 style="margin-top:0;">🎯 {objective_label}: {objective}</h2>
            <p>
                Overall progress is based on
                <strong>{len(df_objective)}</strong> equally weighted {key_result_plural}.
            </p>
        </div>
        """, unsafe_allow_html=True)

        c1, c2, c3 = st.columns([1, 1, 2])

        with c1:
            st.metric("Actual Achievement", f"{objective_actual:.1f}%")

        with c2:
            st.metric("Average Target", f"{objective_target:.1f}%", f"{variance:.1f}%")

        with c3:
            ai_text = generate_ai_okr_analysis(
                objective,
                objective_actual,
                objective_target,
                variance,
                active_framework_type
            )

            objective_ai_map[str(objective)] = ai_text

            st.markdown(f"""
            <div class="ai-insight">
                <strong>🤖 AI Insight, Suggested Solution and Next Action:</strong><br>
                {ai_text}
            </div>
            """, unsafe_allow_html=True)

        with st.expander(f"Show {key_result_plural} and Indicator Breakdown"):
            for row_index, row in df_objective.iterrows():
                kr_name = row[col_key_result]
                actual = row["Actual"]
                expected = row["Expected_Num"]

                p1, p2 = st.columns([1, 2])

                with p1:
                    remaining = max(0, expected - actual)

                    fig = go.Figure(
                        go.Pie(
                            values=[actual, remaining],
                            labels=["Achieved", "Remaining"],
                            hole=0.7,
                            marker_colors=["#FF4B4B", "#EEEEEE"],
                            showlegend=False
                        )
                    )

                    fig.update_layout(
                        margin=dict(t=0, b=0, l=0, r=0),
                        height=180
                    )

                    safe_kr_name = re.sub(r"[^a-zA-Z0-9_]", "_", str(kr_name))
                    chart_counter += 1

                    st.plotly_chart(
                        fig,
                        use_container_width=True,
                        key=f"framework_donut_{safe_kr_name}_{row_index}_{chart_counter}",
                        config={
                            "modeBarButtonsToRemove": ["toImage"],
                            "displaylogo": False
                        }
                    )

                    st.download_button(
                        label="⬇️ Download chart data",
                        data=df_objective.to_csv(index=False).encode("utf-8"),
                        file_name=f"{page_label.lower().replace(' ', '_').replace('/', '_')}_breakdown.csv",
                        mime="text/csv",
                        key=f"download_framework_data_{row_index}_{chart_counter}"
                    )

                with p2:
                    st.write(f"**{kr_name}**")
                    st.caption(f"Score: {actual:.1f}% / Target: {expected:.1f}%")

                    if actual >= expected:
                        st.success(f"This {key_result_label} is meeting or exceeding target.")
                    else:
                        st.warning(f"This {key_result_label} is below target.")


# -------------------------------------------------
# BENCHMARKING
# -------------------------------------------------
st.divider()
st.subheader(f"📊 {benchmark_title}")

benchmark_df = df_results.set_index(col_key_result)[
    ["Actual", "Expected_Num"]
]

st.bar_chart(benchmark_df)

with st.expander("Show calculation matching details"):
    detail_cols = [col_key_result, "Actual", "Expected_Num"]
    if "Calculation_Method" in df_results.columns:
        detail_cols += ["Calculation_Method", "Matched_Data_Columns"]
    st.dataframe(df_results[detail_cols], use_container_width=True)


# -------------------------------------------------
# ONE PDF REPORT DOWNLOAD ONLY
# -------------------------------------------------
st.subheader(f"⬇️ Download AI {page_label} Report")

pdf_buffer = create_pdf_report(
    df_results,
    col_objective,
    col_key_result,
    col_outcome_area,
    selected_survey_name,
    overall_ai,
    objective_ai_map,
    active_framework_type
)

st.download_button(
    label="Download PDF Report",
    data=pdf_buffer,
    file_name=download_report_name,
    mime="application/pdf"
)

from lib.floating_assistant import render_floating_ai_assistant
render_floating_ai_assistant()