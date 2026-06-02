from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.analysis.metrics import DAILY_LABELS


def trend_chart(daily_df: pd.DataFrame, column: str) -> go.Figure:
    sub = daily_df[["log_date", column]].dropna()
    fig = px.line(
        sub, x="log_date", y=column, markers=True,
        labels={"log_date": "Дата", column: DAILY_LABELS.get(column, column)},
    )
    fig.update_layout(title=DAILY_LABELS.get(column, column), height=300, margin=dict(t=40))
    return fig


def correlation_heatmap(corr: pd.DataFrame) -> go.Figure:
    fig = px.imshow(
        corr, text_auto=".2f", color_continuous_scale="RdBu", zmin=-1, zmax=1, aspect="auto",
    )
    fig.update_layout(title="Корреляции метрик", height=500, margin=dict(t=40))
    return fig


def scatter_chart(daily_df: pd.DataFrame, x: str, y: str) -> go.Figure:
    sub = daily_df[[x, y]].dropna()
    fig = px.scatter(
        sub, x=x, y=y,
        labels={x: DAILY_LABELS.get(x, x), y: DAILY_LABELS.get(y, y)},
    )
    fig.update_traces(marker=dict(size=10))
    fig.update_layout(height=400, margin=dict(t=40))
    return fig


def expense_pie(txn_df: pd.DataFrame) -> go.Figure:
    exp = txn_df[txn_df["kind"] == "expense"]
    grouped = exp.groupby("category", as_index=False)["amount"].sum()
    fig = px.pie(grouped, names="category", values="amount", hole=0.4)
    fig.update_layout(title="Расходы по категориям", height=400, margin=dict(t=40))
    return fig


def income_expense_bar(txn_df: pd.DataFrame) -> go.Figure:
    t = txn_df.copy()
    t["month"] = t["txn_date"].dt.to_period("M").astype(str)
    grp = t[t["kind"].isin(["income", "expense"])]
    pivot = grp.groupby(["month", "kind"], as_index=False)["amount"].sum()
    fig = px.bar(
        pivot, x="month", y="amount", color="kind", barmode="group",
        labels={"month": "Месяц", "amount": "₽", "kind": "Тип"},
        color_discrete_map={"income": "#2ca02c", "expense": "#d62728"},
    )
    fig.update_layout(title="Доходы и расходы по месяцам", height=350, margin=dict(t=40))
    return fig


def exercise_progress(workouts_df: pd.DataFrame, exercise: str) -> go.Figure:
    sub = workouts_df[workouts_df["exercise"] == exercise].copy()
    sub["session_date"] = sub["started_at"].dt.date
    sub["volume"] = sub["reps"] * sub["weight_kg"].fillna(0)
    agg = sub.groupby("session_date", as_index=False).agg(
        max_weight=("weight_kg", "max"), volume=("volume", "sum")
    )
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=agg["session_date"], y=agg["max_weight"], name="Макс. вес, кг", mode="lines+markers"
    ))
    fig.add_trace(go.Bar(
        x=agg["session_date"], y=agg["volume"], name="Тоннаж", yaxis="y2", opacity=0.4
    ))
    fig.update_layout(
        title=f"Прогресс: {exercise}",
        yaxis=dict(title="Макс. вес, кг"),
        yaxis2=dict(title="Тоннаж", overlaying="y", side="right"),
        height=400, margin=dict(t=40), legend=dict(orientation="h"),
    )
    return fig
