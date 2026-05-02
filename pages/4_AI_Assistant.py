"""
AI Chat — interactive query of Monkey Baa's cleaned datasets.
"""

from __future__ import annotations

import os
import sys
import json
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
from lib.style import inject_css, render_sidebar_nav

inject_css()
render_sidebar_nav()
# --------------------------------------------------
# PATH SETUP
# --------------------------------------------------
APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR))


# --------------------------------------------------
# STYLE
# --------------------------------------------------
def inject_css():
    st.markdown(
        """
        <style>
        .chat-title {
            padding: 1rem;
            border-radius: 16px;
            background: linear-gradient(135deg, #5b2c83, #d64b8c);
            color: white;
            margin-bottom: 1rem;
        }
        .type-pill {
            display: inline-block;
            padding: 0.25rem 0.65rem;
            border-radius: 999px;
            background: #f1e7ff;
            color: #5b2c83;
            font-size: 0.8rem;
            font-weight: 600;
            margin-bottom: 0.4rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def banner(title, subtitle):
    st.markdown(
        f"""
        <div class="chat-title">
            <h1>{title}</h1>
            <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section(title):
    st.markdown(f"### {title}")


try:
    from lib.assistant import render_helper
except Exception:
    render_helper = None


# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(
    page_title="AI Chat",
    page_icon="🤖",
    layout="wide",
)

inject_css()

banner(
    "AI Analyst · Chat",
    "Ask questions about Monkey Baa's saved datasets, OKRs, survey feedback, "
    "impact indicators, Theory of Change, business performance, and social impact results.",
)


# --------------------------------------------------
# OPENAI CLIENT
# --------------------------------------------------
def get_openai_client():
    api_key = None

    try:
        api_key = st.secrets.get("OPENAI_API_KEY")
    except Exception:
        pass

    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        return None

    return OpenAI(api_key=api_key)


client = get_openai_client()


# --------------------------------------------------
# LOAD SAVED DATASETS
# --------------------------------------------------
DATA_FOLDERS = [
    APP_DIR / "stored_data",
    APP_DIR / "data",
]

DATASET_TYPES = [
    "Survey Data",
    "Dashboard Data",
    "Performance Information",
    "Audience Data",
    "Financial Data",
    "Venue Reference Data",
    "Framework Dictionary",
    "Theory of Change",
    "Other",
]


def detect_dataset_type(file_name: str, df: pd.DataFrame) -> str:
    name = file_name.lower()
    cols = " ".join([str(c).lower() for c in df.columns])

    if any(word in name for word in ["survey", "feedback", "response"]) or any(
        word in cols
        for word in ["survey", "feedback", "recommend", "satisfaction", "confidence"]
    ):
        return "Survey Data"

    if any(word in name for word in ["dashboard", "summary", "kpi"]):
        return "Dashboard Data"

    if any(word in name for word in ["performance", "tour", "show"]) or any(
        word in cols for word in ["performance", "show", "production", "attendance"]
    ):
        return "Performance Information"

    if any(word in name for word in ["audience", "visitor", "participant"]) or any(
        word in cols for word in ["audience", "young people", "parents", "teachers"]
    ):
        return "Audience Data"

    if any(
        word in name
        for word in ["finance", "financial", "ledger", "budget", "revenue", "cost"]
    ) or any(
        word in cols for word in ["revenue", "cost", "income", "expense", "budget"]
    ):
        return "Financial Data"

    if any(word in name for word in ["venue", "location", "regional", "metro"]) or any(
        word in cols for word in ["venue", "location", "regional", "metropolitan", "postcode"]
    ):
        return "Venue Reference Data"

    if any(
        word in name
        for word in ["framework", "indicator", "okr", "objective", "outcome"]
    ) or any(
        word in cols for word in ["objective", "key result", "indicator", "outcome", "impact"]
    ):
        return "Framework Dictionary"

    if any(word in name for word in ["theory", "change", "toc"]):
        return "Theory of Change"

    return "Other"


