from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "powerbi" / "project"
REPORT = PROJECT / "RetentionAnalysis.Report"
MODEL = PROJECT / "RetentionAnalysis.SemanticModel"
PAGES = REPORT / "definition" / "pages"

SCHEMA_VISUAL = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json"
INK = "#172B4D"
TEXT = "#344054"
BLUE = "#2F6B9A"
ORANGE = "#D9892B"
BORDER = "#D9E2EC"
BACKGROUND = "#F5F7FA"


TABLES = {
    "headline_kpis": {
        "file": "headline_kpis.csv",
        "columns": {
            "customers": "int64",
            "orders": "int64",
            "revenue": "double",
            "repeat_orders": "int64",
            "repeat_revenue": "double",
            "repeat_revenue_share": "double",
            "m1_retention": "double",
            "m3_retention": "double",
            "m6_retention": "double",
        },
        "measures": {
            "Total customers": ("MAX(headline_kpis[customers])", "#,##0"),
            "Total orders": ("MAX(headline_kpis[orders])", "#,##0"),
            "Total revenue": ("MAX(headline_kpis[revenue])", "£ #,##0"),
            "Repeat revenue share": ("MAX(headline_kpis[repeat_revenue_share])", "0.0%"),
            "M1 retention": ("MAX(headline_kpis[m1_retention])", "0.0%"),
            "M3 retention": ("MAX(headline_kpis[m3_retention])", "0.0%"),
            "M6 retention": ("MAX(headline_kpis[m6_retention])", "0.0%"),
        },
        "formats": {},
    },
    "monthly_metrics": {
        "file": "monthly_metrics.csv",
        "columns": {
            "Month": "string",
            "active_customers": "int64",
            "new_customers": "int64",
            "returning_customers": "int64",
            "orders": "int64",
            "repeat_orders": "int64",
            "revenue": "double",
            "repeat_order_revenue": "double",
            "returning_customer_share": "double",
            "repeat_revenue_share": "double",
        },
        "measures": {
            "Monthly repeat revenue share": ("AVERAGE(monthly_metrics[repeat_revenue_share])", "0.0%"),
            "Monthly revenue": ("SUM(monthly_metrics[revenue])", "£ #,##0"),
            "Active customers": ("SUM(monthly_metrics[active_customers])", "#,##0"),
        },
        "formats": {},
        "source_columns": {"Month": "activity_month"},
    },
    "retention_horizons": {
        "file": "retention_horizons.csv",
        "columns": {
            "month_number": "int64",
            "Horizon": "string",
            "retained_customers": "int64",
            "eligible_cohort_customers": "int64",
            "weighted_retention_rate": "double",
        },
        "measures": {
            "Weighted retention": ("AVERAGE(retention_horizons[weighted_retention_rate])", "0.0%"),
            "Eligible customers": ("SUM(retention_horizons[eligible_cohort_customers])", "#,##0"),
        },
        "formats": {"weighted_retention_rate": "0.0%"},
        "source_columns": {"Horizon": "horizon"},
    },
    "cohort_summary": {
        "file": "cohort_summary.csv",
        "columns": {
            "Cohort": "string",
            "M0": "double",
            "M1": "double",
            "M3": "double",
            "M6": "double",
        },
        "measures": {},
        "formats": {"M0": "0.0%", "M1": "0.0%", "M3": "0.0%", "M6": "0.0%"},
        "source_columns": {"Cohort": "cohort_month", "M0": "m0", "M1": "m1", "M3": "m3", "M6": "m6"},
    },
    "cohort_retention": {
        "file": "cohort_retention.csv",
        "columns": {
            "Cohort": "string",
            "month_number": "int64",
            "Horizon": "string",
            "cohort_size": "int64",
            "retained_customers": "int64",
            "retention_rate": "double",
        },
        "measures": {
            "Cohort retention": ("AVERAGE(cohort_retention[retention_rate])", "0.0%"),
        },
        "formats": {"retention_rate": "0.0%"},
        "source_columns": {"Cohort": "cohort_month", "Horizon": "horizon"},
    },
    "rfm_backtest": {
        "file": "rfm_backtest.csv",
        "columns": {
            "Segment": "string",
            "customers": "int64",
            "historical_revenue": "double",
            "avg_historical_revenue": "double",
            "next_12m_repeat_rate": "double",
            "next_12m_revenue": "double",
            "avg_next_12m_revenue": "double",
        },
        "measures": {
            "Backtest repeat rate": ("AVERAGE(rfm_backtest[next_12m_repeat_rate])", "0.0%"),
            "Backtest customers": ("SUM(rfm_backtest[customers])", "#,##0"),
            "Next 12m revenue": ("SUM(rfm_backtest[next_12m_revenue])", "£ #,##0"),
        },
        "formats": {"next_12m_repeat_rate": "0.0%", "historical_revenue": "£ #,##0", "next_12m_revenue": "£ #,##0"},
        "source_columns": {"Segment": "rfm_segment"},
    },
    "rfm_segments": {
        "file": "rfm_segments.csv",
        "columns": {
            "Segment": "string",
            "customers": "int64",
            "trailing_12m_revenue": "double",
            "avg_customer_revenue": "double",
            "avg_recency_days": "double",
            "avg_orders": "double",
        },
        "measures": {
            "Segment customers": ("SUM(rfm_segments[customers])", "#,##0"),
            "Trailing revenue": ("SUM(rfm_segments[trailing_12m_revenue])", "£ #,##0"),
            "Average recency": ("AVERAGE(rfm_segments[avg_recency_days])", "0"),
        },
        "formats": {"trailing_12m_revenue": "£ #,##0", "avg_customer_revenue": "£ #,##0", "avg_recency_days": "0", "avg_orders": "0.0"},
        "source_columns": {"Segment": "rfm_segment"},
    },
    "priority_kpis": {
        "file": "priority_kpis.csv",
        "columns": {
            "target_customers": "int64",
            "at_risk_customers": "int64",
            "lapsed_customers": "int64",
            "target_historical_revenue": "double",
            "uk_target_customers": "int64",
            "uk_target_revenue": "double",
            "at_risk_backtest_rate": "double",
            "lapsed_backtest_rate": "double",
        },
        "measures": {
            "Target customers": ("MAX(priority_kpis[target_customers])", "#,##0"),
            "At-risk customers": ("MAX(priority_kpis[at_risk_customers])", "#,##0"),
            "Lapsed customers": ("MAX(priority_kpis[lapsed_customers])", "#,##0"),
            "Target historical revenue": ("MAX(priority_kpis[target_historical_revenue])", "£ #,##0"),
            "UK target customers": ("MAX(priority_kpis[uk_target_customers])", "#,##0"),
            "UK target revenue": ("MAX(priority_kpis[uk_target_revenue])", "£ #,##0"),
            "At-risk backtest rate": ("MAX(priority_kpis[at_risk_backtest_rate])", "0.0%"),
            "Lapsed backtest rate": ("MAX(priority_kpis[lapsed_backtest_rate])", "0.0%"),
        },
        "formats": {},
    },
    "segment_decision": {
        "file": "segment_decision.csv",
        "columns": {
            "Segment": "string",
            "Customers": "int64",
            "Trailing revenue": "double",
            "Average customer revenue": "double",
            "Average recency days": "double",
            "Backtest repeat rate": "double",
            "Average next 12m revenue": "double",
        },
        "measures": {},
        "formats": {"Trailing revenue": "£ #,##0", "Average customer revenue": "£ #,##0", "Average recency days": "0", "Backtest repeat rate": "0.0%", "Average next 12m revenue": "£ #,##0"},
        "source_columns": {"Segment": "rfm_segment", "Customers": "current_customers", "Trailing revenue": "trailing_12m_revenue", "Average customer revenue": "avg_customer_revenue", "Average recency days": "avg_recency_days", "Backtest repeat rate": "next_12m_repeat_rate", "Average next 12m revenue": "avg_next_12m_revenue"},
    },
    "country_priority": {
        "file": "country_priority.csv",
        "columns": {
            "Country": "string",
            "Customers": "int64",
            "Target customers": "int64",
            "Target customer share": "double",
            "Trailing revenue": "double",
            "Target historical revenue": "double",
            "Target revenue share": "double",
        },
        "measures": {
            "Market target customers": ("SUM(country_priority[Target customers])", "#,##0"),
            "Market target revenue": ("SUM(country_priority[Target historical revenue])", "£ #,##0"),
            "Market target share": ("AVERAGE(country_priority[Target customer share])", "0.0%"),
        },
        "formats": {"Target customer share": "0.0%", "Trailing revenue": "£ #,##0", "Target historical revenue": "£ #,##0", "Target revenue share": "0.0%"},
        "source_columns": {"Country": "country", "Customers": "customers", "Target customers": "target_customers", "Target customer share": "target_customer_share", "Trailing revenue": "trailing_12m_revenue", "Target historical revenue": "target_historical_revenue", "Target revenue share": "target_revenue_share"},
    },
    "product_affinity": {
        "file": "product_affinity.csv",
        "columns": {
            "stock_code": "string",
            "Product": "string",
            "target_customers": "int64",
            "units": "double",
            "historical_revenue": "double",
        },
        "measures": {
            "Product target customers": ("SUM(product_affinity[target_customers])", "#,##0"),
            "Product historical revenue": ("SUM(product_affinity[historical_revenue])", "£ #,##0"),
        },
        "formats": {"historical_revenue": "£ #,##0"},
        "source_columns": {"Product": "product_description"},
    },
}


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8", newline="\n")


