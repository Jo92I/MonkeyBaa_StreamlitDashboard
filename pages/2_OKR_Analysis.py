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
    page_title="Monkey Baa - OKR Analysis",
    page_icon="🎯",
    layout="wide"
)
from lib.style import inject_css, render_sidebar_nav

inject_css()
render_sidebar_nav()

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
    <div class="hero-title">🎯 Monkey Baa OKR Analysis</div>
    <div class="hero-text">
        Select saved files from the Data Library to calculate OKR results, generate AI insights,
        and download one complete AI report with insights, suggestions, KPI results and graphics.
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


def generate_ai_okr_analysis(objective, actual, target, variance):
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

    try:
        client = OpenAI(api_key=OPENAI_API_KEY)

        response = client.responses.create(
            model="gpt-4.1-mini",
            input=f"""
            You are an AI social impact analyst for Monkey Baa Theatre Company.

            Analyse this OKR result and provide a practical recommendation.

            Objective:
            {objective}

            Actual result:
            {actual:.1f}%

            Target:
            {target:.1f}%

            Variance:
            {variance:.1f}%

            Write the response in this exact structure:

            1. Insight:
            Explain what the result means in relation to Monkey Baa's Theory of Change.

            2. Likely reason:
            Explain the possible reason why the result is above or below target.

            3. Suggested solution:
            Give a practical recommendation to improve or maintain the result.

            4. Next action:
            Give one clear action Monkey Baa staff could take next.

            Keep the full response under 160 words.
            Use professional but simple language.
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
    objective_ai_map
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

    story = []

    story.append(Paragraph("Monkey Baa OKR AI Analysis Report", title_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph(
        f"<b>Survey/Data file used:</b> {selected_survey_name}",
        body_style
    ))

    story.append(Spacer(1, 8))

    story.append(Paragraph(
        "This report summarises Monkey Baa's OKR performance using the selected survey/data file. "
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
        ["Total Objectives", str(results_df[col_objective].nunique())],
        ["Total Key Results", str(results_df[col_key_result].nunique())],
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

    story.append(Paragraph("OKR Benchmarking Table", heading_style))

    table_data = [["Objective", "Key Result", "Actual", "Target", "Variance"]]

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

    story.append(Paragraph("Objective-Level AI Insights and Suggestions", heading_style))
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
        story.append(Paragraph(f"Objective: {objective}", styles["Heading3"]))

        mini_table_data = [
            ["Actual", "Target", "Variance", "Key Results"],
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

        kr_table_data = [["Key Result", "Actual", "Target", "Status"]]

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
df_survey.columns = [clean_text(c) for c in df_survey.columns]

st.success("Files loaded successfully from Data Library.")

if OPENAI_API_KEY:
    st.caption("AI connection active: API key loaded.")
else:
    st.error(api_key_error)


# -------------------------------------------------
# VALIDATE FRAMEWORK COLUMNS
# -------------------------------------------------
framework_cols = {
    str(col).lower().replace(" ", ""): col
    for col in df_framework.columns
}

col_objective = framework_cols.get("objective")
col_key_result = framework_cols.get("keyresult")
col_formula = framework_cols.get("formula")
col_expected = framework_cols.get("expected")
col_outcome_area = framework_cols.get("outcomearea")

required_cols = [
    col_objective,
    col_key_result,
    col_formula,
    col_expected
]

if not all(required_cols):
    st.error("""
    Missing required columns in the Framework Dictionary.

    Required:
    - Objective
    - Key Result
    - Formula
    - Expected

    Optional but recommended:
    - Outcome Area
    """)
    st.stop()


# -------------------------------------------------
# RUN ANALYSIS BUTTON
# -------------------------------------------------
if st.button("Run OKR Analysis"):
    with st.spinner("Calculating OKR impact metrics and generating AI insights..."):
        df_results = df_framework.copy()

        df_results["Actual"] = df_results[col_formula].apply(
            lambda x: calculate_kpi(x, df_survey)
        )

        df_results["Expected_Num"] = df_results[col_expected].apply(
            fix_expected_value
        )

    st.session_state["okr_results"] = df_results
    st.session_state["okr_columns"] = {
        "objective": col_objective,
        "key_result": col_key_result,
        "outcome_area": col_outcome_area,
        "survey_name": selected_survey_name
    }

    st.success("OKR analysis completed.")


if "okr_results" not in st.session_state:
    st.info("Click **Run OKR Analysis** to generate results.")
    st.stop()


df_results = st.session_state["okr_results"]
col_objective = st.session_state["okr_columns"]["objective"]
col_key_result = st.session_state["okr_columns"]["key_result"]
col_outcome_area = st.session_state["okr_columns"]["outcome_area"]
selected_survey_name = st.session_state["okr_columns"]["survey_name"]


# -------------------------------------------------
# SUMMARY
# -------------------------------------------------
st.subheader("📊 Overall OKR Performance")

st.caption(f"Analysis based on selected survey/data file: **{selected_survey_name}**")

total_objectives = df_results[col_objective].nunique()
total_key_results = df_results[col_key_result].nunique()
avg_actual = df_results["Actual"].mean()
avg_target = df_results["Expected_Num"].mean()
avg_variance = avg_actual - avg_target

m1, m2, m3, m4 = st.columns(4)

m1.metric("Objectives", total_objectives)
m2.metric("Key Results", total_key_results)
m3.metric("Average Actual", f"{avg_actual:.1f}%")
m4.metric("Average Target", f"{avg_target:.1f}%", f"{avg_variance:.1f}%")

overall_ai = generate_ai_okr_analysis(
    "Overall OKR performance",
    avg_actual,
    avg_target,
    avg_variance
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
    st.header(f"📍 Outcome Area: {area}")

    df_area = df_results[df_results[col_outcome_area] == area]

    for objective in df_area[col_objective].dropna().unique():
        df_objective = df_area[df_area[col_objective] == objective]

        objective_actual = df_objective["Actual"].mean()
        objective_target = df_objective["Expected_Num"].mean()
        variance = objective_actual - objective_target

        st.markdown(f"""
        <div class="okr-card">
            <h2 style="margin-top:0;">🎯 Objective: {objective}</h2>
            <p>
                Overall progress is based on
                <strong>{len(df_objective)}</strong> equally weighted Key Results.
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
                variance
            )

            objective_ai_map[str(objective)] = ai_text

            st.markdown(f"""
            <div class="ai-insight">
                <strong>🤖 AI Insight, Suggested Solution and Next Action:</strong><br>
                {ai_text}
            </div>
            """, unsafe_allow_html=True)

        with st.expander("Show Key Results and Indicator Breakdown"):
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
                        key=f"okr_donut_{safe_kr_name}_{row_index}_{chart_counter}",
                        config={
                            "modeBarButtonsToRemove": ["toImage"],
                            "displaylogo": False
                        }
                    )

                    st.download_button(
                        label="⬇️ Download chart data",
                        data=df_objective.to_csv(index=False).encode("utf-8"),
                        file_name="okr_key_result_breakdown.csv",
                        mime="text/csv",
                        key=f"download_okr_data_{row_index}_{chart_counter}"
                    )

                with p2:
                    st.write(f"**{kr_name}**")
                    st.caption(f"Score: {actual:.1f}% / Target: {expected:.1f}%")

                    if actual >= expected:
                        st.success("This Key Result is meeting or exceeding target.")
                    else:
                        st.warning("This Key Result is below target.")


# -------------------------------------------------
# BENCHMARKING
# -------------------------------------------------
st.divider()
st.subheader("📊 Actual vs Target OKR Benchmarking")

benchmark_df = df_results.set_index(col_key_result)[
    ["Actual", "Expected_Num"]
]

st.bar_chart(benchmark_df)


# -------------------------------------------------
# ONE PDF REPORT DOWNLOAD ONLY
# -------------------------------------------------
st.subheader("⬇️ Download AI OKR Report")

pdf_buffer = create_pdf_report(
    df_results,
    col_objective,
    col_key_result,
    col_outcome_area,
    selected_survey_name,
    overall_ai,
    objective_ai_map
)

st.download_button(
    label="Download PDF Report",
    data=pdf_buffer,
    file_name="monkey_baa_ai_okr_report.pdf",
    mime="application/pdf"
)

from lib.floating_assistant import render_floating_ai_assistant
render_floating_ai_assistant()