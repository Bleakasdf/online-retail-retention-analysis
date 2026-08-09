from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCAL_PACKAGES = ROOT / ".python-packages"
sys.path.insert(0, str(LOCAL_PACKAGES))

import nbformat as nbf
import pandas as pd
from nbclient import NotebookClient


NOTEBOOK_PATH = ROOT / "notebooks" / "analysis.ipynb"


def pct(value: float) -> str:
    return f"{value:.1%}"


def money(value: float) -> str:
    return f"£{value:,.0f}"


def build_notebook() -> nbf.NotebookNode:
    headline = pd.read_csv(ROOT / "outputs" / "tables" / "headline_kpis.csv").iloc[0]
    priority = pd.read_csv(ROOT / "outputs" / "tables" / "priority_kpis.csv").iloc[0]
    backtest = pd.read_csv(ROOT / "outputs" / "tables" / "rfm_backtest_summary.csv")
    backtest = backtest.set_index("rfm_segment")

    at_risk_repeat = float(backtest.loc["High-Value At Risk", "next_12m_repeat_rate"])
    lapsed_repeat = float(backtest.loc["High-Value Lapsed", "next_12m_repeat_rate"])

    notebook = nbf.v4.new_notebook()
    notebook["metadata"]["kernelspec"] = {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    }
    notebook["metadata"]["language_info"] = {"name": "python", "version": "3.12"}

    cells = [
        nbf.v4.new_markdown_cell(
            "# Customer Retention and Revenue Prioritization\n\n"
            "## tl;dr\n\n"
            f"- Repeat orders generated **{pct(float(headline['repeat_revenue_share']))}** of observed revenue.\n"
            f"- Weighted retention was **{pct(float(headline['m1_retention']))} at M1** and "
            f"**{pct(float(headline['m6_retention']))} at M6**.\n"
            f"- The current high-value risk pool contains **{int(priority['target_customers']):,} customers** "
            f"with **{money(float(priority['target_historical_revenue']))}** in trailing historical revenue.\n"
            f"- In the historical backtest, High-Value At Risk customers repurchased at "
            f"**{pct(at_risk_repeat)}**, versus **{pct(lapsed_repeat)}** for High-Value Lapsed customers.\n"
            "- Recommendation: prioritize High-Value At Risk customers first; treat lapsed customers as a separate, lower-confidence reactivation group."
        ),
        nbf.v4.new_markdown_cell(
            "## Context & Methods\n\n"
            "**Business question:** Which customers and markets should be prioritized to retain repeat revenue?\n\n"
            "The analysis follows four simple steps: measure repeat-revenue health, calculate cohort retention, "
            "backtest behavioral segments, and identify actionable customer, market, and product priorities.\n\n"
            "### Key Assumptions\n\n"
            "- December 2011 is incomplete and excluded from performance calculations.\n"
            "- Cancelled invoices, returns, non-positive prices, and rows without Customer ID are excluded.\n"
            "- RFM segments describe observed behavior; they do not prove why a customer stopped purchasing.\n"
            "- Historical revenue in a risk segment is not a forecast or guaranteed revenue uplift."
        ),
        nbf.v4.new_code_cell(
            "from pathlib import Path\n"
            "import sys, sqlite3\n\n"
            "PROJECT_ROOT = Path.cwd()\n"
            "sys.path.insert(0, str(PROJECT_ROOT / '.python-packages'))\n\n"
            "import pandas as pd\n"
            "import numpy as np\n"
            "import matplotlib.pyplot as plt\n"
            "from matplotlib.ticker import PercentFormatter\n"
            "from IPython.display import display\n\n"
            "DB_PATH = PROJECT_ROOT / 'data' / 'processed' / 'retention_analysis.sqlite'\n"
            "CHART_DIR = PROJECT_ROOT / 'outputs' / 'charts'\n"
            "CHART_DIR.mkdir(parents=True, exist_ok=True)\n"
            "connection = sqlite3.connect(DB_PATH)\n"
            "plt.style.use('seaborn-v0_8-whitegrid')"
        ),
        nbf.v4.new_markdown_cell("## Data\n\n### 1. Check the source and cleaning flow"),
        nbf.v4.new_code_cell(
            "quality_sql = \"\"\"\n"
            "SELECT quality_check, rows, share_of_raw_rows\n"
            "FROM data_quality_summary\n"
            "ORDER BY check_order\n"
            "\"\"\"\n"
            "quality = pd.read_sql_query(quality_sql, connection)\n"
            "display(quality)"
        ),
        nbf.v4.new_code_cell(
            "cleaning_sql = \"\"\"\n"
            "SELECT stage, rows, removed_from_previous, retained_share_of_raw\n"
            "FROM cleaning_flow\n"
            "\"\"\"\n"
            "cleaning = pd.read_sql_query(cleaning_sql, connection)\n"
            "display(cleaning)"
        ),
        nbf.v4.new_markdown_cell("## Results\n\n### 2. How dependent is revenue on repeat purchasing?"),
        nbf.v4.new_code_cell(
            "headline_sql = \"\"\"\n"
            "SELECT\n"
            "    COUNT(DISTINCT customer_id) AS customers,\n"
            "    COUNT(*) AS orders,\n"
            "    SUM(order_revenue) AS revenue,\n"
            "    SUM(CASE WHEN customer_order_number > 1 THEN order_revenue ELSE 0 END) AS repeat_revenue,\n"
            "    1.0 * SUM(CASE WHEN customer_order_number > 1 THEN order_revenue ELSE 0 END)\n"
            "        / SUM(order_revenue) AS repeat_revenue_share\n"
            "FROM fact_orders_enriched\n"
            "\"\"\"\n"
            "headline = pd.read_sql_query(headline_sql, connection)\n"
            "display(headline)"
        ),
        nbf.v4.new_code_cell(
            "monthly = pd.read_sql_query(\n"
            "    'SELECT * FROM monthly_customer_metrics ORDER BY activity_month', connection\n"
            ")\n"
            "fig, ax = plt.subplots(figsize=(10, 4.5))\n"
            "ax.plot(monthly['activity_month'], monthly['repeat_revenue_share'], color='#2F6B9A', linewidth=2.5)\n"
            "ax.set_title('Monthly repeat-revenue share')\n"
            "ax.set_xlabel('Month')\n"
            "ax.set_ylabel('Repeat-revenue share')\n"
            "ax.yaxis.set_major_formatter(PercentFormatter(1))\n"
            "ax.tick_params(axis='x', rotation=60)\n"
            "fig.tight_layout()\n"
            "fig.savefig(CHART_DIR / 'monthly_repeat_revenue.png', dpi=160, bbox_inches='tight')\n"
            "plt.show()"
        ),
        nbf.v4.new_markdown_cell("### 3. Where does retention decline across acquisition cohorts?"),
        nbf.v4.new_code_cell(
            "cohort_sql = \"\"\"\n"
            "SELECT cohort_month, month_number, cohort_size, retained_customers, retention_rate\n"
            "FROM cohort_retention\n"
            "WHERE month_number <= 12\n"
            "ORDER BY cohort_month, month_number\n"
            "\"\"\"\n"
            "cohort = pd.read_sql_query(cohort_sql, connection)\n"
            "cohort_matrix = cohort.pivot(index='cohort_month', columns='month_number', values='retention_rate')\n"
            "display(cohort_matrix.round(3).tail(12))"
        ),
        nbf.v4.new_code_cell(
            "cohort_heatmap = cohort_matrix.loc[:, (cohort_matrix.columns >= 1) & (cohort_matrix.columns <= 6)]\n"
            "fig, ax = plt.subplots(figsize=(11, 8))\n"
            "palette = plt.get_cmap('YlOrBr').copy()\n"
            "palette.set_bad('#E5E7EB')\n"
            "values = np.ma.masked_invalid(cohort_heatmap.to_numpy(dtype=float))\n"
            "image = ax.imshow(values, aspect='auto', cmap=palette, vmin=0, vmax=0.5)\n"
            "ax.set_title('Monthly retention by acquisition cohort (M1-M6)', fontsize=15, weight='bold', pad=28)\n"
            "ax.text(0.5, 1.015, 'Darker = higher retention; grey = not yet observable; M0 is 100% by definition',\n"
            "        transform=ax.transAxes, ha='center', va='bottom', color='#52606D', fontsize=10)\n"
            "ax.set_xlabel('Months since first purchase')\n"
            "ax.set_ylabel('Acquisition cohort')\n"
            "ax.set_xticks(range(len(cohort_heatmap.columns)))\n"
            "ax.set_xticklabels([f'M{month}' for month in cohort_heatmap.columns])\n"
            "ax.set_yticks(range(len(cohort_heatmap.index)))\n"
            "ax.set_yticklabels(cohort_heatmap.index)\n"
            "for row_index in range(cohort_heatmap.shape[0]):\n"
            "    for column_index in range(cohort_heatmap.shape[1]):\n"
            "        value = cohort_heatmap.iat[row_index, column_index]\n"
            "        if pd.notna(value):\n"
            "            text_color = 'white' if value >= 0.32 else '#172B4D'\n"
            "            ax.text(column_index, row_index, f'{value:.0%}', ha='center', va='center',\n"
            "                    color=text_color, fontsize=7)\n"
            "colorbar = fig.colorbar(image, ax=ax)\n"
            "colorbar.set_label('Monthly retention (darker = higher)')\n"
            "colorbar.ax.yaxis.set_major_formatter(PercentFormatter(1))\n"
            "fig.tight_layout()\n"
            "fig.savefig(CHART_DIR / 'cohort_retention_heatmap.png', dpi=160, bbox_inches='tight')\n"
            "plt.show()"
        ),
        nbf.v4.new_markdown_cell("### 4. Which behavioral segments were most likely to repurchase?"),
        nbf.v4.new_code_cell(
            "backtest_sql = \"\"\"\n"
            "SELECT\n"
            "    rfm_segment, customers, next_12m_repeat_rate, next_12m_revenue, avg_next_12m_revenue\n"
            "FROM rfm_backtest_summary\n"
            "ORDER BY next_12m_repeat_rate DESC\n"
            "\"\"\"\n"
            "backtest = pd.read_sql_query(backtest_sql, connection)\n"
            "display(backtest)"
        ),
        nbf.v4.new_code_cell(
            "plot_data = backtest.sort_values('next_12m_repeat_rate')\n"
            "fig, ax = plt.subplots(figsize=(9, 5))\n"
            "ax.barh(plot_data['rfm_segment'], plot_data['next_12m_repeat_rate'], color='#D9892B')\n"
            "ax.set_title('Historical 12-month repurchase rate by segment')\n"
            "ax.set_xlabel('Repurchase rate')\n"
            "ax.xaxis.set_major_formatter(PercentFormatter(1))\n"
            "fig.tight_layout()\n"
            "fig.savefig(CHART_DIR / 'segment_backtest.png', dpi=160, bbox_inches='tight')\n"
            "plt.show()"
        ),
        nbf.v4.new_markdown_cell("### 5. Which current customers and markets should CRM prioritize?"),
        nbf.v4.new_code_cell(
            "segment_sql = \"\"\"\n"
            "SELECT\n"
            "    c.rfm_segment, c.customers, c.trailing_12m_revenue, c.avg_recency_days,\n"
            "    b.next_12m_repeat_rate\n"
            "FROM rfm_current_summary AS c\n"
            "LEFT JOIN rfm_backtest_summary AS b\n"
            "    ON c.rfm_segment = b.rfm_segment\n"
            "ORDER BY c.trailing_12m_revenue DESC\n"
            "\"\"\"\n"
            "segments = pd.read_sql_query(segment_sql, connection)\n"
            "display(segments)"
        ),
        nbf.v4.new_code_cell(
            "country_sql = \"\"\"\n"
            "SELECT country, customers, target_customers, target_customer_share, target_historical_revenue\n"
            "FROM country_priority\n"
            "WHERE customers >= 20\n"
            "ORDER BY target_historical_revenue DESC\n"
            "\"\"\"\n"
            "countries = pd.read_sql_query(country_sql, connection)\n"
            "display(countries)"
        ),
        nbf.v4.new_code_cell(
            "country_plot = countries.loc[countries['target_customers'] > 0].sort_values('target_historical_revenue')\n"
            "fig, ax = plt.subplots(figsize=(9, 4.5))\n"
            "ax.barh(country_plot['country'], country_plot['target_historical_revenue'], color='#2F6B9A')\n"
            "ax.set_title('Historical revenue in high-value risk segments by market')\n"
            "ax.set_xlabel('Trailing historical revenue (£)')\n"
            "fig.tight_layout()\n"
            "fig.savefig(CHART_DIR / 'country_priority.png', dpi=160, bbox_inches='tight')\n"
            "plt.show()"
        ),
        nbf.v4.new_markdown_cell("### 6. Which products are familiar to the target customers?"),
        nbf.v4.new_code_cell(
            "product_sql = \"\"\"\n"
            "SELECT stock_code, product_description, target_customers, historical_revenue\n"
            "FROM target_product_affinity\n"
            "WHERE target_customers >= 10\n"
            "ORDER BY target_customers DESC, historical_revenue DESC\n"
            "LIMIT 15\n"
            "\"\"\"\n"
            "products = pd.read_sql_query(product_sql, connection)\n"
            "display(products)"
        ),
        nbf.v4.new_markdown_cell(
            "## Takeaways\n\n"
            f"1. Repeat purchasing is economically important: it generated **{pct(float(headline['repeat_revenue_share']))}** of observed revenue.\n"
            f"2. Retention remains near one quarter at M1/M3 and declines to **{pct(float(headline['m6_retention']))}** at M6.\n"
            f"3. **High-Value At Risk** is the first CRM priority: the historical backtest shows a **{pct(at_risk_repeat)}** 12-month repurchase rate.\n"
            f"4. **High-Value Lapsed** needs a separate reactivation motion: its backtested repurchase rate was only **{pct(lapsed_repeat)}**.\n"
            f"5. The two target groups contain **{int(priority['target_customers']):,} customers** and "
            f"**{money(float(priority['target_historical_revenue']))}** in trailing historical revenue; this is an observed value base, not predicted uplift.\n"
            f"6. The United Kingdom contains **{int(priority['uk_target_customers']):,} target customers** and "
            f"**{money(float(priority['uk_target_revenue']))}** of that historical revenue, so it is the only market with sufficient scale for a first pilot."
        ),
        nbf.v4.new_code_cell("connection.close()"),
    ]
    notebook["cells"] = cells
    return notebook


def main() -> None:
    notebook = build_notebook()
    NOTEBOOK_PATH.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(notebook, NOTEBOOK_PATH)

    os.environ["PYTHONPATH"] = str(LOCAL_PACKAGES)
    client = NotebookClient(
        notebook,
        timeout=180,
        kernel_name="python3",
        resources={"metadata": {"path": str(ROOT)}},
    )
    executed = client.execute()
    nbf.write(executed, NOTEBOOK_PATH)
    print(f"Executed notebook: {NOTEBOOK_PATH}")


if __name__ == "__main__":
    main()