def load_available_datasets() -> dict[str, dict]:
    datasets = {}

    for folder in DATA_FOLDERS:
        if not folder.exists():
            continue

        for file in folder.glob("*"):
            try:
                if file.suffix.lower() == ".csv":
                    df = pd.read_csv(file)
                elif file.suffix.lower() in [".xlsx", ".xls"]:
                    df = pd.read_excel(file)
                else:
                    continue

                datasets[file.name] = {
                    "dataframe": df,
                    "path": str(file),
                    "type": detect_dataset_type(file.name, df),
                }

            except Exception as e:
                st.warning(f"Could not load {file.name}: {e}")

    return datasets


# --------------------------------------------------
# DATE + BUSINESS PERFORMANCE LOGIC
# --------------------------------------------------
def find_date_column(df: pd.DataFrame):
    possible_names = [
        "date",
        "submission date",
        "submit date",
        "start date",
        "event date",
        "created",
        "timestamp",
        "time",
    ]

    for col in df.columns:
        col_lower = str(col).lower()
        if any(name in col_lower for name in possible_names):
            converted = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
            if converted.notna().sum() > 0:
                return col

    return None


def get_last_quarter_label() -> str:
    today = pd.Timestamp.today()
    return str(today.to_period("Q") - 1)


def prepare_quarter_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    date_col = find_date_column(df)

    if not date_col:
        return df

    df["analysis_date"] = pd.to_datetime(df[date_col], errors="coerce", dayfirst=True)
    df = df.dropna(subset=["analysis_date"])
    df["quarter"] = df["analysis_date"].dt.to_period("Q").astype(str)

    return df


def calculate_last_quarter_business_summary(datasets: dict[str, dict]) -> dict:
    last_quarter = get_last_quarter_label()

    survey_frames = []
    performance_frames = []
    financial_frames = []
    audience_frames = []

    for name, item in datasets.items():
        df = item["dataframe"]
        dtype = item["type"]

        prepared = prepare_quarter_data(df)

        if "quarter" not in prepared.columns:
            continue

        qdf = prepared[prepared["quarter"] == last_quarter].copy()

        if qdf.empty:
            continue

        if dtype == "Survey Data":
            survey_frames.append((name, qdf))
        elif dtype == "Performance Information":
            performance_frames.append((name, qdf))
        elif dtype == "Financial Data":
            financial_frames.append((name, qdf))
        elif dtype == "Audience Data":
            audience_frames.append((name, qdf))

    summary = {
        "quarter": last_quarter,
        "survey_summary": {},
        "performance_summary": {},
        "financial_summary": {},
        "audience_summary": {},
        "available_evidence": [],
        "missing_evidence": [],
    }

    if survey_frames:
        all_surveys = pd.concat([df for _, df in survey_frames], ignore_index=True)
        summary["available_evidence"].append("Survey Data")
        summary["survey_summary"]["total_responses"] = int(len(all_surveys))

        numeric_cols = all_surveys.select_dtypes(include="number").columns.tolist()

        metric_keywords = [
            "satisfaction",
            "confidence",
            "creativity",
            "engagement",
            "enjoyment",
            "recommend",
            "rating",
            "score",
            "inclusive",
            "inclusion",
            "thinking",
        ]

        selected_metrics = [
            col
            for col in numeric_cols
            if any(k in str(col).lower() for k in metric_keywords)
        ]

        metric_results = {}

        for col in selected_metrics:
            values = pd.to_numeric(all_surveys[col], errors="coerce").dropna()
            if not values.empty:
                metric_results[col] = {
                    "average": round(float(values.mean()), 2),
                    "count": int(values.count()),
                    "min": round(float(values.min()), 2),
                    "max": round(float(values.max()), 2),
                }

        summary["survey_summary"]["metrics"] = metric_results

        possible_show_cols = [
            col
            for col in all_surveys.columns
            if "show" in str(col).lower() or "production" in str(col).lower()
        ]

        if possible_show_cols:
            show_col = possible_show_cols[0]
            summary["survey_summary"]["top_shows"] = (
                all_surveys[show_col]
                .dropna()
                .astype(str)
                .value_counts()
                .head(5)
                .to_dict()
            )
    else:
        summary["missing_evidence"].append("Survey Data for last quarter")

    if performance_frames:
        all_perf = pd.concat([df for _, df in performance_frames], ignore_index=True)
        summary["available_evidence"].append("Performance Information")
        summary["performance_summary"]["records"] = int(len(all_perf))

        numeric_cols = all_perf.select_dtypes(include="number").columns.tolist()
        perf_metrics = {}

        for col in numeric_cols:
            values = pd.to_numeric(all_perf[col], errors="coerce").dropna()
            if not values.empty:
                perf_metrics[col] = {
                    "total": round(float(values.sum()), 2),
                    "average": round(float(values.mean()), 2),
                    "count": int(values.count()),
                }

        summary["performance_summary"]["metrics"] = perf_metrics
    else:
        summary["missing_evidence"].append("Performance Information for last quarter")

    if financial_frames:
        all_fin = pd.concat([df for _, df in financial_frames], ignore_index=True)
        summary["available_evidence"].append("Financial Data")
        summary["financial_summary"]["records"] = int(len(all_fin))

        numeric_cols = all_fin.select_dtypes(include="number").columns.tolist()
        finance_metrics = {}

        for col in numeric_cols:
            values = pd.to_numeric(all_fin[col], errors="coerce").dropna()
            if not values.empty:
                finance_metrics[col] = {
                    "total": round(float(values.sum()), 2),
                    "average": round(float(values.mean()), 2),
                    "count": int(values.count()),
                }

        summary["financial_summary"]["metrics"] = finance_metrics
    else:
        summary["missing_evidence"].append("Financial Data for last quarter")

    if audience_frames:
        all_aud = pd.concat([df for _, df in audience_frames], ignore_index=True)
        summary["available_evidence"].append("Audience Data")
        summary["audience_summary"]["records"] = int(len(all_aud))

        numeric_cols = all_aud.select_dtypes(include="number").columns.tolist()
        audience_metrics = {}

        for col in numeric_cols:
            values = pd.to_numeric(all_aud[col], errors="coerce").dropna()
            if not values.empty:
                audience_metrics[col] = {
                    "total": round(float(values.sum()), 2),
                    "average": round(float(values.mean()), 2),
                    "count": int(values.count()),
                }

        summary["audience_summary"]["metrics"] = audience_metrics
    else:
        summary["missing_evidence"].append("Audience Data for last quarter")

    return summary