def write_json(path: Path, value: dict) -> None:
    write_text(path, json.dumps(value, indent=2, ensure_ascii=False))


def tmdl_table(name: str, spec: dict) -> str:
    lines = [f"table {name}", ""]
    for measure, (expression, format_string) in spec["measures"].items():
        lines.extend([
            f"\tmeasure '{measure}' = {expression}",
            f"\t\tformatString: {format_string}",
            "",
        ])
    for column, data_type in spec["columns"].items():
        column_name = f"'{column}'" if " " in column else column
        source_column = spec.get("source_columns", {}).get(column, column)
        lines.extend([
            f"\tcolumn {column_name}",
            f"\t\tdataType: {data_type}",
        ])
        if column in spec.get("formats", {}):
            lines.append(f"\t\tformatString: {spec['formats'][column]}")
        lines.extend([
            "\t\tsummarizeBy: none",
            f"\t\tsourceColumn: {source_column}",
            "",
        ])

    type_map = {"string": "type text", "int64": "Int64.Type", "double": "type number"}
    transformations = ", ".join(
        f'{{"{spec.get("source_columns", {}).get(column, column)}", {type_map[data_type]}}}'
        for column, data_type in spec["columns"].items()
    )
    lines.extend([
        f"\tpartition {name} = m",
        "\t\tmode: import",
        "\t\tsource =",
        "\t\t\tlet",
        f'\t\t\t\tSource = Csv.Document(File.Contents(#"DataFolder" & "\\{spec["file"]}"), [Delimiter=",", Columns={len(spec["columns"])}, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),',
        "\t\t\t\tHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),",
        f'\t\t\t\tTyped = Table.TransformColumnTypes(Headers, {{{transformations}}}, "en-US")',
        "\t\t\tin",
        "\t\t\t\tTyped",
        "",
    ])
    return "\n".join(lines)


