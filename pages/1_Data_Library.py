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
from lib.style import inject_css, render_sidebar_nav

inject_css()
render_sidebar_nav()

from lib.insights import generate_dataset_summary
from lib.venue_matcher import add_venue_area_to_survey

st.set_page_config(page_title="Data Library", page_icon="📁", layout="wide")

if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("Please login first from the Home page.")
    st.stop()

st.title("📁 Monkey Baa Data Library")

st.markdown("""
Upload, clean, store and manage Monkey Baa datasets.  
This page accepts **Excel, CSV, JSON and TXT files**.  
Uploaded files are automatically cleaned before they are saved to the library.
""")

tab_upload, tab_manage = st.tabs(["Upload & Clean New Data", "Manage Existing Data"])


def cleaning_report(raw_df, cleaned_df):
    duplicate_count = raw_df.duplicated().sum()
    missing_before = raw_df.isna().sum().sum()
    missing_after = cleaned_df.isna().sum().sum()

    text_cols = cleaned_df.select_dtypes(include="object").columns.tolist()
    numeric_cols = cleaned_df.select_dtypes(include=["int64", "float64"]).columns.tolist()
    date_cols = cleaned_df.select_dtypes(include=["datetime64[ns]"]).columns.tolist()

    return {
        "raw_rows": len(raw_df),
        "cleaned_rows": len(cleaned_df),
        "raw_columns": len(raw_df.columns),
        "cleaned_columns": len(cleaned_df.columns),
        "duplicates_removed": duplicate_count,
        "missing_before": missing_before,
        "missing_after": missing_after,
        "text_columns": text_cols,
        "numeric_columns": numeric_cols,
        "date_columns": date_cols,
    }


with tab_upload:
    uploaded_file = st.file_uploader(
        "Upload Excel, CSV, JSON or TXT data",
        type=["xlsx", "xls", "csv", "json", "txt"]
    )

    if uploaded_file:
        try:
            raw_df = read_uploaded_file(uploaded_file)
            cleaned_df = clean_dataset(raw_df)

            report = cleaning_report(raw_df, cleaned_df)

            st.subheader("Cleaning Summary")

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Original Rows", report["raw_rows"])
            c2.metric("Cleaned Rows", report["cleaned_rows"])
            c3.metric("Columns", report["cleaned_columns"])
            c4.metric("Duplicates Removed", report["duplicates_removed"])

            c5, c6 = st.columns(2)
            c5.metric("Missing Values Before", report["missing_before"])
            c6.metric("Missing Values After", report["missing_after"])

            st.subheader("Detected Column Types")

            col_a, col_b, col_c = st.columns(3)

            with col_a:
                st.write("**Text Columns**")
                st.write(report["text_columns"])

            with col_b:
                st.write("**Numeric Columns**")
                st.write(report["numeric_columns"])

            with col_c:
                st.write("**Date Columns**")
                st.write(report["date_columns"])

            st.subheader("Cleaned Data Preview")
            st.dataframe(cleaned_df.head(30), use_container_width=True)

            summary = generate_dataset_summary(cleaned_df)

            st.subheader("Dataset Details")

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

            if st.button("Save Cleaned Dataset to Library"):
                save_dataset(cleaned_df, dataset_name, dataset_type, notes)
                st.success("Cleaned dataset saved successfully.")
                st.rerun()

        except Exception as e:
            st.error(f"Could not read or clean this file: {e}")


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