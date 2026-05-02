import re
from collections import Counter

import pandas as pd
import plotly.express as px
import streamlit as st

from lib.data_store import list_datasets, load_dataset

st.set_page_config(
    page_title="Monkey Baa Impact Dashboard",
    page_icon="🎭",
    layout="wide"
)

st.markdown("""
<style>
.block-container {
    padding-top: 2rem;
}

.hero-card {
    background: linear-gradient(135deg, #31124d, #7b2cbf);
    padding: 30px;
    border-radius: 24px;
    color: white;
    margin-bottom: 28px;
}

.hero-title {
    font-size: 34px;
    font-weight: 800;
    margin-bottom: 8px;
}

.hero-subtitle {
    font-size: 17px;
    opacity: 0.92;
}

.metric-card {
    background: white;
    padding: 22px;
    border-radius: 18px;
    box-shadow: 0 4px 14px rgba(0,0,0,0.08);
    text-align: center;
    border: 1px solid #eee;
}

.metric-number {
    font-size: 30px;
    font-weight: 800;
    color: #3b1c59;
}

.metric-label {
    font-size: 14px;
    color: #555;
}

.section-card {
    background: white;
    padding: 24px;
    border-radius: 20px;
    box-shadow: 0 4px 14px rgba(0,0,0,0.08);
    margin-bottom: 22px;
    border: 1px solid #eee;
}

.okr-box {
    background: #f2e8ff;
    border-left: 6px solid #7b2cbf;
    padding: 18px;
    border-radius: 14px;
    margin-bottom: 12px;
}

.small-muted {
    color: #666;
    font-size: 14px;
}
</style>
""", unsafe_allow_html=True)


POSITIVE_WORDS = [
    "good", "great", "excellent", "amazing", "fun", "enjoyed", "enjoy",
    "love", "loved", "happy", "engaging", "creative", "inspiring",
    "wonderful", "positive", "interesting", "helpful", "excited",
    "beautiful", "fantastic", "brilliant"
]

NEGATIVE_WORDS = [
    "bad", "poor", "boring", "confusing", "difficult", "hard", "negative",
    "disappointed", "issue", "problem", "slow", "unclear", "tired",
    "lack", "limited", "noisy", "expensive"
]

THEME_KEYWORDS = {
    "Engagement": ["engaged", "engaging", "fun", "enjoy", "interactive", "interest", "attention"],
    "Learning": ["learn", "learning", "understand", "education", "school", "student", "teacher"],
    "Creativity": ["creative", "creativity", "imagination", "art", "performance", "story", "play"],
    "Accessibility": ["access", "accessible", "inclusive", "support", "easy", "difficult", "barrier"],
    "Emotional Impact": ["feel", "feeling", "happy", "excited", "confident", "inspired", "emotion"],
}


def clean_text(value):
    if pd.isna(value):
        return ""
    value = str(value).lower()
    value = value.replace("â€™", "'").replace("’", "'")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def tokenize(text):
    text = clean_text(text)
    words = re.findall(r"\b[a-zA-Z]{3,}\b", text)

    stopwords = {
        "the", "and", "for", "that", "this", "with", "was", "were", "are",
        "you", "they", "have", "has", "from", "but", "all", "our", "their",
        "there", "about", "very", "into", "also", "when", "what", "your",
        "will", "been", "would", "could", "should"
    }

    return [w for w in words if w not in stopwords]


def detect_sentiment(text):
    words = tokenize(text)

    if not words:
        return "Neutral"

    positive = sum(1 for word in words if word in POSITIVE_WORDS)
    negative = sum(1 for word in words if word in NEGATIVE_WORDS)

    if positive > negative:
        return "Positive"
    if negative > positive:
        return "Negative"
    return "Neutral"


def detect_themes(text):
    words = tokenize(text)
    found = []

    for theme, keywords in THEME_KEYWORDS.items():
        if any(keyword in words for keyword in keywords):
            found.append(theme)

    return ", ".join(found) if found else "General Feedback"


def detect_text_columns(df):
    text_cols = []

    for col in df.columns:
        sample = df[col].dropna().astype(str).head(50)
        if sample.empty:
            continue

        average_length = sample.str.len().mean()
        unique_ratio = df[col].astype(str).nunique() / max(len(df), 1)

        if average_length > 8 or unique_ratio > 0.25:
            text_cols.append(col)

    return text_cols


def find_possible_column(df, keywords):
    for col in df.columns:
        col_lower = str(col).lower()
        if any(keyword in col_lower for keyword in keywords):
            return col
    return None


