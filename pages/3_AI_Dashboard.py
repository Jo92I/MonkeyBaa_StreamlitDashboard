import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

from lib.data_store import load_all_data, list_datasets, load_dataset
from lib.geo_australia import add_geographic_insights
from lib.venue_matcher import add_venue_area_to_survey
from lib.ai_config import get_openai_client

try:
    from openai import OpenAI
except Exception:
    OpenAI = None


# -------------------------------------------------
# PAGE CONFIG + LOGIN
# -------------------------------------------------
st.set_page_config(page_title="Data Review Dashboard", page_icon="📊", layout="wide")

if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("Please login first from the Home page.")
    st.stop()


# -------------------------------------------------
# OPENAI KEY
# -------------------------------------------------
OPENAI_API_KEY, api_key_error = get_openai_client()


# -------------------------------------------------
# CSS DESIGN
# -------------------------------------------------
st.markdown("""
<style>
:root {
    --card-bg: rgba(255,255,255,0.94);
    --text-main: #1f2937;
    --text-soft: #6b7280;
    --accent: #b83280;
    --accent-soft: #fce7f3;
    --border: #f3d1e3;
    --shadow: rgba(0,0,0,0.08);
}

@media (prefers-color-scheme: dark) {
    :root {
        --card-bg: rgba(31,41,55,0.94);
        --text-main: #f9fafb;
        --text-soft: #d1d5db;
        --accent: #f9a8d4;
        --accent-soft: rgba(131,24,67,0.35);
        --border: rgba(249,168,212,0.35);
        --shadow: rgba(0,0,0,0.35);
    }
}

.hero-card, .content-card, .metric-card {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 24px;
    padding: 24px;
    margin-bottom: 20px;
    box-shadow: 0 10px 28px var(--shadow);
}

.hero-title {
    color: var(--text-main);
    font-size: 38px;
    font-weight: 800;
    margin-bottom: 8px;
}

.hero-subtitle {
    color: var(--text-soft);
    font-size: 17px;
    line-height: 1.6;
}

.section-title {
    color: var(--text-main);
    font-size: 26px;
    font-weight: 750;
    margin-top: 20px;
    margin-bottom: 12px;
}

.metric-number {
    color: var(--accent);
    font-size: 34px;
    font-weight: 800;
    text-align: center;
}

.metric-label {
    color: var(--text-soft);
    font-size: 15px;
    text-align: center;
}

.insight-box {
    background: var(--accent-soft);
    border-left: 6px solid var(--accent);
    border-radius: 16px;
    padding: 18px;
    color: var(--text-main);
    margin-bottom: 18px;
}
</style>
""", unsafe_allow_html=True)


# -------------------------------------------------
# HEADER
# -------------------------------------------------
st.markdown("""
<div class="hero-card">
    <div class="hero-title">📊 Monkey Baa Data Review Dashboard</div>
    <div class="hero-subtitle">
        Select any saved dataset from the Data Library and automatically review its structure,
        key values, charts, show activity, regional information, missing values and useful insights.
    </div>
</div>
""", unsafe_allow_html=True)


# -------------------------------------------------
# LOAD DATASETS
# -------------------------------------------------
datasets = list_datasets()

if not datasets:
    st.warning("No saved datasets found. Please upload and save data in the Data Library first.")
    st.stop()


# -------------------------------------------------
# DATASET SELECTION
# -------------------------------------------------
st.markdown('<div class="section-title">📁 Select Data to Review</div>', unsafe_allow_html=True)

dataset_options = ["All Saved Data"] + [item["dataset_name"] for item in datasets]

selected_dataset = st.selectbox(
    "Choose the dataset you want to review",
    dataset_options
)

if selected_dataset == "All Saved Data":
    df = load_all_data()
    selected_item = {"dataset_name": "All Saved Data", "dataset_type": "Combined"}
else:
    selected_item = next(item for item in datasets if item["dataset_name"] == selected_dataset)
    df = load_dataset(selected_item["filename"])

if df.empty:
    st.error("The selected dataset is empty.")
    st.stop()


# -------------------------------------------------
# ENRICH DATA
# -------------------------------------------------
catalog = list_datasets()

df = add_geographic_insights(df)

df, venue_message = add_venue_area_to_survey(
    df,
    catalog,
    load_dataset
)


