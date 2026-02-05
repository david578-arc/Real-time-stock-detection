# src/dashboard.py
import json
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from sqlalchemy.orm import Session
from sqlalchemy import func

from db import SessionLocal, engine
from models import Product, Inventory, Sale

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"

st.set_page_config(page_title="Shelf Dashboard", layout="wide")

# -------------------------------
# Load prices.json (optional override)
# -------------------------------
@st.cache_data(ttl=10.0)
def load_prices():
    try:
        with open(CONFIG_DIR / "prices.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# -------------------------------
# Load inventory (ORM)
# -------------------------------
@st.cache_data(ttl=5.0)
def load_inventory():
    db: Session = SessionLocal()
    try:
        rows = (
            db.query(
                Product.name.label("item"),
                Inventory.quantity.label("last_count"),
                Product.unit_price.label("price"),
                Inventory.updated_at.label("last_updated")
            )
            .join(Inventory, Product.id == Inventory.product_id)
            .all()
        )
        return pd.DataFrame(rows)
    finally:
        db.close()

# -------------------------------
# Load daily aggregates (ORM from sales)
# -------------------------------
@st.cache_data(ttl=5.0)
def load_daily():
    db: Session = SessionLocal()
    try:
        rows = (
            db.query(
                func.date(Sale.sold_at).label("date"),
                Product.name.label("item"),
                func.sum(Sale.quantity).label("units"),
                func.sum(Sale.amount).label("revenue"),
            )
            .join(Product, Sale.product_id == Product.id)
            .group_by(func.date(Sale.sold_at), Product.name)
            .order_by(func.date(Sale.sold_at))
            .all()
        )
        return pd.DataFrame(rows)
    finally:
        db.close()

# -------------------------------
# Forecasting helper
# -------------------------------
def forecast_series(series, periods=5):
    if len(series) < 3 or series.sum() == 0:
        return pd.Series(
            [0] * periods,
            index=pd.date_range(
                start=pd.Timestamp.today().normalize() + pd.Timedelta(days=1),
                periods=periods
            )
        )
    model = ExponentialSmoothing(
        series,
        trend=None,
        seasonal=None,
        initialization_method="estimated"
    )
    fit = model.fit()
    fc = fit.forecast(periods)
    return fc.clip(lower=0)

# -------------------------------
# Dashboard
# -------------------------------
def main():
    st.title("🛒 Real-Time Shelf Dashboard (ORM)")
    st.caption("Powered by SQLAlchemy · Products · Inventory · Sales")

    prices = load_prices()

    # Inventory snapshot
    inv = load_inventory()
    if inv.empty:
        st.info("No inventory yet. Run the detector to populate the database.")
        return

    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("Current Inventory Snapshot")
        st.dataframe(inv)

    with col2:
        total_items = int(inv["last_count"].sum())
        st.metric("Items on Shelf (est.)", total_items)

        est_revenue = sum(
            (prices.get(row["item"], row["price"]) or 0.0) * row["last_count"]
            for _, row in inv.iterrows()
        )
        st.metric("Potential Shelf Value (₹)", f"{est_revenue:,.2f}")

    # Daily sales
    daily = load_daily()
    if daily.empty:
        st.warning("No sales/daily aggregates yet. Keep the detector running.")
        return

    st.subheader("Daily Units & Revenue")
    pivot_units = daily.pivot_table(
        index="date", columns="item", values="units", aggfunc="sum"
    ).fillna(0)
    pivot_rev = daily.pivot_table(
        index="date", columns="item", values="revenue", aggfunc="sum"
    ).fillna(0)

    st.line_chart(pivot_units)
    st.bar_chart(pivot_rev)

    # Forecast
    st.subheader("5-Day Forecast")
    periods = 5
    fc_frames = []
    for item in pivot_units.columns:
        series = pd.to_numeric(pivot_units[item], errors="coerce").fillna(0.0)
        series.index = pd.to_datetime(series.index)
        fc = forecast_series(series, periods=periods)
        df_fc = pd.DataFrame(
            {"date": fc.index.date, "item": item, "forecast_units": fc.values}
        )
        fc_frames.append(df_fc)

    fc_all = pd.concat(fc_frames, ignore_index=True)
    st.dataframe(fc_all)

    if st.button("Generate PDF Report"):
        from report import build_report
        path = build_report()
        st.success(f"Report generated: {path}")

if __name__ == "__main__":
    main()
