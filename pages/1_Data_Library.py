import streamlit as st
import pandas as pd
from io import BytesIO

from lib.smart_reader import read_uploaded_file, clean_dataset
from lib.data_store import (
    save_dataset,
    list_datasets,
    load_dataset,
    update_dataset,
    delete_dataset,
    update_notes
)
from lib.insights import generate_dataset_summary
from lib.venue_matcher import add_venue_area_to_survey

st.set_page_config(page_title="Data Library", page_icon="📁", layout="wide")

if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("Please login first from the Home page.")
    st.stop()

st.title("📁 Monkey Baa Data Library")

st.markdown("""
Upload, clean, store and manage Monkey Baa datasets.  
This page accepts Excel, CSV, JSON and TXT files.  
You can search, filter, edit, download and match venue/regional data.
""")

tab_upload, tab_manage = st.tabs(["Upload New Data", "Manage Existing Data"])

with tab_upload:
    uploaded_file = st.file_uploader(
        "Upload Excel, CSV, JSON or TXT data",
        type=["xlsx", "xls", "csv", "json", "txt"]
    )

    if uploaded_file:
        try:
            raw_df = read_uploaded_file(uploaded_file)
            cleaned_df = clean_dataset(raw_df)

            st.subheader("Preview")
            st.dataframe(cleaned_df.head(30), use_container_width=True)

            summary = generate_dataset_summary(cleaned_df)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Rows", summary["rows"])
            c2.metric("Columns", summary["columns"])
            c3.metric("Missing Values", summary["missing_values"])
            c4.metric("Duplicate Rows", summary["duplicate_rows"])

            dataset_name = st.text_input("Dataset name", value=uploaded_file.name)

            dataset_type = st.selectbox(
                "Dataset type",
                [
                    "Survey Data",
                    "Dashboard Data",
                    "Performance Information",
                    "Audience Data",
                    "Financial Data",
                    "Venue Reference Data",
                    "Framework Dictionary",
                    "Theory of Change",
                    "Other"
                ]
            )

            notes = st.text_area("Dataset notes")

            if st.button("Save Dataset to Library"):
                save_dataset(cleaned_df, dataset_name, dataset_type, notes)
                st.success("Dataset saved successfully.")
                st.rerun()

        except Exception as e:
            st.error(f"Could not read this file: {e}")

with tab_manage:
    datasets = list_datasets()

    if not datasets:
        st.info("No datasets saved yet.")
        st.stop()

    catalog_df = pd.DataFrame(datasets)

    st.subheader("Saved Datasets")
    st.dataframe(catalog_df, use_container_width=True)

    selected_name = st.selectbox(
        "Select dataset",
        [item["dataset_name"] for item in datasets]
    )

    selected = next(item for item in datasets if item["dataset_name"] == selected_name)
    filename = selected["filename"]
    df = load_dataset(filename)

    c1, c2, c3 = st.columns(3)
    c1.metric("Type", selected["dataset_type"])
    c2.metric("Rows", selected["rows"])
    c3.metric("Columns", selected["columns"])

    notes = st.text_area("Notes", value=selected.get("notes", ""))

    if st.button("Update Notes"):
        update_notes(filename, notes)
        st.success("Notes updated.")
        st.rerun()

    st.subheader("🔎 Search and Filter Dataset")

    filtered_df = df.copy()

    search_word = st.text_input(
        "Search inside data",
        placeholder="Type a word, venue, show name, year, postcode..."
    )

    if search_word:
        mask = filtered_df.astype(str).apply(
            lambda row: row.str.contains(search_word, case=False, na=False).any(),
            axis=1
        )
        filtered_df = filtered_df[mask]

    filter_col = st.selectbox(
        "Filter by column",
        ["No column filter"] + list(df.columns)
    )

    if filter_col != "No column filter":
        unique_values = (
            df[filter_col]
            .dropna()
            .astype(str)
            .sort_values()
            .unique()
            .tolist()
        )

        selected_values = st.multiselect(
            f"Select value(s) from {filter_col}",
            unique_values
        )

        if selected_values:
            filtered_df = filtered_df[
                filtered_df[filter_col].astype(str).isin(selected_values)
            ]

    st.write(f"Showing **{len(filtered_df)}** of **{len(df)}** rows.")

    st.subheader("Venue / Regional Matching")

    st.write("""
    Use this when you have uploaded:
    - Survey file with **Where did you see the show?**
    - Dashboard Project file with venue and regional/location information
    """)

    if st.button("Match Venue and Regional Area"):
        catalog = list_datasets()

        matched_df, message = add_venue_area_to_survey(
            df,
            catalog,
            load_dataset
        )

        update_dataset(filename, matched_df)
        st.success(message)
        st.rerun()

    st.subheader("Edit Dataset")

    edited_df = st.data_editor(
        filtered_df,
        use_container_width=True,
        num_rows="dynamic"
    )

    st.warning(
        "If you save changes while filters are active, only the filtered view is saved. "
        "Clear filters first if you want to edit the full dataset."
    )

    col_save, col_download, col_delete = st.columns(3)

    with col_save:
        if st.button("Save Current View Changes"):
            update_dataset(filename, edited_df)
            st.success("Dataset updated.")

    with col_download:
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            edited_df.to_excel(writer, index=False, sheet_name="Data")

        st.download_button(
            "Download Current View",
            output.getvalue(),
            file_name=f"{selected_name}_filtered.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    with col_delete:
        if st.button("Delete Dataset"):
            delete_dataset(filename)
            st.success("Dataset deleted.")
            st.rerun()

from lib.floating_assistant import render_floating_ai_assistant
render_floating_ai_assistant()