# -------------------------------------------------
# COLUMN DETECTION
# -------------------------------------------------
def detect_column(dataframe, keywords):
    for col in dataframe.columns:
        col_lower = str(col).lower()
        if any(keyword in col_lower for keyword in keywords):
            return col
    return None


show_col = detect_column(df, ["show"])
date_col = detect_column(df, ["date", "year", "submit", "start"])
venue_col = detect_column(df, ["venue", "where did you see", "location", "theatre"])
postcode_col = detect_column(df, ["postcode", "post code"])

if date_col:
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df["Year"] = df[date_col].dt.year


# -------------------------------------------------
# DATA FILTERING
# -------------------------------------------------
st.markdown('<div class="section-title">🔎 Filter Selected Dataset</div>', unsafe_allow_html=True)

filtered_df = df.copy()

filter_columns = st.multiselect(
    "Choose columns to filter",
    options=df.columns.tolist()
)

for col in filter_columns:
    unique_values = df[col].dropna().astype(str).unique()

    if len(unique_values) <= 50:
        selected_values = st.multiselect(
            f"Filter by {col}",
            options=sorted(unique_values),
            key=f"filter_{col}"
        )

        if selected_values:
            filtered_df = filtered_df[
                filtered_df[col].astype(str).isin(selected_values)
            ]

    else:
        search_text = st.text_input(
            f"Search inside {col}",
            key=f"search_{col}"
        )

        if search_text:
            filtered_df = filtered_df[
                filtered_df[col].astype(str).str.contains(
                    search_text,
                    case=False,
                    na=False
                )
            ]

st.info(f"Showing {filtered_df.shape[0]} of {df.shape[0]} records after filtering.")

df = filtered_df


# -------------------------------------------------
# METRIC CARDS
# -------------------------------------------------
numeric_cols = df.select_dtypes(include="number").columns.tolist()
text_cols = df.select_dtypes(include="object").columns.tolist()
missing_values = int(df.isna().sum().sum())

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-number">{df.shape[0]}</div>
        <div class="metric-label">Rows / Records</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-number">{df.shape[1]}</div>
        <div class="metric-label">Columns / Fields</div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-number">{len(numeric_cols)}</div>
        <div class="metric-label">Numeric Fields</div>
    </div>
    """, unsafe_allow_html=True)

with c4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-number">{missing_values}</div>
        <div class="metric-label">Missing Values</div>
    </div>
    """, unsafe_allow_html=True)


# -------------------------------------------------
# AI SUMMARY
# -------------------------------------------------
def generate_ai_summary(data):
    column_names = ", ".join([str(c) for c in data.columns[:30]])

    show_summary = "No show column detected."
    if show_col:
        top_shows = data[show_col].dropna().astype(str).value_counts().head(5)
        show_summary = "; ".join([f"{k}: {v}" for k, v in top_shows.items()])

    regional_summary = "No regional/metro field detected."
    if "Venue Area" in data.columns:
        area_counts = data["Venue Area"].dropna().astype(str).value_counts()
        regional_summary = "; ".join([f"{k}: {v}" for k, v in area_counts.items()])
    elif "Area Type" in data.columns:
        area_counts = data["Area Type"].dropna().astype(str).value_counts()
        regional_summary = "; ".join([f"{k}: {v}" for k, v in area_counts.items()])

    fallback = (
        f"This dataset contains {data.shape[0]} records and {data.shape[1]} columns. "
        f"Important detected fields include: {column_names}. "
        f"Show activity: {show_summary}. "
        f"Regional or metro distribution: {regional_summary}."
    )

    if not OPENAI_API_KEY or OpenAI is None:
        return fallback

    try:
        client = OpenAI(api_key=OPENAI_API_KEY)

        response = client.responses.create(
            model="gpt-4.1-mini",
            input=f"""
            Write a clear professional summary of this dataset for Monkey Baa Theatre Company.

            Focus on:
            - what the dataset appears to contain
            - important fields
            - show activity
            - survey count per show if available
            - regional or metro information if available
            - what the organisation should notice

            Dataset name: {selected_dataset}
            Dataset type: {selected_item.get("dataset_type", "")}
            Rows: {data.shape[0]}
            Columns: {data.shape[1]}
            Columns: {column_names}
            Show summary: {show_summary}
            Regional summary: {regional_summary}

            Keep it under 140 words.
            """
        )

        return response.output_text

    except Exception:
        return fallback


st.markdown('<div class="section-title">🤖 Automatic Data Summary</div>', unsafe_allow_html=True)

