import streamlit as st
import pandas as pd

from lib.data_store import (
    list_datasets,
    save_dataset,
    load_dataset,
    update_dataset,
    delete_dataset,
    update_notes,
    load_catalog,
    save_catalog,
)

from lib.style import inject_css, render_sidebar_nav, require_login

st.set_page_config(
    page_title="Monkey Baa - Data Library",
    page_icon="📚",
    layout="wide"
)

inject_css()
render_sidebar_nav()
require_login()

if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("Please login first from the Home page.")
    st.stop()


st.title("📚 Monkey Baa Data Library")
st.write(
    "Upload, manage, preview, clean and organise datasets used by the AI analysis system."
)


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


# -------------------------------------------------
# UPLOAD DATASET
# -------------------------------------------------
st.subheader("⬆️ Upload New Dataset")

uploaded_file = st.file_uploader(
    "Upload Excel or CSV file",
    type=["xlsx", "xls", "csv"]
)

dataset_name = st.text_input("Dataset name")
dataset_type = st.selectbox("Dataset type", DATASET_TYPES)
notes = st.text_area("Notes / description", placeholder="Optional notes about this dataset")

if uploaded_file is not None:
    try:
        if uploaded_file.name.lower().endswith(".csv"):
            df_upload = pd.read_csv(uploaded_file)
        else:
            df_upload = pd.read_excel(uploaded_file)

        st.success("File loaded successfully.")
        st.write("Preview:")
        st.dataframe(df_upload.head(20), use_container_width=True)

        if st.button("Save Dataset"):
            if not dataset_name.strip():
                st.error("Please enter a dataset name before saving.")
            else:
                save_dataset(
                    df_upload,
                    dataset_name.strip(),
                    dataset_type,
                    notes.strip()
                )
                st.success("Dataset saved successfully.")
                st.rerun()

    except Exception as e:
        st.error(f"Could not read uploaded file: {e}")


st.divider()


# -------------------------------------------------
# MANAGE SAVED DATASETS
# -------------------------------------------------
st.subheader("🗂️ Manage Saved Datasets")

datasets = list_datasets()

if not datasets:
    st.info("No saved datasets found yet.")
    st.stop()


# Remove broken records before displaying
cleaned_datasets = []

for item in datasets:
    filename = item.get("filename")

    if not filename:
        continue

    try:
        _ = load_dataset(filename)
        cleaned_datasets.append(item)

    except FileNotFoundError:
        st.warning(f"Missing file removed from Data Library: {filename}")
        continue

    except Exception as e:
        st.warning(f"Could not load {filename}: {e}")
        continue


if len(cleaned_datasets) != len(datasets):
    save_catalog(cleaned_datasets)
    datasets = cleaned_datasets


if not datasets:
    st.info("No valid datasets found. Please upload your files again.")
    st.stop()


dataset_labels = [
    f"{item.get('dataset_name', 'Unnamed')} | {item.get('dataset_type', 'Unknown')} | {item.get('filename', '')}"
    for item in datasets
]

selected_label = st.selectbox("Select dataset", dataset_labels)

selected_index = dataset_labels.index(selected_label)
selected_item = datasets[selected_index]

filename = selected_item.get("filename")


try:
    df = load_dataset(filename)

except FileNotFoundError:
    st.error(f"File missing: {filename}. This record will be removed.")
    catalog = load_catalog()
    catalog = [item for item in catalog if item.get("filename") != filename]
    save_catalog(catalog)
    st.rerun()

except Exception as e:
    st.error(f"Could not load dataset: {e}")
    st.stop()


# -------------------------------------------------
# DATASET DETAILS
# -------------------------------------------------
st.markdown("### Dataset Details")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Dataset Name", selected_item.get("dataset_name", ""))
col2.metric("Dataset Type", selected_item.get("dataset_type", ""))
col3.metric("Rows", df.shape[0])
col4.metric("Columns", df.shape[1])

st.write("**Filename:**", filename)
st.write("**Uploaded at:**", selected_item.get("uploaded_at", ""))


# -------------------------------------------------
# NOTES
# -------------------------------------------------
st.markdown("### 📝 Notes")

new_notes = st.text_area(
    "Edit notes",
    value=selected_item.get("notes", ""),
    key=f"notes_{filename}"
)

if st.button("Update Notes"):
    update_notes(filename, new_notes)
    st.success("Notes updated.")
    st.rerun()


# -------------------------------------------------
# PREVIEW DATA
# -------------------------------------------------
st.markdown("### 👀 Preview Dataset")

st.dataframe(df, use_container_width=True)


# -------------------------------------------------
# BASIC CLEANING
# -------------------------------------------------
st.markdown("### 🧹 Basic Cleaning Options")

clean_df = df.copy()

if st.button("Remove Empty Rows"):
    clean_df = clean_df.dropna(how="all")
    update_dataset(filename, clean_df)
    st.success("Empty rows removed.")
    st.rerun()

if st.button("Remove Duplicate Rows"):
    clean_df = clean_df.drop_duplicates()
    update_dataset(filename, clean_df)
    st.success("Duplicate rows removed.")
    st.rerun()


# -------------------------------------------------
# DOWNLOAD DATASET
# -------------------------------------------------
st.markdown("### ⬇️ Download Dataset")

csv_data = df.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Download as CSV",
    data=csv_data,
    file_name=f"{selected_item.get('dataset_name', 'dataset')}.csv",
    mime="text/csv"
)


# -------------------------------------------------
# DELETE DATASET
# -------------------------------------------------
st.markdown("### 🗑️ Delete Dataset")

delete_confirm = st.checkbox(
    f"I confirm I want to delete {selected_item.get('dataset_name', '')}"
)

if delete_confirm:
    if st.button("Delete Dataset"):
        delete_dataset(filename)
        st.success("Dataset deleted.")
        st.rerun()