def field_column(table: str, column: str) -> dict:
    return {"Column": {"Expression": {"SourceRef": {"Entity": table}}, "Property": column}}


def field_measure(table: str, measure: str) -> dict:
    return {"Measure": {"Expression": {"SourceRef": {"Entity": table}}, "Property": measure}}


def projection(table: str, property_name: str, kind: str, label: str | None = None) -> dict:
    field = field_measure(table, property_name) if kind == "measure" else field_column(table, property_name)
    return {
        "field": field,
        "queryRef": f"{table}.{property_name}",
        "nativeQueryRef": label or property_name.replace("_", " ").title(),
    }


def literal(value: str) -> dict:
    return {"expr": {"Literal": {"Value": value}}}


def container_style(title: str) -> dict:
    return {
        "title": [{"properties": {"show": literal("true"), "text": literal(f"'{title}'"), "fontSize": literal("14D"), "fontColor": {"solid": {"color": literal(f"'{TEXT}'")}}}}],
        "background": [{"properties": {"show": literal("true"), "color": {"solid": {"color": literal("'#FFFFFF'")}}, "transparency": literal("0D")}}],
        "border": [{"properties": {"show": literal("true"), "color": {"solid": {"color": literal(f"'{BORDER}'")}}, "radius": literal("8D")}}],
        "visualHeader": [{"properties": {"show": literal("false")}}],
        "padding": [{"properties": {side: literal("8D") for side in ("top", "bottom", "left", "right")}}],
    }