summary_text = generate_ai_summary(df)

st.markdown(f"""
<div class="insight-box">
    <strong>Summary:</strong><br>
    {summary_text}
</div>
""", unsafe_allow_html=True)


# -------------------------------------------------
# DATA PREVIEW
# -------------------------------------------------
st.markdown('<div class="section-title">👀 Data Preview</div>', unsafe_allow_html=True)

with st.expander("View first 100 rows", expanded=False):
    st.dataframe(df.head(100), use_container_width=True)


# -------------------------------------------------
# GENERAL DATA QUALITY
# -------------------------------------------------
st.markdown('<div class="section-title">🧹 Data Quality Overview</div>', unsafe_allow_html=True)

quality_cols = st.columns(2)

with quality_cols[0]:
    missing_by_col = df.isna().sum().sort_values(ascending=False).head(15).reset_index()
    missing_by_col.columns = ["Column", "Missing Values"]

    fig_missing = px.bar(
        missing_by_col,
        x="Column",
        y="Missing Values",
        title="Top Columns with Missing Values",
        text="Missing Values"
    )
    fig_missing.update_layout(xaxis_tickangle=-35)
    st.plotly_chart(fig_missing, use_container_width=True, key="missing_values_chart")

with quality_cols[1]:
    dtype_df = pd.DataFrame(df.dtypes.astype(str).value_counts()).reset_index()
    dtype_df.columns = ["Data Type", "Count"]

    fig_types = px.pie(
        dtype_df,
        names="Data Type",
        values="Count",
        title="Column Type Distribution"
    )
    st.plotly_chart(fig_types, use_container_width=True, key="data_type_chart")


# -------------------------------------------------
# SHOW ANALYSIS
# -------------------------------------------------
st.markdown('<div class="section-title">🎭 Show Review</div>', unsafe_allow_html=True)

if show_col:
    show_counts = df[show_col].dropna().astype(str).value_counts().reset_index()
    show_counts.columns = ["Show Name", "Survey / Record Count"]

    left, right = st.columns([2, 1])

    with left:
        fig_show = px.bar(
            show_counts.head(20),
            x="Show Name",
            y="Survey / Record Count",
            title="Survey / Record Count by Show",
            text="Survey / Record Count"
        )
        fig_show.update_layout(xaxis_tickangle=-35)
        st.plotly_chart(fig_show, use_container_width=True, key="show_count_chart")

    with right:
        st.dataframe(show_counts, use_container_width=True)

else:
    st.info("No show column detected. A show column usually contains words like 'show' in the heading.")


# -------------------------------------------------
# REGIONAL / VENUE ANALYSIS
# -------------------------------------------------
st.markdown('<div class="section-title">🌍 Regional, Metro and Venue Review</div>', unsafe_allow_html=True)

area_source = None

if "Venue Area" in df.columns:
    area_source = "Venue Area"
elif "Area Type" in df.columns:
    area_source = "Area Type"

if area_source:
    area_counts = df[area_source].dropna().astype(str).value_counts().reset_index()
    area_counts.columns = [area_source, "Count"]

    a1, a2 = st.columns([2, 1])

    with a1:
        fig_area = px.pie(
            area_counts,
            names=area_source,
            values="Count",
            title="Regional / Metro / Area Distribution"
        )
        st.plotly_chart(fig_area, use_container_width=True, key="area_distribution_chart")

    with a2:
        st.dataframe(area_counts, use_container_width=True)
else:
    st.info("No regional/metro classification detected yet. Upload venue reference data or postcode/location data.")


if "Matched Venue" in df.columns:
    venue_counts = df["Matched Venue"].dropna().astype(str).value_counts().reset_index()
    venue_counts.columns = ["Matched Venue", "Count"]

    fig_venue = px.bar(
        venue_counts.head(20),
        x="Matched Venue",
        y="Count",
        title="Top Matched Venues",
        text="Count"
    )
    fig_venue.update_layout(xaxis_tickangle=-35)
    st.plotly_chart(fig_venue, use_container_width=True, key="matched_venue_chart")


# -------------------------------------------------
# CITY / STATE REVIEW
# -------------------------------------------------
st.markdown('<div class="section-title">🏙️ City and State Review</div>', unsafe_allow_html=True)

g1, g2 = st.columns(2)

