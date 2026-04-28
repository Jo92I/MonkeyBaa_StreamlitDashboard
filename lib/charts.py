
from __future__ import annotations

import plotly.express as px
import pandas as pd


def bar_rates(df: pd.DataFrame, x: str, y: str, title: str):
    fig = px.bar(df, x=x, y=y, text_auto=".0%", title=title)
    fig.update_layout(height=420, xaxis_title="", yaxis_title="")
    return fig


def trend_scatter(df: pd.DataFrame, title: str):
    if df.empty:
        return px.scatter(title=title)
    fig = px.scatter(
        df,
        x="child_responses",
        y="avg_star_rating",
        color="show_name" if "show_name" in df.columns else None,
        size="child_responses",
        hover_data=df.columns,
        title=title,
    )
    fig.update_layout(height=450)
    return fig


def okr_bullet(df: pd.DataFrame):
    fig = px.bar(
        df,
        x="actual",
        y="objective_area",
        orientation="h",
        text="status",
        title="OKR progress by objective area",
    )
    fig.update_layout(height=420, xaxis_title="Actual progress", yaxis_title="")
    return fig