def position(x: int, y: int, width: int, height: int, z: int) -> dict:
    return {"x": x, "y": y, "z": z, "height": height, "width": width, "tabOrder": z}


def textbox(name: str, x: int, y: int, width: int, height: int, text: str, font_size: int = 28, bold: bool = True) -> dict:
    return {
        "$schema": SCHEMA_VISUAL,
        "name": name,
        "position": position(x, y, width, height, 100),
        "visual": {
            "visualType": "textbox",
            "objects": {"general": [{"properties": {"paragraphs": [{"textRuns": [{"value": text, "textStyle": {"fontFamily": "Segoe UI", "fontSize": f"{font_size}px", "fontWeight": "bold" if bold else "normal", "color": INK}}], "horizontalTextAlignment": "left"}]}}]},
            "visualContainerObjects": {"background": [{"properties": {"show": literal("false")}}], "border": [{"properties": {"show": literal("false")}}]},
        },
    }


def card(name: str, x: int, y: int, width: int, table: str, measure: str, title: str, z: int) -> dict:
    return {
        "$schema": SCHEMA_VISUAL,
        "name": name,
        "position": position(x, y, width, 144, z),
        "visual": {
            "visualType": "card",
            "query": {"queryState": {"Values": {"projections": [projection(table, measure, "measure", measure)]}}},
            "visualContainerObjects": container_style(title),
            "objects": {"labels": [{"properties": {"labelDisplayUnits": literal("1D")}}]},
        },
    }


def chart(name: str, chart_type: str, x: int, y: int, width: int, height: int, category: tuple[str, str], value: tuple[str, str], title: str, color: str, z: int) -> dict:
    sort_field = field_measure(value[0], value[1]) if chart_type == "clusteredBarChart" else field_column(category[0], category[1])
    sort_direction = "Descending" if chart_type == "clusteredBarChart" else "Ascending"
    return {
        "$schema": SCHEMA_VISUAL,
        "name": name,
        "position": position(x, y, width, height, z),
        "visual": {
            "visualType": chart_type,
            "query": {
                "queryState": {
                    "Category": {"projections": [projection(category[0], category[1], "column")]},
                    "Y": {"projections": [projection(value[0], value[1], "measure")]},
                },
                "sortDefinition": {"sort": [{"field": sort_field, "direction": sort_direction}], "isDefaultSort": True},
            },
            "objects": {
                "categoryAxis": [{"properties": {"show": literal("true"), "fontSize": literal("10D"), "labelColor": {"solid": {"color": literal("'#52606D'")}}}}],
                "valueAxis": [{"properties": {"show": literal("true"), "start": literal("0D"), "gridlineStyle": literal("'dotted'"), "gridlineColor": {"solid": {"color": literal("'#E5E7EB'")}}, "labelDisplayUnits": literal("1D")}}],
                "labels": [{"properties": {"show": literal("false" if chart_type == "lineChart" else "true"), "fontSize": literal("9D"), "color": {"solid": {"color": literal(f"'{TEXT}'")}}, "labelDisplayUnits": literal("1D")}}],
                "dataPoint": [{"properties": {"fill": {"solid": {"color": literal(f"'{color}'")}}}}],
                "lineStyles": [{"properties": {"strokeWidth": literal("3D")}}],
            },
            "visualContainerObjects": container_style(title),
        },
    }


