import pandas as pd
import re


# -------------------------------
# Detect postcode column
# -------------------------------
def detect_postcode_column(df):
    for col in df.columns:
        lower = str(col).lower()
        if "postcode" in lower or "post code" in lower or "zip" in lower:
            return col
    return None


# -------------------------------
# Clean postcode values
# -------------------------------
def clean_postcode(value):
    if pd.isna(value):
        return None

    text = str(value).strip()

    match = re.search(r"\b\d{4}\b", text)

    if match:
        return match.group(0)

    return None


# -------------------------------
# Postcode → State
# -------------------------------
def postcode_to_state(postcode):
    if postcode is None:
        return "Unknown"

    pc = int(postcode)

    if 1000 <= pc <= 2599 or 2619 <= pc <= 2899 or 2921 <= pc <= 2999:
        return "NSW"
    if 200 <= pc <= 299 or 2600 <= pc <= 2618 or 2900 <= pc <= 2920:
        return "ACT"
    if 3000 <= pc <= 3999:
        return "VIC"
    if 4000 <= pc <= 4999:
        return "QLD"
    if 5000 <= pc <= 5999:
        return "SA"
    if 6000 <= pc <= 6999:
        return "WA"
    if 7000 <= pc <= 7999:
        return "TAS"
    if 800 <= pc <= 999:
        return "NT"

    return "Unknown"


# -------------------------------
# Postcode → Metro / Regional
# -------------------------------
def classify_australian_area(postcode):
    if postcode is None:
        return "Unknown"

    pc = int(postcode)

    # Major metro zones
    metro_ranges = [
        range(2000, 2240),   # Sydney
        range(3000, 3210),   # Melbourne
        range(4000, 4218),   # Brisbane
        range(5000, 5175),   # Adelaide
        range(6000, 6215),   # Perth
        range(7000, 7170),   # Hobart
        range(2600, 2621),   # Canberra
        range(800, 840),     # Darwin
    ]

    for r in metro_ranges:
        if pc in r:
            return "Metro / City"

    # Remote approximation
    remote_ranges = [
        range(841, 1000),
        range(5700, 5800),
        range(6400, 6800),
        range(4800, 5000),
        range(2830, 2900),
    ]

    for r in remote_ranges:
        if pc in r:
            return "Regional / Remote"

    return "Regional"


# -------------------------------
# Postcode → Estimated City
# -------------------------------
def postcode_to_city(postcode):
    if postcode is None:
        return "Unknown"

    pc = int(postcode)

    # NSW
    if 2000 <= pc <= 2240:
        return "Sydney"
    if 2250 <= pc <= 2338:
        return "Central Coast / Newcastle"
    if 2339 <= pc <= 2599:
        return "Regional NSW"

    # VIC
    if 3000 <= pc <= 3207:
        return "Melbourne"
    if 3210 <= pc <= 3325:
        return "Geelong"
    if 3326 <= pc <= 3999:
        return "Regional VIC"

    # QLD
    if 4000 <= pc <= 4207:
        return "Brisbane"
    if 4208 <= pc <= 4229:
        return "Gold Coast"
    if 4300 <= pc <= 4399:
        return "Ipswich / Regional QLD"
    if 4400 <= pc <= 4999:
        return "Regional QLD"

    # SA
    if 5000 <= pc <= 5175:
        return "Adelaide"
    if 5176 <= pc <= 5999:
        return "Regional SA"

    # WA
    if 6000 <= pc <= 6215:
        return "Perth"
    if 6216 <= pc <= 6999:
        return "Regional WA"

    # TAS
    if 7000 <= pc <= 7170:
        return "Hobart"
    if 7171 <= pc <= 7999:
        return "Regional TAS"

    # ACT
    if 2600 <= pc <= 2620:
        return "Canberra"

    # NT
    if 800 <= pc <= 840:
        return "Darwin"
    if 841 <= pc <= 999:
        return "Regional NT"

    return "Other / Unknown"


# -------------------------------
# MAIN FUNCTION (this is what you import)
# -------------------------------
def add_geographic_insights(df):
    updated_df = df.copy()

    postcode_col = detect_postcode_column(updated_df)

    if postcode_col:
        updated_df["Clean Postcode"] = updated_df[postcode_col].apply(clean_postcode)
        updated_df["Australian State"] = updated_df["Clean Postcode"].apply(postcode_to_state)
        updated_df["Area Type"] = updated_df["Clean Postcode"].apply(classify_australian_area)
        updated_df["Estimated City"] = updated_df["Clean Postcode"].apply(postcode_to_city)

    return updated_df