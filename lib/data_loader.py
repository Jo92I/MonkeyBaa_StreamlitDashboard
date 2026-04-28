from pathlib import Path
import pandas as pd
import re
from typing import Optional, Dict


DATA_DIR = Path("data")


def resolve_file(candidates):
    """
    Finds a file either in the project root or inside /data.
    Supports exact names and common '(1)' style duplicates.
    """
    search_paths = [Path("."), DATA_DIR]

    for folder in search_paths:
        for candidate in candidates:
            exact = folder / candidate
            if exact.exists():
                return exact

        for folder_file in folder.glob("*"):
            name = folder_file.name.lower()
            for candidate in candidates:
                candidate_lower = candidate.lower()
                base = candidate_lower.replace(".xlsx", "").replace(".csv", "").replace(".png", "")
                if candidate_lower in name or base in name:
                    return folder_file
    return None


def load_excel_sheets(file_path: Path) -> Dict[str, pd.DataFrame]:
    xls = pd.ExcelFile(file_path)
    return {sheet: pd.read_excel(file_path, sheet_name=sheet) for sheet in xls.sheet_names}


def load_monkey_baa_workbook():
    file_path = resolve_file(["monkey_baa_cleaned_workbook.xlsx", "monkey_baa_cleaned_workbook(1).xlsx"])
    if not file_path:
        return {}
    return load_excel_sheets(file_path)


def load_teacher_survey():
    file_path = resolve_file(["teacher_survey.xlsx"])
    if not file_path:
        return None
    return pd.read_excel(file_path)


def load_okr_file():
    file_path = resolve_file(["OKR.xlsx"])
    if not file_path:
        return None
    return pd.read_excel(file_path)


def load_strategic_agreements():
    file_path = resolve_file(["STRATEGIC AGREEMNTS.xlsx"])
    if not file_path:
        return None
    return pd.read_excel(file_path)


def load_financial_ledger():
    file_path = resolve_file(["FINANCIAL LEDGER.xlsx"])
    if not file_path:
        return None
    return pd.read_excel(file_path)


def load_child_survey_csv():
    file_path = resolve_file(["survey responses 2026.csv"])
    if not file_path:
        return None
    return pd.read_csv(file_path)


def normalise_column_name(col: str) -> str:
    col = str(col).strip().lower()
    col = re.sub(r"[^a-z0-9]+", "_", col)
    col = re.sub(r"_+", "_", col).strip("_")
    return col


def normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [normalise_column_name(c) for c in df.columns]
    return df