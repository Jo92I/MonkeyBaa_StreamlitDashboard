import pandas as pd
import json
from pathlib import Path
from datetime import datetime

DATA_DIR = Path("stored_data")
DATA_DIR.mkdir(exist_ok=True)

CATALOG_FILE = DATA_DIR / "data_catalog.json"


def load_catalog():
    if not CATALOG_FILE.exists():
        CATALOG_FILE.write_text("[]")
    return json.loads(CATALOG_FILE.read_text())


def save_catalog(catalog):
    CATALOG_FILE.write_text(json.dumps(catalog, indent=4))


def save_dataset(df, dataset_name, dataset_type, notes=""):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = dataset_name.replace(" ", "_").replace("/", "_")
    filename = f"{timestamp}_{safe_name}.xlsx"
    filepath = DATA_DIR / filename

    df.to_excel(filepath, index=False)

    catalog = load_catalog()
    catalog.append({
        "dataset_name": dataset_name,
        "dataset_type": dataset_type,
        "filename": filename,
        "uploaded_at": timestamp,
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "notes": notes
    })
    save_catalog(catalog)


def list_datasets():
    return load_catalog()


def load_dataset(filename):
    return pd.read_excel(DATA_DIR / filename)


def update_dataset(filename, df):
    df.to_excel(DATA_DIR / filename, index=False)


def delete_dataset(filename):
    filepath = DATA_DIR / filename

    if filepath.exists():
        filepath.unlink()

    catalog = load_catalog()
    catalog = [item for item in catalog if item["filename"] != filename]
    save_catalog(catalog)


def update_notes(filename, notes):
    catalog = load_catalog()

    for item in catalog:
        if item["filename"] == filename:
            item["notes"] = notes

    save_catalog(catalog)


def load_all_data():
    catalog = load_catalog()
    frames = []

    for item in catalog:
        df = load_dataset(item["filename"])
        df["Dataset Name"] = item["dataset_name"]
        df["Dataset Type"] = item["dataset_type"]
        frames.append(df)

    if frames:
        return pd.concat(frames, ignore_index=True, sort=False)

    return pd.DataFrame()