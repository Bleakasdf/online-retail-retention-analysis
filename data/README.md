# Data

The raw workbook is not stored in Git because of its size.

Run:

```bash
python scripts/download_data.py
```

This downloads the official UCI archive and extracts `data/raw/online_retail_II.xlsx`.

The small CSV files in `data/powerbi` are included so the Power BI report can be opened without rebuilding the complete analysis.
