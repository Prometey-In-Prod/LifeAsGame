from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st  # noqa: E402

from src.analysis import charts, metrics  # noqa: E402
from src.analysis.metrics import DAILY_LABELS, DAILY_NUMERIC  # noqa: E402

st.set_page_config(page_title="LifeAsGame", page_icon="🎮", layout="wide")


@st.cache_data(ttl=60)
def load_data():
    return (
        metrics.load_daily_df(),
        metrics.load_transactions_df(),
        metrics.load_workouts_df(),
    )


daily_df, txn_df, workouts_df = load_data()

st.title("🎮 LifeAsGame — панель")
if st.button("🔄 Обновить данные"):
    st.cache_data.clear()
    st.rerun()

# --- Обзор и геймификация -------------------------------------------------
st.header("Обзор")
streaks = metrics.compute_streaks(daily_df)

c1, c2, c3, c4 = st.columns(4)
c1.metric("🔥 Чек-ин подряд", f"{streaks['checkin']} дн.",
          help="Дней подряд с заполненным днём")
c2.metric("💪 Тренировки подряд", f"{streaks['training']} дн.")
c3.metric("📅 Всего дней", len(daily_df))
c4.metric("🏋️ Тренировок всего", int(daily_df["trained"].sum()) if not daily_df.empty else 0)

for label, value in (("Чек-ин", streaks["checkin"]), ("Тренировки", streaks["training"])):
    badge = metrics.milestone_label(value)
    if badge:
        st.success(f"Веха «{label}»: {badge}")

if daily_df.empty:
    st.info("Пока нет данных. Заполни несколько дней через бота — графики появятся здесь.")
    st.stop()

# --- Тренды ---------------------------------------------------------------
st.header("Тренды")
available = [c for c in DAILY_NUMERIC if c in daily_df.columns and daily_df[c].notna().any()]
chosen = st.multiselect(
    "Метрики", available, default=available[:3],
    format_func=lambda c: DAILY_LABELS.get(c, c),
)
for col in chosen:
    st.plotly_chart(charts.trend_chart(daily_df, col), use_container_width=True)

# --- Корреляции -----------------------------------------------------------
st.header("Корреляции")
corr = metrics.correlation_matrix(daily_df)
if corr.empty:
    st.info("Нужно минимум 3 заполненных дня для корреляций.")
else:
    st.plotly_chart(charts.correlation_heatmap(corr), use_container_width=True)
    st.caption("Близко к +1 — растут вместе, близко к −1 — одно растёт, другое падает.")

    cc1, cc2 = st.columns(2)
    opts = [c for c in DAILY_NUMERIC + ["trained_int"] if c in daily_df.columns]
    x = cc1.selectbox("Ось X", opts, index=opts.index("sleep_hours") if "sleep_hours" in opts else 0,
                      format_func=lambda c: DAILY_LABELS.get(c, c))
    y = cc2.selectbox("Ось Y", opts, index=opts.index("day_rating") if "day_rating" in opts else 0,
                      format_func=lambda c: DAILY_LABELS.get(c, c))
    st.plotly_chart(charts.scatter_chart(daily_df, x, y), use_container_width=True)

# --- Финансы --------------------------------------------------------------
st.header("Финансы")
if txn_df.empty:
    st.info("Нет транзакций.")
else:
    st.plotly_chart(charts.income_expense_bar(txn_df), use_container_width=True)
    if (txn_df["kind"] == "expense").any():
        st.plotly_chart(charts.expense_pie(txn_df), use_container_width=True)

# --- Тренировки -----------------------------------------------------------
st.header("Тренировки")
if workouts_df.empty:
    st.info("Нет записанных тренировок.")
else:
    exercises = sorted(workouts_df["exercise"].unique())
    ex = st.selectbox("Упражнение", exercises)
    st.plotly_chart(charts.exercise_progress(workouts_df, ex), use_container_width=True)
