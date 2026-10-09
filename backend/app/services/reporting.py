from __future__ import annotations

from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.models import Project

PINE = colors.HexColor("#1D5C45")
INK = colors.HexColor("#18201D")
MUTED = colors.HexColor("#66706C")
CANVAS = colors.HexColor("#F5F7F4")
AMBER = colors.HexColor("#D28A39")


def _text(value: Any) -> str:
    return escape(str(value if value is not None else "Not available"))


def _metric(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.4f}"
    if isinstance(value, (dict, list)):
        return f"{len(value)} item(s)"
    return str(value)


def _table(rows: list[list[Any]], widths: list[float] | None = None, header: bool = True) -> Table:
    table = Table(rows, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TEXTCOLOR", (0, 0), (-1, -1), INK),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#DDE2DF")),
        ("ROWBACKGROUNDS", (0, 1 if header else 0), (-1, -1), [colors.white, CANVAS]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if header:
        commands.extend([
            ("BACKGROUND", (0, 0), (-1, 0), PINE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ])
    table.setStyle(TableStyle(commands))
    return table


def _page(canvas, doc) -> None:
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#DDE2DF"))
    canvas.line(doc.leftMargin, 0.55 * inch, letter[0] - doc.rightMargin, 0.55 * inch)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(doc.leftMargin, 0.36 * inch, "InsightFlow analytical report")
    canvas.drawRightString(letter[0] - doc.rightMargin, 0.36 * inch, f"Page {doc.page}")
    canvas.restoreState()


def build_project_report(project: Project, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=25, leading=30, textColor=PINE, alignment=TA_CENTER, spaceAfter=10))
    styles.add(ParagraphStyle(name="Section", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=15, leading=19, textColor=PINE, spaceBefore=12, spaceAfter=8))
    styles.add(ParagraphStyle(name="Subsection", parent=styles["Heading3"], fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=INK, spaceBefore=8, spaceAfter=5))
    styles.add(ParagraphStyle(name="BodySmall", parent=styles["BodyText"], fontSize=9, leading=13, textColor=INK, spaceAfter=6))
    styles.add(ParagraphStyle(name="Note", parent=styles["BodyText"], fontSize=8, leading=11, textColor=MUTED, backColor=CANVAS, borderPadding=8, spaceBefore=6, spaceAfter=8))

    document = SimpleDocTemplate(
        str(destination), pagesize=letter, rightMargin=0.65 * inch, leftMargin=0.65 * inch,
        topMargin=0.65 * inch, bottomMargin=0.75 * inch,
        title=f"InsightFlow report - {project.name}", author="InsightFlow",
    )
    story: list[Any] = [
        Spacer(1, 0.25 * inch),
        Paragraph("InsightFlow", styles["ReportTitle"]),
        Paragraph(f"Project report: {_text(project.name)}", ParagraphStyle(name="Subtitle", parent=styles["Heading2"], alignment=TA_CENTER, textColor=INK, spaceAfter=8)),
        Paragraph(f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}", ParagraphStyle(name="Generated", parent=styles["BodySmall"], alignment=TA_CENTER, textColor=MUTED)),
        Spacer(1, 0.25 * inch),
        Paragraph("Project information", styles["Section"]),
        _table([
            ["Project", "Description", "Created"],
            [Paragraph(_text(project.name), styles["BodySmall"]), Paragraph(_text(project.description or "No description provided"), styles["BodySmall"]), project.created_at.strftime("%Y-%m-%d")],
        ], [1.55 * inch, 3.75 * inch, 1.0 * inch]),
        Paragraph("Dataset overview and data quality", styles["Section"]),
    ]

    if not project.datasets:
        story.append(Paragraph("No datasets have been uploaded to this project.", styles["Note"]))
    for dataset in project.datasets:
        story.extend([
            KeepTogether([
                Paragraph(_text(dataset.name), styles["Subsection"]),
                _table([
                    ["Status", "Rows", "Columns", "Missing cells", "Duplicates", "Quality"],
                    [dataset.status, _metric(dataset.row_count), _metric(dataset.column_count), _metric(dataset.missing_cells), _metric(dataset.duplicate_rows), f"{dataset.quality_score:.1f}/100" if dataset.quality_score is not None else "-"],
                ], [0.85 * inch, 0.8 * inch, 0.8 * inch, 1.05 * inch, 0.9 * inch, 0.9 * inch]),
            ]),
            Paragraph("; ".join(_text(issue) for issue in (dataset.quality_issues or ["Profile is not available yet."])), styles["Note"]),
        ])
        if dataset.columns:
            column_rows = [["Column", "Type", "Unique", "Missing"]]
            for column in dataset.columns:
                column_rows.append([Paragraph(_text(column.name), styles["BodySmall"]), column.data_type, str(column.unique_count), f"{column.missing_count} ({column.missing_percentage:.2f}%)"])
            story.extend([Paragraph("Column profile", styles["Subsection"]), _table(column_rows, [2.45 * inch, 1.1 * inch, 1.0 * inch, 1.35 * inch])])

    story.extend([PageBreak(), Paragraph("Saved visualizations", styles["Section"])])
    if project.visualizations:
        rows = [["Name", "Type", "X-axis", "Y-axis", "Group/color"]]
        for visualization in project.visualizations:
            rows.append([Paragraph(_text(visualization.name), styles["BodySmall"]), visualization.chart_type, _text(visualization.x_axis or "-"), _text(visualization.y_axis or "-"), _text(visualization.group_column or "-")])
        story.append(_table(rows, [1.7 * inch, 0.75 * inch, 1.3 * inch, 1.3 * inch, 1.3 * inch]))
        story.append(Paragraph("Visualization entries describe configurations saved from uploaded data; no placeholder charts are included.", styles["Note"]))
    else:
        story.append(Paragraph("No visualizations have been saved for this project.", styles["Note"]))

    story.append(Paragraph("Machine-learning experiments", styles["Section"]))
    if not project.experiments:
        story.append(Paragraph("No machine-learning experiments have been saved for this project.", styles["Note"]))
    for experiment in project.experiments:
        story.extend([
            Paragraph(_text(experiment.name), styles["Subsection"]),
            Paragraph(f"Task: {_text(experiment.task_type)} | Status: {_text(experiment.status)} | Target: {_text(experiment.target_column or 'Not applicable')}", styles["BodySmall"]),
        ])
        if experiment.metrics:
            metric_rows = [["Model", "Metrics", "Top model-derived features"]]
            for result in experiment.metrics:
                scalar_metrics = ", ".join(f"{_text(key)}: {_text(_metric(value))}" for key, value in result.metrics.items() if not isinstance(value, (dict, list))) or "No scalar metrics"
                importance = (result.explainability or {}).get("global_importance", [])[:5]
                important_features = ", ".join(f"{_text(item.get('feature'))} ({float(item.get('share', 0)) * 100:.1f}%)" for item in importance) or "Not available"
                metric_rows.append([Paragraph(_text(result.model_name), styles["BodySmall"]), Paragraph(scalar_metrics, styles["BodySmall"]), Paragraph(important_features, styles["BodySmall"])])
            story.append(_table(metric_rows, [1.35 * inch, 3.0 * inch, 2.0 * inch]))
        else:
            story.append(Paragraph("Metrics are not available for this experiment.", styles["Note"]))

    ready_datasets = [dataset for dataset in project.datasets if dataset.status == "ready"]
    completed_experiments = [experiment for experiment in project.experiments if experiment.status == "completed"]
    story.extend([
        Paragraph("Conclusions", styles["Section"]),
        Paragraph(
            f"This project contains {len(project.datasets)} dataset(s), of which {len(ready_datasets)} completed profiling; "
            f"{len(project.visualizations)} saved visualization(s); and {len(completed_experiments)} completed experiment(s). "
            "Review the documented quality issues before interpreting charts or model results. Model metrics and feature importance describe fitted-model performance and behavior, not causal effects.",
            styles["BodySmall"],
        ),
        Paragraph("Correlation indicates statistical association. Neither correlation nor model-derived feature importance establishes causation.", styles["Note"]),
    ])
    document.build(story, onFirstPage=_page, onLaterPages=_page)
