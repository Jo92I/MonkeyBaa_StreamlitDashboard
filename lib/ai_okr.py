import os
from openai import OpenAI
import re
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from lib.ssot import load_single_source_of_truth, ssot_summary_text

try:
    from openai import OpenAI
except Exception:
    OpenAI = None


def get_openai_client():
    api_key = None

    try:
        api_key = st.secrets.get("OPENAI_API_KEY")
    except Exception:
        api_key = None

    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        st.error("OpenAI API key not found. Please add OPENAI_API_KEY in Streamlit Secrets.")
        st.stop()

    return OpenAI(api_key=api_key)


def generate_ai_strategic_analysis(prompt):
    client = get_openai_client()

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
    )

    return response.output_text

def clean_text(value):
    if pd.isna(value):
        return ""
    return " ".join(str(value).replace("â€™", "'").replace("’", "'").split()).strip()


def find_column(name, columns):
    name = clean_text(name).lower()

    for col in columns:
        col_clean = clean_text(col).lower()
        if name == col_clean or name in col_clean or col_clean in name:
            return col

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
                    .eq(crit)
                ).sum()

    return points


def calculate_kpi(formula, data):
    try:
        f = clean_text(formula).replace("=", "")

        if "AVERAGE" in f.upper():
            match = re.search(r'AVERAGE\(Survey\[(.*?)\]\)', f, re.IGNORECASE)
            if match:
                col = find_column(match.group(1), data.columns)
                if col:
                    return pd.to_numeric(data[col], errors="coerce").mean()
            return 0

        if "/" in f:
            parts = f.rsplit("/", 1)
            numerator = total_countifs(parts[0], data)
            valid_rows = len(data.dropna(how="all"))
            denominator = valid_rows if valid_rows > 0 else 1
            return numerator / denominator * 100

        return total_countifs(f, data)

    except Exception:
        return 0


def analyse_ssot():
    ssot = load_single_source_of_truth()

    findings = {
        "ssot_summary": ssot_summary_text(ssot),
        "okr_results": [],
        "risks": [],
        "priorities": [],
        "theory_of_change": "",
    }

    if ssot.get("theory_of_change"):
        toc_text = []
        for item in ssot["theory_of_change"]:
            df = item["data"]
            toc_text.append(df.to_string(index=False))
        findings["theory_of_change"] = "\n\n".join(toc_text)

    if not ssot.get("okr_frameworks") or not ssot.get("survey_data"):
        findings["risks"].append(
            "OKR analysis cannot run because either the Framework Dictionary or Survey Data is missing."
        )
        return findings

    framework = ssot["okr_frameworks"][0]["data"]
    survey = ssot["survey_data"][0]["data"]

    framework_cols = {
        str(col).lower().replace(" ", ""): col
        for col in framework.columns
    }

    col_objective = framework_cols.get("objective")
    col_key_result = framework_cols.get("keyresult")
    col_formula = framework_cols.get("formula")
    col_expected = framework_cols.get("expected")
    col_outcome_area = framework_cols.get("outcomearea")

    if not all([col_objective, col_key_result, col_formula, col_expected]):
        findings["risks"].append(
            "Framework Dictionary is missing required columns: Objective, Key Result, Formula, Expected."
        )
        return findings

    results = framework.copy()

    results["Actual"] = results[col_formula].apply(lambda x: calculate_kpi(x, survey))
    results["Target"] = pd.to_numeric(results[col_expected], errors="coerce").fillna(0)
    results["Target"] = results["Target"].apply(lambda x: x * 100 if 0 < x <= 1 else x)
    results["Gap"] = results["Target"] - results["Actual"]
    results["Status"] = results["Gap"].apply(
        lambda x: "Below Target" if x > 0 else "On/Above Target"
    )

    if col_outcome_area:
        group_cols = [col_outcome_area, col_objective]
    else:
        group_cols = [col_objective]

    grouped = (
        results.groupby(group_cols, dropna=False)
        .agg({
            "Actual": "mean",
            "Target": "mean",
            "Gap": "mean",
        })
        .reset_index()
    )

    grouped["Priority Score"] = grouped["Gap"].apply(lambda x: max(x, 0))
    grouped = grouped.sort_values("Priority Score", ascending=False)

    findings["okr_results"] = grouped.to_dict(orient="records")

    risks = grouped[grouped["Gap"] > 0].head(5)

    for _, row in risks.iterrows():
        findings["risks"].append(
            f"{row.to_dict()} is below target with an average gap of {row['Gap']:.1f}%."
        )

    findings["priorities"] = grouped.head(5).to_dict(orient="records")

    return findings


def ask_ai_agent(user_question):
    client, error = get_openai_client()

    if error:
        return f"ERROR: System not connected successfully to OpenAI API. {error}"

    findings = analyse_ssot()

    prompt = f"""
You are the Monkey Baa AI Strategic Assistant.

You must only use the trusted internal Single Source of Truth below.
Do not invent facts. If data is missing, say what is missing.

Decision logic:
- Validate internal data first.
- Compare current results against targets.
- Identify gaps and risks.
- Prioritise the most important issues.
- Apply the Theory of Change.
- Generate strategic insights and recommendations.

Trusted Single Source of Truth:
{findings["ssot_summary"]}

Theory of Change:
{findings["theory_of_change"]}

Structured Agent Analysis:

OKR Results:
{findings["okr_results"]}

Risks:
{findings["risks"]}

Priorities:
{findings["priorities"]}

User question:
{user_question}

Response structure:
1. Answer
2. Evidence from internal data
3. Key risk or gap
4. Recommendation
5. Next action

Use professional, simple language.
"""

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=prompt,
        )
        return response.output_text

    except Exception as e:
        return f"ERROR: OpenAI request failed. {e}"