def table_visual(name: str, x: int, y: int, width: int, height: int, fields: list[tuple[str, str, str]], title: str, z: int) -> dict:
    projections = [
        projection(field[0], field[1], field[2], field[3] if len(field) > 3 else None)
        for field in fields
    ]
    return {
        "$schema": SCHEMA_VISUAL,
        "name": name,
        "position": position(x, y, width, height, z),
        "visual": {
            "visualType": "tableEx",
            "query": {"queryState": {"Values": {"projections": projections}}},
            "objects": {
                "columnHeaders": [{"properties": {"autoSizeColumnWidth": literal("true"), "backColor": {"solid": {"color": literal("'#EAF2F8'")}}, "fontColor": {"solid": {"color": literal(f"'{INK}'")}}}}],
                "values": [{"properties": {"backColorPrimary": {"solid": {"color": literal("'#FFFFFF'")}}, "backColorSecondary": {"solid": {"color": literal("'#F7F9FC'")}}, "fontColorPrimary": {"solid": {"color": literal(f"'{TEXT}'")}}}}],
                "total": [{"properties": {"totals": literal("false")}}],
            },
            "visualContainerObjects": container_style(title),
        },
    }


def cohort_heatmap(name: str, x: int, y: int, width: int, height: int, title: str, z: int) -> dict:
    measure_ref = "cohort_retention.Cohort retention"
    gradient = {
        "properties": {
            "backColor": {
                "solid": {
                    "color": {
                        "expr": {
                            "FillRule": {
                                "Input": {"SelectRef": {"ExpressionName": measure_ref}},
                                "FillRule": {
                                    "linearGradient2": {
                                        "min": {"color": {"Literal": {"Value": "'#FFF3E5'"}}},
                                        "max": {"color": {"Literal": {"Value": "'#D9892B'"}}},
                                        "nullColoringStrategy": {"strategy": {"Literal": {"Value": "'noColor'"}}},
                                    }
                                },
                            }
                        }
                    }
                }
            }
        },
        "selector": {
            "data": [{"dataViewWildcard": {"matchingOption": 1}}],
            "metadata": measure_ref,
        },
    }
    visual_container_objects = container_style(title)
    visual_container_objects["stylePreset"] = [{"properties": {"name": literal("'None'")}}]
    return {
        "$schema": SCHEMA_VISUAL,
        "name": name,
        "position": position(x, y, width, height, z),
        "visual": {
            "visualType": "pivotTable",
            "query": {
                "queryState": {
                    "Rows": {"projections": [projection("cohort_retention", "Cohort", "column")]},
                    "Columns": {"projections": [projection("cohort_retention", "Horizon", "column")]},
                    "Values": {"projections": [projection("cohort_retention", "Cohort retention", "measure")]},
                },
                "sortDefinition": {
                    "sort": [
                        {"field": field_column("cohort_retention", "Cohort"), "direction": "Ascending"},
                        {"field": field_column("cohort_retention", "Horizon"), "direction": "Ascending"},
                    ],
                    "isDefaultSort": True,
                },
            },
            "objects": {
                "columnHeaders": [{"properties": {
                    "columnAdjustment": literal("'growToFit'"),
                    "autoSizeColumnWidth": literal("true"),
                    "backColor": {"solid": {"color": literal("'#EAF2F8'")}},
                    "fontColor": {"solid": {"color": literal(f"'{INK}'")}},
                }}],
                "rowHeaders": [{"properties": {
                    "backColor": {"solid": {"color": literal("'#FFFFFF'")}},
                    "fontColor": {"solid": {"color": literal(f"'{TEXT}'")}},
                }}],
                "values": [
                    {"properties": {
                        "fontColorPrimary": {"solid": {"color": literal(f"'{TEXT}'")}},
                        "fontColorSecondary": {"solid": {"color": literal(f"'{TEXT}'")}},
                    }},
                    gradient,
                ],
                "subTotals": [{"properties": {
                    "rowSubtotals": literal("false"),
                    "columnSubtotals": literal("false"),
                }}],
                "total": [{"properties": {"totals": literal("false")}}],
            },
            "visualContainerObjects": visual_container_objects,
        },
    }


def page_definition(name: str, display_name: str) -> dict:
    return {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json",
        "name": name,
        "displayName": display_name,
        "displayOption": "FitToPage",
        "height": 1080,
        "width": 1920,
        "objects": {"background": [{"properties": {"color": {"solid": {"color": literal(f"'{BACKGROUND}'")}}, "transparency": literal("0D")}}]},
    }


