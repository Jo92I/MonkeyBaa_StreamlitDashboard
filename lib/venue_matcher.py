import pandas as pd
import re
from difflib import SequenceMatcher


def normalise_text(value):
    if pd.isna(value):
        return ""

    text = str(value).lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text


def find_column(df, keywords):
    for col in df.columns:
        lower = str(col).lower()
        if any(keyword in lower for keyword in keywords):
            return col
    return None


def find_venue_reference_dataset(catalog, load_dataset_function):
    for item in catalog:
        dataset_type = str(item.get("dataset_type", "")).lower()
        dataset_name = str(item.get("dataset_name", "")).lower()

        if (
            "dashboard" in dataset_type
            or "performance" in dataset_type
            or "venue" in dataset_name
            or "dashboard" in dataset_name
            or "performance" in dataset_name
        ):
            df = load_dataset_function(item["filename"])

            venue_col = find_column(df, ["venue"])
            regional_col = find_column(df, ["regional", "area", "region", "location type"])
            state_col = find_column(df, ["state"])

            if venue_col and regional_col:
                return df, venue_col, regional_col, state_col

    return None, None, None, None


def build_venue_lookup(reference_df, venue_col, regional_col, state_col=None):
    lookup = []

    for _, row in reference_df.iterrows():
        venue = row.get(venue_col)

        if pd.isna(venue):
            continue

        venue_text = normalise_text(venue)

        if not venue_text:
            continue

        lookup.append({
            "venue_original": str(venue),
            "venue_clean": venue_text,
            "regional_area": row.get(regional_col, "Unknown"),
            "state": row.get(state_col, "Unknown") if state_col else "Unknown"
        })

    return lookup


def match_venue(location_value, lookup, threshold=0.58):
    location_clean = normalise_text(location_value)

    if not location_clean:
        return {
            "Matched Venue": "Unknown",
            "Venue Area": "Unknown",
            "Venue State": "Unknown",
            "Venue Match Score": 0
        }

    best_match = None
    best_score = 0

    for item in lookup:
        venue_clean = item["venue_clean"]

        if venue_clean in location_clean or location_clean in venue_clean:
            score = 1.0
        else:
            score = SequenceMatcher(None, location_clean, venue_clean).ratio()

        if score > best_score:
            best_score = score
            best_match = item

    if best_match and best_score >= threshold:
        return {
            "Matched Venue": best_match["venue_original"],
            "Venue Area": best_match["regional_area"],
            "Venue State": best_match["state"],
            "Venue Match Score": round(best_score, 2)
        }

    return {
        "Matched Venue": "Unknown",
        "Venue Area": "Unknown",
        "Venue State": "Unknown",
        "Venue Match Score": round(best_score, 2)
    }


def add_venue_area_to_survey(survey_df, catalog, load_dataset_function):
    updated_df = survey_df.copy()

    location_col = find_column(
        updated_df,
        [
            "where did you see the show",
            "where",
            "venue",
            "location",
            "theatre"
        ]
    )

    if not location_col:
        return updated_df, "No survey venue/location column found."

    reference_df, venue_col, regional_col, state_col = find_venue_reference_dataset(
        catalog,
        load_dataset_function
    )

    if reference_df is None:
        return updated_df, "No venue reference dataset found. Upload the Dashboard Project file first."

    lookup = build_venue_lookup(reference_df, venue_col, regional_col, state_col)

    matched_rows = updated_df[location_col].apply(
        lambda value: match_venue(value, lookup)
    )

    matched_df = pd.DataFrame(list(matched_rows))

    for col in matched_df.columns:
        updated_df[col] = matched_df[col]

    return updated_df, "Venue matching completed."