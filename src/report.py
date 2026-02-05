# src/report.py
import argparse
from pathlib import Path
from datetime import datetime

import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# Paths
ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "shelf.db"
REPORTS_DIR = ROOT / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

# -----------------------------
# Database snapshot
# -----------------------------
def snapshot_tables():
    with sqlite3.connect(DB_PATH) as conn:
        inv = pd.read_sql_query("SELECT * FROM inventory", conn)
        daily = pd.read_sql_query("SELECT * FROM daily", conn)
    return inv, daily

# -----------------------------
# Plot
# -----------------------------
def plot_daily_revenue(daily):
    fig = plt.figure()
    if not daily.empty:
        pivot_rev = (
            daily.pivot_table(index="date", columns="item", values="revenue", aggfunc="sum")
            .fillna(0)
        )
        pivot_rev.plot(kind="bar", ax=plt.gca())
        plt.title("Daily Revenue by Item")
        plt.xlabel("Date")
        plt.ylabel("Revenue")
        plt.tight_layout()
    return fig

# -----------------------------
# Report Builder
# -----------------------------
def build_report(output_path=None):
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_path = output_path or (REPORTS_DIR / f"revenue_report_{now}.pdf")

    inv, daily = snapshot_tables()

    # Save plot image
    fig = plot_daily_revenue(daily)
    plot_img = REPORTS_DIR / "revenue_plot.png"
    fig.savefig(plot_img)
    plt.close(fig)

    # Styles
    styles = getSampleStyleSheet()
    story = []

    # Title
    story.append(Paragraph("<b>Shelf Revenue Report</b>", styles["Title"]))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles["Normal"]))
    story.append(Paragraph(f"Database: {DB_PATH.name}", styles["Normal"]))
    story.append(Spacer(1, 12))

    # KPIs
    total_items = int(inv["last_count"].sum()) if not inv.empty else 0
    total_revenue = float(daily["revenue"].sum()) if not daily.empty else 0.0
    story.append(Paragraph(f"<b>Items on Shelf:</b> {total_items}", styles["Heading3"]))
    story.append(Paragraph(f"<b>Total Revenue (to date):</b> ₹ {total_revenue:,.2f}", styles["Heading3"]))
    story.append(Spacer(1, 12))

    # Revenue Chart
    story.append(Paragraph("<b>Revenue Chart</b>", styles["Heading2"]))
    story.append(Image(str(plot_img), width=14*cm, height=8*cm))
    story.append(Spacer(1, 12))

    # Inventory Snapshot
    story.append(Paragraph("<b>Inventory Snapshot</b>", styles["Heading2"]))
    if not inv.empty:
        inv_table = [inv.columns.tolist()] + inv.head(20).values.tolist()
        t = Table(inv_table, hAlign="LEFT")
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
        ]))
        story.append(t)
    else:
        story.append(Paragraph("No inventory data available.", styles["Normal"]))
    story.append(Spacer(1, 12))

    # Daily Sales
    story.append(Paragraph("<b>Daily Sales</b>", styles["Heading2"]))
    if not daily.empty:
        daily_table = [daily.columns.tolist()] + daily.head(20).values.tolist()
        t2 = Table(daily_table, hAlign="LEFT")
        t2.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
        ]))
        story.append(t2)
    else:
        story.append(Paragraph("No daily sales data available.", styles["Normal"]))

    # Build PDF
    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4)
    doc.build(story)

    # Cleanup temp image
    try:
        plot_img.unlink()
    except Exception:
        pass

    return str(pdf_path)

# -----------------------------
# CLI
# -----------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()
    path = build_report(args.output)
    print(f"✅ Report saved: {path}")

if __name__ == "__main__":
    main()