def build_model(data_folder: Path) -> None:
    definition = MODEL / "definition"
    tables_dir = definition / "tables"
    refs = "\n".join(f"ref table {name}" for name in TABLES)
    model_text = (
        "model Model\n"
        "\tculture: en-US\n"
        "\tdefaultPowerBIDataSourceVersion: powerBI_V3\n"
        "\tsourceQueryCulture: en-US\n"
        "\tdiscourageImplicitMeasures\n\n"
        f'expression DataFolder = "{data_folder}" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]\n\n'
        f"{refs}\n"
    )
    write_text(definition / "model.tmdl", model_text)
    write_text(definition / "database.tmdl", "database RetentionAnalysis\n\tcompatibilityLevel: 1702\n\tcompatibilityMode: powerBI\n\tlanguage: 1033\n")
    for name, spec in TABLES.items():
        write_text(tables_dir / f"{name}.tmdl", tmdl_table(name, spec))
    write_json(MODEL / "definition.pbism", {"version": "4.2", "settings": {"qnaEnabled": True}})
    write_json(MODEL / "diagramLayout.json", {"version": "1.1.0", "diagrams": []})


def write_page(page_name: str, display_name: str, visuals: list[dict]) -> None:
    page_dir = PAGES / page_name
    write_json(page_dir / "page.json", page_definition(page_name, display_name))
    for visual in visuals:
        write_json(page_dir / "visuals" / visual["name"] / "visual.json", visual)


