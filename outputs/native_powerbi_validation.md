# Native Power BI validation

**Status: Ready to share with documented data limitations.**

- Application: Power BI Desktop 2.156.951.0
- Validation date: 8 August 2026
- Source: local prepared CSV files in `data/powerbi`
- Result: the PBIP project opened without definition errors, refreshed successfully, and rendered all three pages.

## Reconciled headline values

| Metric | Power BI | SQL output |
|---|---:|---:|
| Customers analyzed | 5,850 | 5,850 |
| Repeat revenue share | 85.8% | 85.8% |
| M1 retention | 23.4% | 23.4% |
| M6 retention | 22.1% | 22.1% |
| Target customers | 135 | 135 |
| Target historical revenue | £468,149 | £468,149 |
| At-risk 12m repurchase rate | 67.6% | 67.6% |
| Lapsed 12m repurchase rate | 34.1% | 34.1% |
| UK target customers | 109 | 109 |
| UK target historical revenue | £395,895 | £395,895 |

## Visual checks

- All KPI cards, charts, and tables contain data.
- M1, M3, and M6 are shown as categorical horizons.
- Segment, market, and product bars are sorted by the displayed value.
- Currency and percentage formats are applied consistently.
- Table headers and chart dimensions use human-readable English names.
- No clipped titles, broken visuals, definition errors, or empty report pages were found.

## Required caveats

- December 2011 is incomplete and excluded from performance analysis.
- Historical segment repurchase rates are associations, not campaign uplift estimates.
- The report uses a local `DataFolder` parameter; update it after moving the repository.
