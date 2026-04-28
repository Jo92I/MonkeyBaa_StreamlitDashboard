import re
import pandas as pd
from lib.data_loader import normalise_columns


def extract_target_from_kr(kr_text: str):
    """
    Reads targets like:
    - 4.5/5
    - 80%
    """
    if not isinstance(kr_text, str):
        return None, None

    ratio_match = re.search(r"(\d+(\.\d+)?)\s*/\s*5", kr_text)
    if ratio_match:
        return float(ratio_match.group(1)), "ratio_5"

    pct_match = re.search(r"(\d+(\.\d+)?)\s*%", kr_text)
    if pct_match:
        return float(pct_match.group(1)), "percent"

    score10_match = re.search(r"(\d+(\.\d+)?)\s*/\s*10", kr_text)
    if score10_match:
        return float(score10_match.group(1)), "ratio_10"

    return None, None


def compute_actual_value(source_name, column_name, teacher_df=None, agreements_df=None, ledger_df=None):
    """
    Maps the OKR row to the correct dataset and computes the actual value.
    """
    source_name = str(source_name).strip().lower() if source_name is not None else ""
    column_name = str(column_name).strip().lower() if column_name is not None else ""

    if teacher_df is not None:
        teacher_df = normalise_columns(teacher_df)
    if agreements_df is not None:
        agreements_df = normalise_columns(agreements_df)
    if ledger_df is not None:
        ledger_df = normalise_columns(ledger_df)

    if source_name == "teacher_survey" and teacher_df is not None:
        if column_name in teacher_df.columns:
            val = pd.to_numeric(teacher_df[column_name], errors="coerce").mean()
            return round(val, 2) if pd.notna(val) else None

        # Special fallback for confidence index if someone wants %
        if column_name == "confidence_score_1_5":
            val = pd.to_numeric(teacher_df[column_name], errors="coerce").mean()
            return round((val / 5) * 100, 2) if pd.notna(val) else None

    if source_name == "strategic_agreements" and agreements_df is not None:
        if column_name in agreements_df.columns:
            series = pd.to_numeric(agreements_df[column_name], errors="coerce")
            val = series.mean()
            return round(val, 2) if pd.notna(val) else None

    if source_name == "financial_ledger" and ledger_df is not None:
        if column_name in ledger_df.columns:
            series = pd.to_numeric(ledger_df[column_name], errors="coerce")
            val = series.mean()
            return round(val, 2) if pd.notna(val) else None

    return None


def align_actual_to_target_scale(actual, column_name, target_type):
    """
    If target is 80% but the teacher survey metric is on a 1–5 scale,
    convert mean score to percent.
    """
    if actual is None:
        return None

    if target_type == "percent" and column_name in [
        "engagement_enjoyment_score_1_5",
        "creativity_score_1_5",
        "critical_thinking_score_1_5",
        "confidence_score_1_5",
        "inclusiveness_score_1_5",
        "facilitator_effectiveness_score_1_5",
        "overall_satisfaction_score_1_5",
    ]:
        return round((actual / 5) * 80, 2)

    if target_type == "percent" and column_name == "recommendation_score_1_10":
        return round((actual / 10) * 80, 2)

    return actual


def evaluate_status(actual, target):
    if actual is None or target is None:
        return "No data"

    if actual >= target:
        return "On Track"
    if actual >= target * 0.9:
        return "At Risk"
    return "Below Target"


def build_okr_results(okr_df, teacher_df=None, agreements_df=None, ledger_df=None):
    okr_df = okr_df.copy()
    rows = []

    for _, row in okr_df.iterrows():
        objective = row.get("Objective")
        kr_text = row.get("Key Results (KRs)")
        source_name = row.get("Exact Data Source (Archivo)")
        column_name = row.get("Specific Column (Opcional)")

        target, target_type = extract_target_from_kr(kr_text)
        actual_raw = compute_actual_value(
            source_name=source_name,
            column_name=column_name,
            teacher_df=teacher_df,
            agreements_df=agreements_df,
            ledger_df=ledger_df,
        )
        actual = align_actual_to_target_scale(actual_raw, str(column_name).strip().lower(), target_type)
        status = evaluate_status(actual, target)

        rows.append(
            {
                "Area": row.get("Area"),
                "Sub Area": row.get("Sub Area"),
                "Objective": objective,
                "KR": kr_text,
                "Source": source_name,
                "Column": column_name,
                "Target": target,
                "Target Type": target_type,
                "Actual": actual,
                "Status": status,
            }
        )

    return pd.DataFrame(rows)