def build_report() -> None:
    write_json(PROJECT / "RetentionAnalysis.pbip", {"version": "1.0", "artifacts": [{"report": {"path": "RetentionAnalysis.Report"}}], "settings": {"enableAutoRecovery": True}})
    write_json(REPORT / "definition.pbir", {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json", "version": "4.0", "datasetReference": {"byPath": {"path": "../RetentionAnalysis.SemanticModel"}}})
    write_json(REPORT / "definition" / "version.json", {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json", "version": "2.0.0"})
    write_json(REPORT / "definition" / "report.json", {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/3.3.0/schema.json",
        "themeCollection": {"baseTheme": {"name": "CY24SU10", "reportVersionAtImport": {"visual": "2.1.0", "report": "3.0.0", "page": "2.0.0"}, "type": "SharedResources"}},
        "settings": {"useStylableVisualContainerHeader": True, "useEnhancedTooltips": True, "exportDataMode": "AllowSummarized"},
    })

    page1 = "01retentionoverview000"
    page2 = "02segmentdecision0000"
    page3 = "03crmpriority000000"
    write_json(PAGES / "pages.json", {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json", "pageOrder": [page1, page2, page3], "activePageName": page1})

    write_page(page1, "Retention overview", [
        textbox("p1title0000000000000", 40, 24, 1500, 56, "How healthy is repeat customer revenue?"),
        card("p1cardcustomers00000", 40, 112, 448, "headline_kpis", "Total customers", "Customers analyzed", 200),
        card("p1cardrepeat0000000", 504, 112, 448, "headline_kpis", "Repeat revenue share", "Repeat revenue share", 210),
        card("p1cardm100000000000", 968, 112, 448, "headline_kpis", "M1 retention", "M1 retention", 220),
        card("p1cardm600000000000", 1432, 112, 448, "headline_kpis", "M6 retention", "M6 retention", 230),
        chart("p1line0000000000000", "lineChart", 40, 280, 900, 344, ("monthly_metrics", "Month"), ("monthly_metrics", "Monthly repeat revenue share"), "Monthly repeat-revenue share", BLUE, 300),
        chart("p1bar00000000000000", "clusteredColumnChart", 968, 280, 912, 344, ("retention_horizons", "Horizon"), ("retention_horizons", "Weighted retention"), "Weighted retention at complete horizons", ORANGE, 310),
        cohort_heatmap("p1heatmap0000000000", 40, 648, 900, 376, "Cohort retention heatmap (M1-M6; darker = higher)", 320),
        textbox("p1note0000000000000", 992, 680, 840, 260, "Repeat orders generate most observed revenue, but only about one quarter of acquired customers return at M1. M3 can exceed M1 because customers may skip a month and return later; retention is not cumulative.", 18, False),
    ])

    write_page(page2, "Segment decision", [
        textbox("p2title0000000000000", 40, 24, 1600, 56, "Which customer segments should CRM prioritize?"),
        card("p2cardtarget0000000", 40, 112, 448, "priority_kpis", "Target customers", "High-value risk customers", 200),
        card("p2cardrevenue000000", 504, 112, 448, "priority_kpis", "Target historical revenue", "Historical revenue in target groups", 210),
        card("p2cardriskrate00000", 968, 112, 448, "priority_kpis", "At-risk backtest rate", "At-risk 12m repurchase rate", 220),
        card("p2cardlapsedrate000", 1432, 112, 448, "priority_kpis", "Lapsed backtest rate", "Lapsed 12m repurchase rate", 230),
        chart("p2barbacktest000000", "clusteredBarChart", 40, 280, 900, 344, ("rfm_backtest", "Segment"), ("rfm_backtest", "Backtest repeat rate"), "Historical 12-month repurchase rate", ORANGE, 300),
        chart("p2barcurrent0000000", "clusteredBarChart", 968, 280, 912, 344, ("rfm_segments", "Segment"), ("rfm_segments", "Trailing revenue"), "Current trailing revenue by segment", BLUE, 310),
        table_visual("p2table000000000000", 40, 648, 1180, 376, [("segment_decision", "Segment", "column"), ("segment_decision", "Customers", "column"), ("segment_decision", "Trailing revenue", "column"), ("segment_decision", "Average recency days", "column"), ("segment_decision", "Backtest repeat rate", "column")], "Segment evidence", 320),
        textbox("p2note0000000000000", 1260, 680, 580, 260, "Primary action: retain High-Value At Risk customers while their historical repurchase rate remains relatively strong. Use a separate, lower-cost reactivation test for High-Value Lapsed customers.", 18, False),
    ])

    write_page(page3, "CRM priorities", [
        textbox("p3title0000000000000", 40, 24, 1600, 56, "Where should the first CRM pilot focus?"),
        card("p3cardukcustomers000", 40, 112, 448, "priority_kpis", "UK target customers", "UK target customers", 200),
        card("p3cardukrevenue0000", 504, 112, 448, "priority_kpis", "UK target revenue", "UK target historical revenue", 210),
        card("p3cardatrisk0000000", 968, 112, 448, "priority_kpis", "At-risk customers", "High-Value At Risk", 220),
        card("p3cardlapsed0000000", 1432, 112, 448, "priority_kpis", "Lapsed customers", "High-Value Lapsed", 230),
        chart("p3barcountry0000000", "clusteredBarChart", 40, 280, 900, 344, ("country_priority", "Country"), ("country_priority", "Market target revenue"), "Historical target revenue by market", BLUE, 300),
        chart("p3barproduct0000000", "clusteredBarChart", 968, 280, 912, 344, ("product_affinity", "Product"), ("product_affinity", "Product target customers"), "Products familiar to target customers", ORANGE, 310),
        table_visual("p3table000000000000", 40, 648, 1000, 376, [("country_priority", "Country", "column"), ("country_priority", "Customers", "column"), ("country_priority", "Target customers", "column"), ("country_priority", "Target customer share", "column"), ("country_priority", "Target historical revenue", "column")], "Markets with at least 20 active customers", 320),
        textbox("p3note0000000000000", 1080, 680, 760, 260, "Start in the United Kingdom because it contains most target customers and target historical revenue. Use previously purchased products as offer context, not as proof that a specific product will cause repurchase. Treat smaller markets as exploratory due to limited sample sizes.", 18, False),
    ])


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the local Power BI project.")
    parser.add_argument(
        "--data-folder",
        type=Path,
        default=Path("C:/path/to/online-retail-retention-analysis/data/powerbi"),
        help="Folder containing the prepared Power BI CSV files.",
    )
    args = parser.parse_args()
    if PROJECT.exists():
        shutil.rmtree(PROJECT)
    build_model(args.data_folder)
    build_report()
    print(f"Power BI project: {PROJECT / 'RetentionAnalysis.pbip'}")


if __name__ == "__main__":
    main()
