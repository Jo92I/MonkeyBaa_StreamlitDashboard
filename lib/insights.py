import pandas as pd


THEORY_OF_CHANGE = {
    "Emotional Engagement": {
        "icon": "💗",
        "keywords": ["happy", "excited", "curious", "proud", "good inside", "emotion"]
    },
    "Connection and Belonging": {
        "icon": "🤝",
        "keywords": ["connected", "belonging", "similar", "character", "included", "inclusion"]
    },
    "Confidence and Self-Expression": {
        "icon": "🌟",
        "keywords": ["brave", "confidence", "share ideas", "ask questions", "try something new", "perform"]
    },
    "Learning and Reflection": {
        "icon": "🧠",
        "keywords": ["learn", "learning", "think", "reflection", "story", "education"]
    },
    "Audience Reach and Access": {
        "icon": "🌍",
        "keywords": [
            "audience", "attendance", "postcode", "post code", "region",
            "school", "remote", "location", "area type",
            "australian state", "estimated city", "city",
            "matched venue", "venue area", "venue state",
            "where did you see the show"
        ]
    },
    "Satisfaction and Advocacy": {
        "icon": "⭐",
        "keywords": ["stars", "recommend", "rating", "satisfaction", "like the show", "feedback"]
    }
}


def find_columns(df, keywords):
    matched = []

    for col in df.columns:
        lower = str(col).lower()
        if any(key in lower for key in keywords):
            matched.append(col)

    return matched


def detect_show_column(df):
    return next((col for col in df.columns if "show" in str(col).lower()), None)


def detect_date_column(df):
    return next(
        (
            col for col in df.columns
            if any(k in str(col).lower() for k in ["date", "year", "submit", "start"])
        ),
        None
    )


def generate_dataset_summary(df):
    return {
        "rows": df.shape[0],
        "columns": df.shape[1],
        "missing_values": int(df.isna().sum().sum()),
        "duplicate_rows": int(df.duplicated().sum())
    }


def theory_of_change_insights(df):
    results = {}

    for area, info in THEORY_OF_CHANGE.items():
        matched = find_columns(df, info["keywords"])
        area_results = {}

        for col in matched:
            series = df[col].dropna()

            if series.empty:
                continue

            numeric = pd.to_numeric(series, errors="coerce")

            if numeric.notna().sum() > 0:
                area_results[col] = round(float(numeric.mean()), 2)
            else:
                top = series.astype(str).value_counts().head(1)
                if not top.empty:
                    area_results[col] = top.index[0]

        results[area] = {
            "icon": info["icon"],
            "columns": matched,
            "results": area_results
        }

    return results