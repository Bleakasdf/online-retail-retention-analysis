# Validation report

**Result: 12/12 checks passed.**

| Check | Status | Evidence |
|---|---:|---:|
| Order natural key is unique | PASS | 0 |
| Retention rates are between 0% and 100% | PASS | 0 |
| Target customer count reconciles | PASS | 135 |
| UK target count reconciles | PASS | 109 |
| All Power BI JSON files parse | PASS | 37 |
| Power BI CSV schemas match the semantic model | PASS | OK |
| Power BI text files use UTF-8 without BOM | PASS | OK |
| Notebook has no execution errors | PASS | 0 |
| Notebook contains executed code | PASS | 14 |
| Dashboard image exists: overview.png | PASS | 120342 |
| Dashboard image exists: segments.png | PASS | 64654 |
| Dashboard image exists: priorities.png | PASS | 64612 |

## Distribution caveat

The largest observed order is £77,184. The top 1% of orders account for 16.3% of revenue. The portfolio contains large wholesale-like orders, so revenue concentration should be considered when sizing a CRM pilot.

The Power BI project passed the structural checks above. A completed native Power BI Desktop render check is documented in `outputs/native_powerbi_validation.md`. After cloning the repository, set the `DataFolder` parameter to the local `data/powerbi` directory before refreshing the report.
