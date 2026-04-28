# Monkey Baa Streamlit Dashboard

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

The workbook is expected at:

`data/monkey_baa_cleaned_workbook.xlsx`

## Pages
- Home
- Dashboard
- Theory of Change & OKRs
- AI Insights (local rule-based summary shell)
- Data Quality

## What this starter app does
- Reads the uploaded Monkey Baa workbook
- Uses `KPI_Summary`, `Master_Child_Level`, `Parent_Responses`, `Performances`, and `Outcomes_Framework`
- Builds KPI cards, show and year filters, emotion and outcome charts
- Adds an OKR view linked to Theory of Change style outcome areas
- Includes a data quality page for capstone transparency
