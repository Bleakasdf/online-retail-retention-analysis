# Power BI measures

The report uses simple measures because the business logic is calculated in SQL.

```dax
Total customers = MAX(headline_kpis[customers])

Repeat revenue share =
    MAX(headline_kpis[repeat_revenue_share])

M1 retention = MAX(headline_kpis[m1_retention])

Target customers = MAX(priority_kpis[target_customers])

Target historical revenue =
    MAX(priority_kpis[target_historical_revenue])

At-risk backtest rate =
    MAX(priority_kpis[at_risk_backtest_rate])
```

`MAX` is used for KPI files that contain one summary row. Charts use prepared tables at their natural grain.