def apply_filters(df):
    filtered_df = df.copy()

    year_col = find_possible_column(df, ["year", "date"])
    show_col = find_possible_column(df, ["show", "production", "performance", "event", "program"])
    region_col = find_possible_column(df, ["region", "location", "venue", "metro", "regional", "area"])

    st.sidebar.title("Dashboard Filters")

    if year_col:
        if "date" in str(year_col).lower():
            filtered_df[year_col] = pd.to_datetime(filtered_df[year_col], errors="coerce")
            years = sorted(filtered_df[year_col].dt.year.dropna().unique())
        else:
            years = sorted(filtered_df[year_col].dropna().astype(str).unique())

        selected_years = st.sidebar.multiselect("Year", years, default=years)

        if selected_years:
            if "date" in str(year_col).lower():
                filtered_df = filtered_df[filtered_df[year_col].dt.year.isin(selected_years)]
            else:
                filtered_df = filtered_df[filtered_df[year_col].astype(str).isin(selected_years)]

    if show_col:
        shows = sorted(filtered_df[show_col].dropna().astype(str).unique())
        selected_shows = st.sidebar.multiselect("Show / Program", shows, default=shows)

        if selected_shows:
            filtered_df = filtered_df[filtered_df[show_col].astype(str).isin(selected_shows)]

    if region_col:
        regions = sorted(filtered_df[region_col].dropna().astype(str).unique())
        selected_regions = st.sidebar.multiselect("Region / Venue", regions, default=regions)

        if selected_regions:
            filtered_df = filtered_df[filtered_df[region_col].astype(str).isin(selected_regions)]

    return filtered_df, year_col, show_col, region_col


def analyse_text(df, selected_cols):
    all_responses = []

    for col in selected_cols:
        for value in df[col].dropna().astype(str):
            if value.strip():
                all_responses.append({
                    "column": col,
                    "response": value,
                    "sentiment": detect_sentiment(value),
                    "themes": detect_themes(value),
                })

    response_df = pd.DataFrame(all_responses)

    all_words = []
    for response in response_df["response"].tolist() if not response_df.empty else []:
        all_words.extend(tokenize(response))

    word_df = pd.DataFrame(
        Counter(all_words).most_common(30),
        columns=["word", "count"]
    )

    if response_df.empty:
        sentiment_df = pd.DataFrame(columns=["sentiment", "count"])
        theme_df = pd.DataFrame(columns=["theme", "count"])
    else:
        sentiment_df = response_df["sentiment"].value_counts().reset_index()
        sentiment_df.columns = ["sentiment", "count"]

        theme_df = response_df["themes"].value_counts().reset_index()
        theme_df.columns = ["theme", "count"]

    return word_df, sentiment_df, theme_df, response_df


def okr_theme_connection(theme_df):
    okr_map = {
        "Engagement": "OKR Analysis: Audience and student engagement outcomes",
        "Learning": "OKR Analysis: Educational value and learning development",
        "Creativity": "OKR Analysis: Creativity, imagination and artistic participation",
        "Accessibility": "OKR Analysis: Inclusion, access and regional reach",
        "Emotional Impact": "OKR Analysis: Confidence, belonging and social impact",
        "General Feedback": "OKR Analysis: General service quality and audience experience",
    }

    rows = []

    for _, row in theme_df.iterrows():
        theme = row["theme"]
        count = row["count"]

        for single_theme in str(theme).split(","):
            single_theme = single_theme.strip()

            rows.append({
                "Detected Theme": single_theme,
                "Mentions": count,
                "Linked OKR / Impact Area": okr_map.get(
                    single_theme,
                    "OKR Analysis: General feedback and service quality"
                )
            })

    return pd.DataFrame(rows)


st.markdown("""
<div class="hero-card">
    <div class="hero-title">🎭 Monkey Baa Impact Analytics Dashboard</div>
    <div class="hero-subtitle">
        Transforming cleaned survey comments, feedback and program data into structured, visual and evidence-based insights.
    </div>
</div>
""", unsafe_allow_html=True)

if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("Please login first from the Home page.")
    st.stop()

datasets = list_datasets()

if not datasets:
    st.warning("No cleaned datasets found. Please upload and save data in the Data Library first.")
    st.stop()

dataset_options = [
    item for item in datasets
    if item.get("dataset_type") in [
        "Survey Data",
        "Dashboard Data",
        "Performance Information",
        "Audience Data",
        "Venue Reference Data",
        "Other"
    ]
]

if not dataset_options:
    dataset_options = datasets

selected_dataset_name = st.sidebar.selectbox(
    "Select cleaned dataset",
    [item["dataset_name"] for item in dataset_options]
)

selected_dataset = next(
    item for item in dataset_options
    if item["dataset_name"] == selected_dataset_name
)

df = load_dataset(selected_dataset["filename"])

filtered_df, year_col, show_col, region_col = apply_filters(df)

if filtered_df.empty:
    st.warning("No data matches your selected filters.")
    st.stop()

text_cols = detect_text_columns(filtered_df)
numeric_cols = filtered_df.select_dtypes(include=["int64", "float64"]).columns.tolist()

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-number">{len(filtered_df)}</div>
        <div class="metric-label">Filtered Records</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-number">{len(text_cols)}</div>
        <div class="metric-label">Text Columns</div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-number">{len(numeric_cols)}</div>
        <div class="metric-label">Numeric Columns</div>
    </div>
    """, unsafe_allow_html=True)

with c4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-number">{len(filtered_df.columns)}</div>
        <div class="metric-label">Total Columns</div>
    </div>
    """, unsafe_allow_html=True)