def is_business_performance_question(question: str) -> bool:
    q = question.lower()

    business_keywords = [
        "business performed",
        "business performance",
        "last quarter",
        "quarter",
        "performance last quarter",
        "how did we perform",
        "how did my business perform",
        "company performance",
        "organisation performance",
        "overall performance",
        "strongest and weakest performance",
        "board-ready business performance",
    ]

    return any(keyword in q for keyword in business_keywords)


def build_business_performance_context(summary: dict) -> str:
    return f"""
Business performance analysis context for Monkey Baa.

Quarter being analysed:
{summary.get("quarter")}

Available evidence:
{summary.get("available_evidence")}

Missing evidence:
{summary.get("missing_evidence")}

Survey summary:
{summary.get("survey_summary")}

Performance summary:
{summary.get("performance_summary")}

Financial summary:
{summary.get("financial_summary")}

Audience summary:
{summary.get("audience_summary")}

Important instruction:
- Use only the evidence provided.
- If financial, attendance, or audience data is missing, explain that business performance can only be partially assessed.
- For Monkey Baa, business performance should include social impact, audience engagement, program delivery, survey evidence, and financial evidence when available.
- Do not invent numbers.
"""


# --------------------------------------------------
# GENERAL DATA CONTEXT
# --------------------------------------------------
def summarise_dataframe(name: str, item: dict) -> str:
    df = item["dataframe"]
    dtype = item["type"]

    summary = []

    summary.append(f"Dataset name: {name}")
    summary.append(f"Dataset type: {dtype}")
    summary.append(f"Rows: {len(df)}")
    summary.append(f"Columns: {len(df.columns)}")
    summary.append(f"Column names: {', '.join(map(str, df.columns))}")

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    text_cols = df.select_dtypes(include="object").columns.tolist()

    if numeric_cols:
        summary.append("Numeric columns summary:")
        summary.append(df[numeric_cols].describe().round(2).to_string())

    if text_cols:
        summary.append("Text columns detected:")
        summary.append(", ".join(text_cols[:15]))

        sample_text = []
        for col in text_cols[:5]:
            values = df[col].dropna().astype(str).head(5).tolist()
            if values:
                sample_text.append(f"{col}: {values}")

        if sample_text:
            summary.append("Sample text values:")
            summary.append("\n".join(sample_text))

    return "\n".join(summary)