with g1:
    if "Estimated City" in df.columns:
        city_counts = df["Estimated City"].dropna().astype(str).value_counts().head(15).reset_index()
        city_counts.columns = ["Estimated City", "Count"]

        fig_city = px.bar(
            city_counts,
            x="Estimated City",
            y="Count",
            title="Top Estimated Cities / Regions",
            text="Count"
        )
        fig_city.update_layout(xaxis_tickangle=-35)
        st.plotly_chart(fig_city, use_container_width=True, key="city_review_chart")
    else:
        st.info("No estimated city data available.")

with g2:
    if "Australian State" in df.columns:
        state_counts = df["Australian State"].dropna().astype(str).value_counts().reset_index()
        state_counts.columns = ["Australian State", "Count"]

        fig_state = px.pie(
            state_counts,
            names="Australian State",
            values="Count",
            title="Australian State Distribution"
        )
        st.plotly_chart(fig_state, use_container_width=True, key="state_review_chart")
    else:
        st.info("No Australian state data available.")


# -------------------------------------------------
# AUTO CHARTS FOR ANY DATA
# -------------------------------------------------
st.markdown('<div class="section-title">📈 Automatic Charts from This Dataset</div>', unsafe_allow_html=True)

categorical_cols = [
    col for col in df.columns
    if df[col].dtype == "object" and df[col].nunique(dropna=True) > 1 and df[col].nunique(dropna=True) <= 30
]

if categorical_cols:
    selected_cat = st.selectbox("Choose a categorical field to chart", categorical_cols)

    cat_counts = df[selected_cat].dropna().astype(str).value_counts().head(20).reset_index()
    cat_counts.columns = [selected_cat, "Count"]

    fig_cat = px.bar(
        cat_counts,
        x=selected_cat,
        y="Count",
        title=f"Distribution of {selected_cat}",
        text="Count"
    )
    fig_cat.update_layout(xaxis_tickangle=-35)
    st.plotly_chart(fig_cat, use_container_width=True, key="automatic_category_chart")
else:
    st.info("No suitable categorical columns found for automatic charting.")

if numeric_cols:
    selected_num = st.selectbox("Choose a numeric field to review", numeric_cols)

    fig_num = px.histogram(
        df,
        x=selected_num,
        title=f"Distribution of {selected_num}"
    )
    st.plotly_chart(fig_num, use_container_width=True, key="automatic_numeric_chart")


# -------------------------------------------------
# DOWNLOAD
# -------------------------------------------------
st.markdown('<div class="section-title">⬇️ Download Reviewed Data</div>', unsafe_allow_html=True)

download_choice = st.selectbox(
    "Choose what to download",
    [
        "Reviewed Dataset",
        "Data Summary",
        "Show Summary",
        "Regional / Metro Summary",
        "City / State Summary"
    ]
)

from lib.floating_assistant import render_floating_ai_assistant
render_floating_ai_assistant()


if download_choice == "Reviewed Dataset":
    download_df = df

elif download_choice == "Data Summary":
    download_df = pd.DataFrame({
        "Metric": ["Dataset", "Rows", "Columns", "Missing Values", "Numeric Columns", "Text Columns"],
        "Value": [selected_dataset, df.shape[0], df.shape[1], missing_values, len(numeric_cols), len(text_cols)]
    })

elif download_choice == "Show Summary":
    if show_col:
        download_df = show_counts
    else:
        download_df = pd.DataFrame({"Message": ["No show column detected"]})

elif download_choice == "Regional / Metro Summary":
    if area_source:
        download_df = area_counts
    else:
        download_df = pd.DataFrame({"Message": ["No regional/metro column detected"]})

else:
    rows = []

    if "Estimated City" in df.columns:
        for value, count in df["Estimated City"].dropna().astype(str).value_counts().items():
            rows.append({"Category": "Estimated City", "Value": value, "Count": count})

    if "Australian State" in df.columns:
        for value, count in df["Australian State"].dropna().astype(str).value_counts().items():
            rows.append({"Category": "Australian State", "Value": value, "Count": count})

    download_df = pd.DataFrame(rows)

output = BytesIO()

with pd.ExcelWriter(output, engine="openpyxl") as writer:
    download_df.to_excel(writer, index=False, sheet_name="Data_Review")

st.download_button(
    "Download Selected Review",
    output.getvalue(),
    file_name="monkey_baa_data_review.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

st.caption(
    "Note: venue and postcode classifications are estimates based on available uploaded reference data."
)