st.write("")

st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.subheader("Select Text Columns for Analysis")

selected_text_cols = st.multiselect(
    "Choose comment, feedback, reflection or survey response columns.",
    text_cols,
    default=text_cols[:3]
)

st.markdown("</div>", unsafe_allow_html=True)

if not selected_text_cols:
    st.warning("Please select at least one text column.")
    st.stop()

word_df, sentiment_df, theme_df, response_df = analyse_text(filtered_df, selected_text_cols)

left, right = st.columns([1.2, 1])

with left:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("Most Common Words")

    if not word_df.empty:
        fig_words = px.bar(
            word_df,
            x="count",
            y="word",
            orientation="h",
            title="Top Words in Feedback"
        )
        fig_words.update_layout(
            height=520,
            yaxis={"categoryorder": "total ascending"},
            margin=dict(l=20, r=20, t=50, b=20)
        )
        st.plotly_chart(fig_words, use_container_width=True)
    else:
        st.info("No words found.")

    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("Sentiment Distribution")

    if not sentiment_df.empty:
        fig_sentiment = px.pie(
            sentiment_df,
            names="sentiment",
            values="count",
            hole=0.45,
            title="Feedback Sentiment"
        )
        fig_sentiment.update_layout(height=360)
        st.plotly_chart(fig_sentiment, use_container_width=True)
    else:
        st.info("No sentiment data available.")

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("Theme Detection")

    if not theme_df.empty:
        fig_themes = px.bar(
            theme_df,
            x="theme",
            y="count",
            title="Detected Feedback Themes"
        )
        fig_themes.update_layout(height=320)
        st.plotly_chart(fig_themes, use_container_width=True)
    else:
        st.info("No themes detected.")

    st.markdown("</div>", unsafe_allow_html=True)


st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.subheader("Filtered Data Overview")

if show_col:
    show_summary = filtered_df[show_col].astype(str).value_counts().head(10).reset_index()
    show_summary.columns = ["Show / Program", "Count"]

    fig_show = px.bar(
        show_summary,
        x="Show / Program",
        y="Count",
        title="Top Shows / Programs"
    )
    st.plotly_chart(fig_show, use_container_width=True)

if region_col:
    region_summary = filtered_df[region_col].astype(str).value_counts().reset_index()
    region_summary.columns = ["Region / Venue", "Count"]

    fig_region = px.pie(
        region_summary,
        names="Region / Venue",
        values="Count",
        title="Region / Venue Distribution"
    )
    st.plotly_chart(fig_region, use_container_width=True)

st.markdown("</div>", unsafe_allow_html=True)


st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.subheader("Visual Connection to OKR Analysis")

st.write("""
The dashboard prepares the qualitative evidence that supports the OKR Analysis page.  
Themes detected from comments can be linked to impact areas such as engagement, learning, creativity, accessibility and emotional impact.
""")

if not theme_df.empty:
    okr_df = okr_theme_connection(theme_df)

    for _, row in okr_df.iterrows():
        st.markdown(f"""
        <div class="okr-box">
            <strong>{row["Detected Theme"]}</strong><br>
            <span class="small-muted">Mentions: {row["Mentions"]}</span><br><br>
            {row["Linked OKR / Impact Area"]}
        </div>
        """, unsafe_allow_html=True)

    st.dataframe(okr_df, use_container_width=True)

st.info("Next step: open the OKR Analysis page to compare these themes with KPI/OKR performance results.")

st.markdown("</div>", unsafe_allow_html=True)


st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.subheader("Sample Text Analysis")

if not response_df.empty:
    st.dataframe(response_df.head(50), use_container_width=True)
else:
    st.info("No text responses available.")

st.markdown("</div>", unsafe_allow_html=True)


st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.subheader("Clear Data-Driven Interpretation")

positive = sentiment_df[sentiment_df["sentiment"] == "Positive"]["count"].sum() if "Positive" in sentiment_df["sentiment"].values else 0
negative = sentiment_df[sentiment_df["sentiment"] == "Negative"]["count"].sum() if "Negative" in sentiment_df["sentiment"].values else 0
neutral = sentiment_df[sentiment_df["sentiment"] == "Neutral"]["count"].sum() if "Neutral" in sentiment_df["sentiment"].values else 0

if positive > negative:
    st.success("The selected data shows stronger positive feedback than negative feedback.")
elif negative > positive:
    st.error("The selected data shows stronger negative feedback than positive feedback.")
else:
    st.info("The selected data shows a balanced or mostly neutral feedback pattern.")

st.write(f"""
Based on the selected cleaned dataset and filters:

- **Positive responses:** {positive}
- **Negative responses:** {negative}
- **Neutral responses:** {neutral}
- **Most common words:** used to identify repeated audience or teacher concerns
- **Detected themes:** used to connect qualitative feedback with impact reporting
- **OKR link:** themes can support the OKR Analysis page by explaining why certain outcomes are strong or weak
""")

st.markdown("</div>", unsafe_allow_html=True)