import pandas as pd


def read_uploaded_file(uploaded_file):
    name = uploaded_file.name.lower()

    if name.endswith(".csv"):
        return pd.read_csv(uploaded_file)

    if name.endswith(".xlsx") or name.endswith(".xls"):
        return pd.read_excel(uploaded_file)

    if name.endswith(".json"):
        return pd.read_json(uploaded_file)

    if name.endswith(".txt"):
        text = uploaded_file.read().decode("utf-8", errors="ignore")
        return pd.DataFrame({"text": text.splitlines()})

    raise ValueError("Unsupported file type. Please upload CSV, Excel, JSON or TXT.")


def clean_dataset(df):
    cleaned = df.copy()

    # Keeps real data. Only removes fully empty rows/columns.
    cleaned = cleaned.dropna(how="all")
    cleaned = cleaned.dropna(axis=1, how="all")

    # Cleans column titles only.
    cleaned.columns = (
        cleaned.columns.astype(str)
        .str.strip()
        .str.replace("\n", " ", regex=False)
        .str.replace("  ", " ", regex=False)
    )

    return cleaned