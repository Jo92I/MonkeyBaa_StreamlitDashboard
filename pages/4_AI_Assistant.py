import streamlit as st
import pandas as pd

from lib.data_store import load_all_data, list_datasets, load_dataset
from lib.insights import theory_of_change_insights, detect_show_column, detect_date_column
from lib.geo_australia import add_geographic_insights
from lib.venue_matcher import add_venue_area_to_survey

st.set_page_config(page_title="AI Assistant", page_icon="🤖", layout="wide")

if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("Please login first from the Home page.")
    st.stop()

st.title("🤖 Monkey Baa AI Assistant")

st.write("""
Ask me about uploaded datasets, shows, years, venues, cities, regional reach or Theory of Change insights.
""")

df = load_all_data()
catalog = list_datasets()

if not df.empty:
    df = add_geographic_insights(df)
    df, venue_message = add_venue_area_to_survey(df, catalog, load_dataset)
else:
    venue_message = "No data uploaded yet."

datasets = list_datasets()

if "assistant_messages" not in st.session_state:
    st.session_state.assistant_messages = [
        {
            "role": "assistant",
            "content": "Hello! I can help you understand Monkey Baa data, venues, regions, shows and Theory of Change insights."
        }
    ]


def assistant_answer(question):
    q = question.lower()

    if df.empty:
        return """
No saved data has been uploaded yet.

Please go to **Data Library**, upload the survey file and Dashboard Project file, then save them.
"""

    if "venue" in q or "where did you see" in q or "regional" in q:
        if "Venue Area" not in df.columns:
            return """
I cannot see venue-area matching yet.

Please make sure:
1. The Dashboard Project file is uploaded.
2. The survey file is uploaded.
3. The survey file has **Where did you see the show?**.
4. The Dashboard Project file has a venue column and area/regional column.
"""

        areas = df["Venue Area"].dropna().astype(str).value_counts()

        return "Venue area summary:\n\n" + "\n".join(
            [f"- **{area}**: {count} records" for area, count in areas.items()]
        )

    if "matched" in q:
        if "Matched Venue" not in df.columns:
            return "No matched venue column found yet."

        venues = df["Matched Venue"].dropna().astype(str).value_counts().head(10)

        return "Top matched venues:\n\n" + "\n".join(
            [f"- **{venue}**: {count} records" for venue, count in venues.items()]
        )

    if "dataset" in q or "uploaded" in q or "file" in q:
        names = [item["dataset_name"] for item in datasets]

        return f"""
There are currently **{len(datasets)} saved datasets**.

The combined data contains:
- **{df.shape[0]} rows**
- **{df.shape[1]} columns**

Saved datasets:
{chr(10).join([f"- {name}" for name in names])}
"""

    if "city" in q or "cities" in q:
        if "Estimated City" not in df.columns:
            return "I could not detect postcode data, so I cannot estimate cities yet."

        cities = df["Estimated City"].dropna().astype(str).value_counts().head(10)

        return "Top estimated cities/regions:\n\n" + "\n".join(
            [f"- **{city}**: {count} records" for city, count in cities.items()]
        )

    if "state" in q:
        if "Australian State" not in df.columns:
            return "I could not detect postcode data, so I cannot estimate Australian states yet."

        states = df["Australian State"].dropna().astype(str).value_counts()

        return "Audience reach by Australian state:\n\n" + "\n".join(
            [f"- **{state}**: {count} records" for state, count in states.items()]
        )

    if "download" in q:
        return """
To download dashboard information:

1. Open **AI Dashboard**
2. Scroll to **Download Dashboard Information**
3. Choose the type of export
4. Click **Download Selected Information**
"""

    if "show" in q:
        show_col = detect_show_column(df)

        if not show_col:
            return "I could not detect a show column yet."

        shows = df[show_col].dropna().astype(str).value_counts().head(10)

        return "Top shows found:\n\n" + "\n".join(
            [f"- **{idx}**: {val} records/surveys" for idx, val in shows.items()]
        )

    if "year" in q:
        date_col = detect_date_column(df)

        if not date_col:
            return "I could not detect a date/year column yet."

        temp = df.copy()
        temp[date_col] = pd.to_datetime(temp[date_col], errors="coerce")
        years = temp[date_col].dt.year.dropna().astype(int).value_counts().sort_index()

        if years.empty:
            return "I found a date column, but I could not convert it into years."

        return "Data by year:\n\n" + "\n".join(
            [f"- **{year}**: {count} records" for year, count in years.items()]
        )

    if "theory" in q or "kpi" in q or "impact" in q or "insight" in q:
        toc = theory_of_change_insights(df)

        response = "Here are the current Theory of Change insights:\n"

        for area, info in toc.items():
            response += f"\n\n### {info['icon']} {area}\n"

            if info["results"]:
                for indicator, result in info["results"].items():
                    response += f"- **{indicator}**: {result}\n"
            else:
                response += "- No matching indicators found yet.\n"

        return response

    return """
I can help with:
- uploaded datasets
- shows
- years
- venues
- venue area
- cities
- Australian states
- Theory of Change insights
- dashboard downloads

Try asking: **What venue areas are in the data?**
"""


for message in st.session_state.assistant_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

user_question = st.chat_input("Ask the Monkey Baa assistant...")

if user_question:
    st.session_state.assistant_messages.append(
        {"role": "user", "content": user_question}
    )

    with st.chat_message("user"):
        st.markdown(user_question)

    answer = assistant_answer(user_question)

    st.session_state.assistant_messages.append(
        {"role": "assistant", "content": answer}
    )

    with st.chat_message("assistant"):
        st.markdown(answer)

from lib.floating_assistant import render_floating_ai_assistant
render_floating_ai_assistant()