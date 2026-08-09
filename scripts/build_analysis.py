from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_XLSX = ROOT / "data" / "raw" / "online_retail_II.xlsx"
DB_PATH = ROOT / "data" / "processed" / "retention_analysis.sqlite"
PROCESSED = ROOT / "data" / "processed"
POWERBI = ROOT / "data" / "powerbi"
TABLES = ROOT / "outputs" / "tables"
SQL_MODEL = ROOT / "sql" / "01_create_model.sql"

LAST_COMPLETE_MONTH_END = pd.Timestamp("2011-12-01")


def normalize_customer_id(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce").astype("Int64")
    return numeric.astype("string")


def load_source() -> pd.DataFrame:
    sheets = pd.read_excel(RAW_XLSX, sheet_name=None, engine="openpyxl")
    frames = []
    for sheet_name, frame in sheets.items():
        frame = frame.copy()
        frame["source_sheet"] = sheet_name
        frames.append(frame)
    raw = pd.concat(frames, ignore_index=True)
    raw = raw.rename(
        columns={
            "Invoice": "invoice_id",
            "StockCode": "stock_code",
            "Description": "description",
            "Quantity": "quantity",
            "InvoiceDate": "invoice_ts",
            "Price": "unit_price",
            "Customer ID": "customer_id",
            "Country": "country",
        }
    )
    raw["invoice_id"] = raw["invoice_id"].astype("string").str.strip()
    raw["stock_code"] = raw["stock_code"].astype("string").str.strip()
    raw["description"] = raw["description"].astype("string").str.strip()
    raw["country"] = raw["country"].astype("string").str.strip()
    raw["customer_id"] = normalize_customer_id(raw["customer_id"])
    raw["invoice_ts"] = pd.to_datetime(raw["invoice_ts"], errors="coerce")
    raw["quantity"] = pd.to_numeric(raw["quantity"], errors="coerce")
    raw["unit_price"] = pd.to_numeric(raw["unit_price"], errors="coerce")
    return raw


def build_quality_profile(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    exact_duplicate = raw.duplicated(
        subset=[
            "invoice_id",
            "stock_code",
            "description",
            "quantity",
            "invoice_ts",
            "unit_price",
            "customer_id",
            "country",
        ]
    )
    cancelled = raw["invoice_id"].str.upper().str.startswith("C", na=False)

    checks = [
        (1, "Raw rows", len(raw)),
        (2, "Exact duplicate rows", int(exact_duplicate.sum())),
        (3, "Rows without Customer ID", int(raw["customer_id"].isna().sum())),
        (4, "Cancelled invoice rows", int(cancelled.sum())),
        (5, "Rows with non-positive quantity", int((raw["quantity"] <= 0).sum())),
        (6, "Rows with non-positive price", int((raw["unit_price"] <= 0).sum())),
        (7, "Rows with invalid invoice date", int(raw["invoice_ts"].isna().sum())),
        (8, "Rows in incomplete Dec-2011 period", int((raw["invoice_ts"] >= LAST_COMPLETE_MONTH_END).sum())),
    ]
    quality = pd.DataFrame(checks, columns=["check_order", "quality_check", "rows"])
    quality["share_of_raw_rows"] = quality["rows"] / len(raw)

    flow = []
    current = raw.copy()
    flow.append(("Raw source", len(current)))
    current = current.loc[~exact_duplicate].copy()
    flow.append(("After exact deduplication", len(current)))
    current = current.loc[current["customer_id"].notna()].copy()
    flow.append(("After requiring Customer ID", len(current)))
    current = current.loc[~current["invoice_id"].str.upper().str.startswith("C", na=False)].copy()
    flow.append(("After excluding cancellations", len(current)))
    current = current.loc[(current["quantity"] > 0) & (current["unit_price"] > 0)].copy()
    flow.append(("After positive quantity and price", len(current)))
    current = current.loc[current["invoice_ts"].notna()].copy()
    flow.append(("Analysis-ready clean rows", len(current)))

    cleaning_flow = pd.DataFrame(flow, columns=["stage", "rows"])
    cleaning_flow["removed_from_previous"] = cleaning_flow["rows"].shift(1) - cleaning_flow["rows"]
    cleaning_flow["retained_share_of_raw"] = cleaning_flow["rows"] / len(raw)
    return quality, cleaning_flow


def clean_transactions(raw: pd.DataFrame) -> pd.DataFrame:
    dedupe_columns = [
        "invoice_id",
        "stock_code",
        "description",
        "quantity",
        "invoice_ts",
        "unit_price",
        "customer_id",
        "country",
    ]
    clean = raw.drop_duplicates(subset=dedupe_columns).copy()
    clean = clean.loc[clean["customer_id"].notna()].copy()
    clean = clean.loc[~clean["invoice_id"].str.upper().str.startswith("C", na=False)].copy()
    clean = clean.loc[(clean["quantity"] > 0) & (clean["unit_price"] > 0)].copy()
    clean = clean.loc[clean["invoice_ts"].notna()].copy()
    clean["line_revenue"] = clean["quantity"] * clean["unit_price"]
    clean["customer_id"] = clean["customer_id"].astype(str)
    clean["invoice_ts"] = clean["invoice_ts"].dt.strftime("%Y-%m-%d %H:%M:%S")
    return clean[
        [
            "invoice_id",
            "stock_code",
            "description",
            "quantity",
            "invoice_ts",
            "unit_price",
            "customer_id",
            "country",
            "line_revenue",
            "source_sheet",
        ]
    ]


def export_query(connection: sqlite3.Connection, name: str, sql: str) -> pd.DataFrame:
    frame = pd.read_sql_query(sql, connection)
    frame.to_csv(TABLES / f"{name}.csv", index=False, encoding="utf-8")
    return frame


def build_outputs(connection: sqlite3.Connection) -> dict[str, pd.DataFrame]:
    outputs: dict[str, pd.DataFrame] = {}
    queries = {
        "headline_kpis": """
            SELECT
                COUNT(DISTINCT customer_id) AS customers,
                COUNT(*) AS orders,
                SUM(order_revenue) AS revenue,
                SUM(CASE WHEN customer_order_number > 1 THEN 1 ELSE 0 END) AS repeat_orders,
                SUM(CASE WHEN customer_order_number > 1 THEN order_revenue ELSE 0 END) AS repeat_revenue,
                1.0 * SUM(CASE WHEN customer_order_number > 1 THEN order_revenue ELSE 0 END)
                    / SUM(order_revenue) AS repeat_revenue_share
            FROM fact_orders_enriched
        """,
        "monthly_customer_metrics": "SELECT * FROM monthly_customer_metrics ORDER BY activity_month",
        "cohort_retention_long": """
            SELECT cohort_month, month_number, cohort_size, retained_customers, retention_rate
            FROM cohort_retention
            WHERE month_number <= 12
            ORDER BY cohort_month, month_number
        """,
        "retention_horizons": """
            SELECT
                month_number,
                SUM(retained_customers) AS retained_customers,
                SUM(cohort_size) AS eligible_cohort_customers,
                1.0 * SUM(retained_customers) / SUM(cohort_size) AS weighted_retention_rate
            FROM cohort_retention
            WHERE month_number IN (1, 3, 6)
            GROUP BY month_number
            ORDER BY month_number
        """,
        "rfm_backtest_summary": "SELECT * FROM rfm_backtest_summary ORDER BY next_12m_revenue DESC",
        "rfm_current_summary": "SELECT * FROM rfm_current_summary ORDER BY trailing_12m_revenue DESC",
        "country_priority": "SELECT * FROM country_priority ORDER BY target_historical_revenue DESC",
        "product_affinity": """
            SELECT * FROM target_product_affinity
            WHERE target_customers >= 10
            ORDER BY target_customers DESC, historical_revenue DESC
            LIMIT 50
        """,
        "customer_priority": """
            SELECT * FROM rfm_current
            WHERE rfm_segment IN ('High-Value At Risk', 'High-Value Lapsed')
            ORDER BY
                CASE rfm_segment WHEN 'High-Value At Risk' THEN 1 ELSE 2 END,
                monetary_revenue DESC
        """,
        "priority_kpis": """
            SELECT
                COUNT(*) AS target_customers,
                SUM(CASE WHEN rfm_segment = 'High-Value At Risk' THEN 1 ELSE 0 END) AS at_risk_customers,
                SUM(CASE WHEN rfm_segment = 'High-Value Lapsed' THEN 1 ELSE 0 END) AS lapsed_customers,
                SUM(monetary_revenue) AS target_historical_revenue,
                SUM(CASE WHEN primary_country = 'United Kingdom' THEN 1 ELSE 0 END) AS uk_target_customers,
                SUM(CASE WHEN primary_country = 'United Kingdom' THEN monetary_revenue ELSE 0 END) AS uk_target_revenue,
                (SELECT next_12m_repeat_rate FROM rfm_backtest_summary
                 WHERE rfm_segment = 'High-Value At Risk') AS at_risk_backtest_rate,
                (SELECT next_12m_repeat_rate FROM rfm_backtest_summary
                 WHERE rfm_segment = 'High-Value Lapsed') AS lapsed_backtest_rate
            FROM rfm_current
            WHERE rfm_segment IN ('High-Value At Risk', 'High-Value Lapsed')
        """,
        "segment_decision": """
            SELECT
                c.rfm_segment,
                c.customers AS current_customers,
                c.trailing_12m_revenue,
                c.avg_customer_revenue,
                c.avg_recency_days,
                b.next_12m_repeat_rate,
                b.avg_next_12m_revenue
            FROM rfm_current_summary AS c
            LEFT JOIN rfm_backtest_summary AS b
                ON c.rfm_segment = b.rfm_segment
            ORDER BY c.trailing_12m_revenue DESC
        """,
    }
    for name, sql in queries.items():
        outputs[name] = export_query(connection, name, sql)

    cohort = outputs["cohort_retention_long"]
    matrix = cohort.pivot(index="cohort_month", columns="month_number", values="retention_rate")
    matrix.to_csv(TABLES / "cohort_retention_matrix.csv", encoding="utf-8")
    outputs["cohort_retention_matrix"] = matrix

    horizons = outputs["retention_horizons"].set_index("month_number")["weighted_retention_rate"]
    outputs["headline_kpis"]["m1_retention"] = float(horizons.get(1, np.nan))
    outputs["headline_kpis"]["m3_retention"] = float(horizons.get(3, np.nan))
    outputs["headline_kpis"]["m6_retention"] = float(horizons.get(6, np.nan))
    outputs["headline_kpis"].to_csv(TABLES / "headline_kpis.csv", index=False, encoding="utf-8")

    cohort_wide = cohort.pivot(index="cohort_month", columns="month_number", values="retention_rate")
    cohort_wide = cohort_wide.rename(columns={0: "m0", 1: "m1", 3: "m3", 6: "m6"})
    cohort_wide = cohort_wide[[column for column in ["m0", "m1", "m3", "m6"] if column in cohort_wide.columns]]
    cohort_wide = cohort_wide.reset_index()
    cohort_wide.to_csv(TABLES / "cohort_summary.csv", index=False, encoding="utf-8")
    outputs["cohort_summary"] = cohort_wide
    return outputs


def export_powerbi(outputs: dict[str, pd.DataFrame], connection: sqlite3.Connection) -> None:
    mapping = {
        "headline_kpis": "headline_kpis.csv",
        "monthly_customer_metrics": "monthly_metrics.csv",
        "cohort_retention_long": "cohort_retention.csv",
        "retention_horizons": "retention_horizons.csv",
        "rfm_backtest_summary": "rfm_backtest.csv",
        "rfm_current_summary": "rfm_segments.csv",
        "country_priority": "country_priority.csv",
        "product_affinity": "product_affinity.csv",
        "priority_kpis": "priority_kpis.csv",
        "segment_decision": "segment_decision.csv",
        "cohort_summary": "cohort_summary.csv",
    }
    for source_name, filename in mapping.items():
        frame = outputs[source_name]
        if source_name == "country_priority":
            frame = frame.loc[frame["customers"] >= 20].copy()
        if source_name == "product_affinity":
            frame = frame.head(10).copy()
        if source_name == "retention_horizons":
            frame = frame.copy()
            frame["horizon"] = "M" + frame["month_number"].astype(str)
            frame = frame[["month_number", "horizon", "retained_customers", "eligible_cohort_customers", "weighted_retention_rate"]]
        if source_name == "cohort_retention_long":
            frame = frame.loc[frame["month_number"].between(1, 6)].copy()
            frame["horizon"] = "M" + frame["month_number"].astype(str)
            frame = frame[["cohort_month", "month_number", "horizon", "cohort_size", "retained_customers", "retention_rate"]]
        frame.to_csv(POWERBI / filename, index=False, encoding="utf-8")

    monthly_rfm = pd.read_sql_query(
        """
        SELECT
            r.customer_id,
            r.primary_country,
            r.recency_days,
            r.frequency_orders,
            r.monetary_revenue,
            r.rfm_segment
        FROM rfm_current AS r
        """,
        connection,
    )
    monthly_rfm.to_csv(POWERBI / "customer_segments.csv", index=False, encoding="utf-8")


def write_summary(outputs: dict[str, pd.DataFrame], quality: pd.DataFrame) -> None:
    headline = outputs["headline_kpis"].iloc[0].to_dict()
    horizons = {
        f"m{int(row.month_number)}": float(row.weighted_retention_rate)
        for row in outputs["retention_horizons"].itertuples()
    }
    top_segments = outputs["rfm_current_summary"].to_dict(orient="records")
    top_countries = outputs["country_priority"].head(10).to_dict(orient="records")
    payload = {
        "source_rows": int(quality.loc[quality["quality_check"] == "Raw rows", "rows"].iloc[0]),
        "analysis_end_exclusive": "2011-12-01",
        "headline": headline,
        "retention_horizons": horizons,
        "rfm_segments": top_segments,
        "top_country_priorities": top_countries,
    }
    (PROCESSED / "analysis_summary.json").write_text(
        json.dumps(payload, indent=2, default=float), encoding="utf-8"
    )


def main() -> None:
    for directory in (PROCESSED, POWERBI, TABLES):
        directory.mkdir(parents=True, exist_ok=True)

    raw = load_source()
    quality, cleaning_flow = build_quality_profile(raw)
    clean = clean_transactions(raw)

    if DB_PATH.exists():
        DB_PATH.unlink()
    connection = sqlite3.connect(DB_PATH)
    try:
        clean.to_sql("transactions_clean", connection, index=False, chunksize=50_000)
        quality.to_sql("data_quality_summary", connection, index=False)
        cleaning_flow.to_sql("cleaning_flow", connection, index=False)
        connection.executescript(SQL_MODEL.read_text(encoding="utf-8"))
        connection.commit()

        outputs = build_outputs(connection)
        export_powerbi(outputs, connection)
        quality.to_csv(TABLES / "data_quality_summary.csv", index=False, encoding="utf-8")
        cleaning_flow.to_csv(TABLES / "cleaning_flow.csv", index=False, encoding="utf-8")
        write_summary(outputs, quality)
    finally:
        connection.close()

    print(f"Raw rows: {len(raw):,}")
    print(f"Clean rows: {len(clean):,}")
    print(f"Database: {DB_PATH}")


if __name__ == "__main__":
    main()
