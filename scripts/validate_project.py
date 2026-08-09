from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path

from build_powerbi_project import TABLES


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "processed" / "retention_analysis.sqlite"
REPORT = ROOT / "outputs" / "validation_report.md"


def one(connection: sqlite3.Connection, sql: str):
    return connection.execute(sql).fetchone()[0]


def main():
    checks: list[tuple[str, bool, str]] = []
    with sqlite3.connect(DB) as connection:
        natural_key_duplicates = one(
            connection,
            """
            SELECT COUNT(*) FROM (
                SELECT invoice_id, customer_id, invoice_ts
                FROM fact_orders
                GROUP BY invoice_id, customer_id, invoice_ts
                HAVING COUNT(*) > 1
            )
            """,
        )
        checks.append(("Order natural key is unique", natural_key_duplicates == 0, str(natural_key_duplicates)))

        bad_retention = one(
            connection,
            "SELECT COUNT(*) FROM cohort_retention WHERE retention_rate < 0 OR retention_rate > 1",
        )
        checks.append(("Retention rates are between 0% and 100%", bad_retention == 0, str(bad_retention)))

        target_customers = one(
            connection,
            "SELECT COUNT(*) FROM rfm_current WHERE rfm_segment IN ('High-Value At Risk', 'High-Value Lapsed')",
        )
        checks.append(("Target customer count reconciles", target_customers == 135, str(target_customers)))

        uk_targets = one(
            connection,
            """
            SELECT COUNT(*) FROM rfm_current
            WHERE primary_country = 'United Kingdom'
              AND rfm_segment IN ('High-Value At Risk', 'High-Value Lapsed')
            """,
        )
        checks.append(("UK target count reconciles", uk_targets == 109, str(uk_targets)))

        top_one_share = one(
            connection,
            """
            WITH ranked AS (
                SELECT order_revenue,
                       ROW_NUMBER() OVER (ORDER BY order_revenue DESC) AS row_number,
                       COUNT(*) OVER () AS order_count
                FROM fact_orders
            )
            SELECT 1.0 * SUM(CASE WHEN row_number <= order_count * 0.01 THEN order_revenue ELSE 0 END)
                 / SUM(order_revenue)
            FROM ranked
            """,
        )
        max_order = one(connection, "SELECT MAX(order_revenue) FROM fact_orders")

    json_files = [
        path
        for path in (ROOT / "powerbi" / "project").rglob("*")
        if path.is_file() and path.suffix.lower() in {".json", ".pbip", ".pbir", ".pbism"}
    ]
    for json_path in json_files:
        try:
            json.loads(json_path.read_text(encoding="utf-8"))
        except Exception as error:
            checks.append((f"Valid JSON: {json_path.relative_to(ROOT)}", False, str(error)))
            break
    else:
        checks.append(("All Power BI JSON files parse", True, str(len(json_files))))

    schema_errors = []
    for table_name, table_spec in TABLES.items():
        csv_path = ROOT / "data" / "powerbi" / table_spec["file"]
        with csv_path.open(encoding="utf-8", newline="") as source:
            actual_columns = next(csv.reader(source))
        expected_columns = [
            table_spec.get("source_columns", {}).get(column, column)
            for column in table_spec["columns"]
        ]
        if actual_columns != expected_columns:
            schema_errors.append(table_name)
    checks.append(("Power BI CSV schemas match the semantic model", not schema_errors, ", ".join(schema_errors) or "OK"))

    bom_files = []
    for path in (ROOT / "powerbi" / "project").rglob("*"):
        if path.is_file() and path.suffix.lower() in {".tmdl", ".json", ".pbip", ".pbir", ".pbism"}:
            if path.read_bytes().startswith(b"\xef\xbb\xbf"):
                bom_files.append(str(path.relative_to(ROOT)))
    checks.append(("Power BI text files use UTF-8 without BOM", not bom_files, ", ".join(bom_files) or "OK"))

    notebook = json.loads((ROOT / "notebooks" / "analysis.ipynb").read_text(encoding="utf-8"))
    notebook_errors = [
        output
        for cell in notebook.get("cells", [])
        for output in cell.get("outputs", [])
        if output.get("output_type") == "error"
    ]
    executed_code = [
        cell
        for cell in notebook.get("cells", [])
        if cell.get("cell_type") == "code" and cell.get("execution_count") is not None
    ]
    checks.append(("Notebook has no execution errors", not notebook_errors, str(len(notebook_errors))))
    checks.append(("Notebook contains executed code", len(executed_code) > 0, str(len(executed_code))))

    for image_name in ["overview.png", "segments.png", "priorities.png"]:
        image_path = ROOT / "powerbi" / "screenshots" / image_name
        checks.append((f"Dashboard image exists: {image_name}", image_path.exists() and image_path.stat().st_size > 0, str(image_path.stat().st_size if image_path.exists() else 0)))

    passed = sum(result for _, result, _ in checks)
    lines = [
        "# Validation report",
        "",
        f"**Result: {passed}/{len(checks)} checks passed.**",
        "",
        "| Check | Status | Evidence |",
        "|---|---:|---:|",
    ]
    lines.extend(f"| {name} | {'PASS' if result else 'FAIL'} | {evidence} |" for name, result, evidence in checks)
    lines.extend(
        [
            "",
            "## Distribution caveat",
            "",
            f"The largest observed order is £{max_order:,.0f}. The top 1% of orders account for {top_one_share:.1%} of revenue. "
            "The portfolio contains large wholesale-like orders, so revenue concentration should be considered when sizing a CRM pilot.",
            "",
            "The Power BI project passed the structural checks above. A completed native Power BI Desktop render check is documented in `outputs/native_powerbi_validation.md`. After cloning the repository, set the `DataFolder` parameter to the local `data/powerbi` directory before refreshing the report.",
        ]
    )
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{passed}/{len(checks)} checks passed")
    print(REPORT)
    if passed != len(checks):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