def build_context_summary(datasets: dict[str, dict]) -> str:
    if not datasets:
        return """
No uploaded datasets were found.

The assistant should explain that data must be uploaded through the Data Library
before detailed analysis can be generated.
"""

    context_parts = [
        """
Monkey Baa project context:
- The system is an AI-powered social impact reporting tool.
- It analyses survey data, Excel files, cleaned datasets, OKRs, and impact indicators.
- The analysis should align with Monkey Baa's Theory of Change.
- The key impact journey is: The Spark → The Growth → The Legacy.
- The system should focus on social outcomes, cultural outcomes, reach, engagement,
  confidence, creativity, inclusion, participation, and stakeholder value.
- Business performance should be interpreted through both operational evidence and social impact evidence.
- Answers should be practical, clear, and suitable for non-technical users.
- When possible, explain what the data suggests, why it matters, and what action is recommended.
"""
    ]

    for name, item in datasets.items():
        context_parts.append(summarise_dataframe(name, item))

    return "\n\n---\n\n".join(context_parts)


# --------------------------------------------------
# PRINT REPORT BUTTON
# --------------------------------------------------
def render_print_report_button(report_text: str):
    report_json = json.dumps(report_text)

    html = f"""
    <script>
    function printAIReport() {{
        const reportContent = {report_json};
        const printWindow = window.open('', '_blank');

        printWindow.document.write(`
            <html>
            <head>
                <title>Monkey Baa AI Report</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        margin: 40px;
                        line-height: 1.6;
                        color: #222;
                    }}
                    h1 {{
                        color: #5b2c83;
                        border-bottom: 3px solid #d64b8c;
                        padding-bottom: 10px;
                    }}
                    .meta {{
                        color: #666;
                        font-size: 14px;
                        margin-bottom: 25px;
                    }}
                    .report {{
                        white-space: pre-wrap;
                        font-size: 15px;
                    }}
                </style>
            </head>
            <body>
                <h1>Monkey Baa AI Analysis Report</h1>
                <div class="meta">
                    Generated from the AI Assistant using saved Monkey Baa system data.
                </div>
                <div class="report">${{reportContent}}</div>
            </body>
            </html>
        `);

        printWindow.document.close();
        printWindow.focus();
        printWindow.print();
    }}
    </script>

    <button onclick="printAIReport()" style="
        background: linear-gradient(135deg, #5b2c83, #d64b8c);
        color: white;
        border: none;
        padding: 0.75rem 1.2rem;
        border-radius: 12px;
        font-weight: 700;
        cursor: pointer;
        margin-top: 1rem;
    ">
        🖨️ Print AI Report
    </button>
    """

    components.html(html, height=90)


# --------------------------------------------------
# AI FUNCTION
# --------------------------------------------------
def ask_ai(question: str, context: str, chat_history: list[dict]) -> str:
    if client is None:
        return """
⚠️ OpenAI API key not found.

To fix this locally, add this to `.env`:

OPENAI_API_KEY=your-api-key-here

To fix this in Streamlit Cloud, add this to Secrets:

OPENAI_API_KEY = "your-api-key-here"
"""

    messages = [
        {
            "role": "system",
            "content": """
You are the AI Analyst for the Monkey Baa Theatre Company social impact reporting tool.

Your role:
- Analyse cleaned datasets saved in the system.
- Recognise dataset types such as Survey Data, Dashboard Data, Performance Information,
  Audience Data, Financial Data, Venue Reference Data, Framework Dictionary,
  Theory of Change, and Other.
- Explain survey and impact results in plain English.
- Link insights to Monkey Baa's Theory of Change.
- Use OKR-style thinking.
- For business performance questions, assess available evidence from survey, audience,
  performance, and financial data.
- Identify strengths, risks, gaps, and recommendations.
- Avoid making up numbers.
- If the data does not contain enough information, say so clearly.
- Write in a professional, board-ready style.
""",
        }
    ]

    for msg in chat_history[-6:]:
        if msg.get("role") in ["user", "assistant"]:
            messages.append(
                {
                    "role": msg["role"],
                    "content": msg["content"],
                }
            )

    messages.append(
        {
            "role": "user",
            "content": f"""
Here is the available dataset context:

{context}

Now answer this user question:

{question}
""",
        }
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.3,
    )

    return response.choices[0].message.content


# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------
if "chat_messages" not in st.session_state:
    st.session_state["chat_messages"] = []

if "latest_ai_report" not in st.session_state:
    st.session_state["latest_ai_report"] = None


# --------------------------------------------------
# MAIN PAGE
# --------------------------------------------------
datasets = load_available_datasets()

c1, c2, c3 = st.columns([1, 1, 2])

with c1:
    if st.button("🧹 Clear conversation", use_container_width=True):
        st.session_state["chat_messages"] = []
        st.session_state["latest_ai_report"] = None
        st.rerun()

with c2:
    st.metric("Datasets found", len(datasets))

with c3:
    if datasets:
        st.success("Saved data loaded from /stored_data and /data. AI analysis is ready.")
    else:
        st.warning("No datasets found yet. Upload data through your Data Library first.")


with st.expander("📂 View available datasets"):
    if datasets:
        for name, item in datasets.items():
            df = item["dataframe"]
            dtype = item["type"]

            st.markdown(
                f"""
                <span class="type-pill">{dtype}</span>  
                **{name}** — {len(df)} rows, {len(df.columns)} columns
                """,
                unsafe_allow_html=True,
            )

            st.dataframe(df.head(5), use_container_width=True)
    else:
        st.info("No CSV or Excel files were found in /data or /stored_data.")


section("Suggested prompts")

suggestions = [
    "How did my business perform in the last quarter?",
    "What were the strongest and weakest performance areas last quarter?",
    "Give me a board-ready business performance summary for the last quarter.",
    "Summarise the strongest social impact signals in the uploaded data.",
    "Which OKR or impact area appears strongest, and which one needs attention?",
    "What does the data suggest about confidence, creativity, and inclusion?",
    "Identify key risks or gaps in the current impact evidence.",
    "Generate a board-ready summary of Monkey Baa's social impact.",
]

scols = st.columns(4)

for i, suggestion in enumerate(suggestions):
    with scols[i % 4]:
        if st.button(suggestion, use_container_width=True, key=f"suggestion_{i}"):
            st.session_state["_pending_prompt"] = suggestion


section("Conversation")

for message in st.session_state["chat_messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        if (
            message["role"] == "assistant"
            and st.session_state.get("latest_ai_report") == message["content"]
        ):
            render_print_report_button(message["content"])


prompt = st.chat_input(
    "Ask about business performance, last quarter, impact, OKRs, survey feedback, confidence, creativity, inclusion, reach..."
)

pending = st.session_state.pop("_pending_prompt", None)
prompt = prompt or pending


if prompt:
    st.session_state["chat_messages"].append(
        {
            "role": "user",
            "content": prompt,
        }
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    if is_business_performance_question(prompt):
        business_summary = calculate_last_quarter_business_summary(datasets)
        context = build_business_performance_context(business_summary)
    else:
        context = build_context_summary(datasets)

    with st.chat_message("assistant"):
        with st.spinner("Analysing Monkey Baa saved data..."):
            try:
                reply = ask_ai(
                    question=prompt,
                    context=context,
                    chat_history=st.session_state["chat_messages"],
                )
            except Exception as e:
                reply = f"⚠️ AI error: {e}"

        st.markdown(reply)

        st.session_state["latest_ai_report"] = reply
        render_print_report_button(reply)

    st.session_state["chat_messages"].append(
        {
            "role": "assistant",
            "content": reply,
        }
    )


# --------------------------------------------------
# AI HELPER PANEL
# --------------------------------------------------
if render_helper:
    render_helper(
        page_key="chat",
        page_title="AI Chat",
        extra_context=f"Messages in session: {len(st.session_state.get('chat_messages', []))}",
    )