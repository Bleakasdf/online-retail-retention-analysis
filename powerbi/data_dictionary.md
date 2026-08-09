# Data dictionary

## Core analytical tables

| Table | Grain | Purpose |
|---|---|---|
| `transactions_clean` | One purchased product line | Clean source transactions |
| `fact_orders` | One customer order | Revenue and order analysis |
| `fact_orders_enriched` | One customer order | Adds the customer's order number |
| `customer_month` | One customer and activity month | Monthly activity and cohorts |
| `cohort_retention` | One cohort and later month | Cohort retention rates |
| `rfm_backtest` | One historical customer | Tests segments on the next 12 months |
| `rfm_current` | One current customer | Current CRM prioritization |

## Key fields

| Field | Meaning |
|---|---|
| `order_revenue` | Sum of quantity × unit price within an order |
| `customer_order_number` | Chronological order number for one customer |
| `cohort_month` | Month of the customer's first observed purchase |
| `month_number` | Months since the first purchase month |
| `retention_rate` | Active cohort customers ÷ original cohort size |
| `recency_days` | Days between the snapshot date and last purchase |
| `frequency_orders` | Orders in the 12-month feature window |
| `monetary_revenue` | Revenue in the 12-month feature window |
| `repeat_12m_flag` | One when the backtest customer purchased in the next 12 months |

## Power BI files

The files in `data/powerbi` are small output tables. They are generated from the SQLite model and are the only files read by Power BI.
