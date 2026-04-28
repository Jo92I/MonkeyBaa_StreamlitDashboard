import pandas as pd
from lib.data_store import list_datasets, load_dataset


def load_single_source_of_truth():
    datasets = list_datasets()

    ssot = {
        "survey_data": [],
        "okr_frameworks": [],
        "dashboard_data": [],
        "theory_of_change": [],
        "all_datasets": datasets
    }

    for item in datasets:
        dtype = item.get("dataset_type", "")
        name = item.get("dataset_name", "")

        try:
            df = load_dataset(item["filename"])
        except Exception:
            continue

        record = {
            "name": name,
            "type": dtype,
            "data": df,
            "notes": item.get("notes", "")
        }

        if dtype == "Survey Data":
            ssot["survey_data"].append(record)
        elif dtype == "Framework Dictionary":
            ssot["okr_frameworks"].append(record)
        elif dtype in ["Dashboard Data", "Performance Information", "Audience Data"]:
            ssot["dashboard_data"].append(record)
        elif dtype == "Theory of Change":
            ssot["theory_of_change"].append(record)

    return ssot


def ssot_summary_text(ssot):
    lines = []

    lines.append("Single Source of Truth Summary:")
    lines.append(f"Survey datasets: {len(ssot['survey_data'])}")
    lines.append(f"OKR frameworks: {len(ssot['okr_frameworks'])}")
    lines.append(f"Dashboard/performance datasets: {len(ssot['dashboard_data'])}")
    lines.append(f"Theory of Change documents: {len(ssot['theory_of_change'])}")

    for group in ["survey_data", "okr_frameworks", "dashboard_data", "theory_of_change"]:
        for item in ssot[group]:
            df = item["data"]
            lines.append(
                f"- {item['name']} ({item['type']}): {df.shape[0]} rows, {df.shape[1]} columns"
            )

    return "\n".join(lines)