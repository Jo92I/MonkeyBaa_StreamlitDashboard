import re
import pandas as pd


def clean_postcode(value):
    if pd.isna(value):
        return None

    text = str(value).strip()

    match = re.search(r"\b\d{4}\b", text)

    if match:
        return match.group(0)

    return None


def postcode_to_state(postcode):
    if postcode is None or pd.isna(postcode):
        return "Unknown"

    try:
        pc = int(postcode)
    except Exception:
        return "Unknown"

    if 1000 <= pc <= 1999 or 2000 <= pc <= 2599 or 2619 <= pc <= 2899 or 2921 <= pc <= 2999:
        return "NSW"

    if 3000 <= pc <= 3999 or 8000 <= pc <= 8999:
        return "VIC"

    if 4000 <= pc <= 4999 or 9000 <= pc <= 9999:
        return "QLD"

    if 5000 <= pc <= 5999:
        return "SA"

    if 6000 <= pc <= 6999:
        return "WA"

    if 7000 <= pc <= 7999:
        return "TAS"

    if 2600 <= pc <= 2618 or 2900 <= pc <= 2920:
        return "ACT"

    if 800 <= pc <= 999:
        return "NT"

    return "Unknown"


def postcode_to_city(postcode):
    if postcode is None or pd.isna(postcode):
        return "Unknown"

    try:
        pc = int(postcode)
    except Exception:
        return "Unknown"

    if 2000 <= pc <= 2234:
        return "Sydney"

    if 3000 <= pc <= 3207:
        return "Melbourne"

    if 4000 <= pc <= 4207:
        return "Brisbane"

    if 5000 <= pc <= 5199:
        return "Adelaide"

    if 6000 <= pc <= 6199:
        return "Perth"

    if 7000 <= pc <= 7199:
        return "Hobart"

    if 2600 <= pc <= 2618:
        return "Canberra"

    if 800 <= pc <= 899:
        return "Darwin"

    return "Regional / Other"


def postcode_to_area_type(postcode):
    city = postcode_to_city(postcode)

    if city in [
        "Sydney",
        "Melbourne",
        "Brisbane",
        "Adelaide",
        "Perth",
        "Hobart",
        "Canberra",
        "Darwin",
    ]:
        return "Metro / City"

    if city == "Unknown":
        return "Unknown"

    return "Regional"


def detect_postcode_column(df):
    possible_names = [
        "postcode",
        "post code",
        "postal code",
        "zip",
        "zip code",
        "school postcode",
        "venue postcode",
        "audience postcode",
        "participant postcode",
    ]

    for col in df.columns:
        col_lower = str(col).lower().strip()

        if any(name in col_lower for name in possible_names):
            return col

    return None


def add_geographic_insights(df):
    updated_df = df.copy()

    postcode_col = detect_postcode_column(updated_df)

    if postcode_col is None:
        updated_df["Clean Postcode"] = None
        updated_df["Australian State"] = "Unknown"
        updated_df["Estimated City"] = "Unknown"
        updated_df["Area Type"] = "Unknown"
        return updated_df

    updated_df["Clean Postcode"] = updated_df[postcode_col].apply(clean_postcode)

    updated_df["Australian State"] = updated_df["Clean Postcode"].apply(postcode_to_state)

    updated_df["Estimated City"] = updated_df["Clean Postcode"].apply(postcode_to_city)

    updated_df["Area Type"] = updated_df["Clean Postcode"].apply(postcode_to_area_type)

    return updated_df