import io
from typing import Dict, Any, List
import pandas as pd
from models.result_models import (
    DatasetProfile,
    CleaningReport,
    AnalysisReport,
    AnomalyReport,
    OverallPipelineResult
)

def generate_non_ai_summary(
    domain: str,
    profile: DatasetProfile,
    cleaning: CleaningReport,
    analysis: AnalysisReport,
    anomaly: AnomalyReport
) -> str:
    """
    Generates a clear, deterministic natural-language executive summary based on calculated data facts.
    """
    summary_parts = []
    summary_parts.append(
        f"DataCleaning4U Executive Summary for target domain: **{domain}**.\n\n"
    )
    summary_parts.append(
        f"The uploaded dataset **'{profile.file_name}'** contains **{profile.total_rows:,} records** across **{profile.total_columns} columns** "
        f"({len(profile.numerical_columns)} numerical, {len(profile.categorical_columns)} categorical, "
        f"{len(profile.datetime_columns)} datetime, and {len(profile.identifier_columns)} identifier column(s)).\n\n"
    )

    # Cleaning findings
    summary_parts.append(
        f"**Data Cleaning Results:**\n"
        f"- Duplicate Rows Removed: **{cleaning.duplicates_removed}**\n"
        f"- Missing Values Handled: **{cleaning.total_missing_handled}** value(s) imputed across columns.\n"
        f"- Data Type Conversions: **{len(cleaning.datatype_conversions)}** column(s) successfully converted.\n"
        f"- Final Processed Dataset: **{cleaning.rows_after:,} rows** and **{cleaning.cols_after} columns**.\n\n"
    )

    # Key Statistical Insights
    summary_parts.append("**Key Statistical Findings:**\n")
    if analysis.group_aggregations and "top_group" in analysis.group_aggregations:
        grp = analysis.group_aggregations
        top = grp["top_group"]
        summary_parts.append(
            f"- Highest Performance Group: In category **'{grp.get('grouped_by')}'**, **'{top.get('category')}'** achieved the highest cumulative total of **{top.get('total_sum'):,}** for metric **'{grp.get('target_metric')}'** (average: {top.get('mean'):,}).\n"
        )

    if analysis.trends and "trend_direction" in analysis.trends:
        tr = analysis.trends
        summary_parts.append(
            f"- Chronological Trend: Primary metric **'{tr.get('metric_column')}'** exhibits a **{tr.get('trend_direction')}** trend ({tr.get('percentage_change')}% change) from {tr.get('start_date')} to {tr.get('end_date')}.\n"
        )

    # Anomalies
    summary_parts.append(
        f"\n**Anomaly & Data Quality Audit:**\n"
        f"- Detected **{anomaly.total_anomalies_found} statistical outlier observation(s)** and **{len(anomaly.data_quality_issues)} data quality issue(s)**.\n"
    )
    if anomaly.statistical_anomalies:
        top_anom = anomaly.statistical_anomalies[0]
        summary_parts.append(
            f"- Notable Anomaly: {top_anom.explanation}\n"
        )

    summary_parts.append(
        "\n*All observations are structured and prepared for optional downstream LLM explanation.*"
    )

    return "".join(summary_parts)

def generate_html_report(pipeline_result: OverallPipelineResult) -> str:
    """
    Generates a modern, standalone HTML report for download.
    """
    p = pipeline_result.profile
    c = pipeline_result.cleaning_report
    a = pipeline_result.analysis_report
    anom = pipeline_result.anomaly_report

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DataCleaning4U Audit Report - {p.file_name}</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #F8FAFC; color: #0F172A; margin: 0; padding: 40px; }}
        .container {{ max-width: 900px; margin: 0 auto; background: #FFFFFF; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); padding: 40px; }}
        .header {{ border-bottom: 2px solid #E2E8F0; padding-bottom: 20px; margin-bottom: 30px; }}
        .header h1 {{ color: #4F46E5; margin: 0 0 10px 0; font-size: 28px; }}
        .header p {{ color: #64748B; margin: 0; font-size: 14px; }}
        .card-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 30px; }}
        .card {{ background: #F1F5F9; border-radius: 8px; padding: 20px; text-align: center; }}
        .card .number {{ font-size: 24px; font-weight: bold; color: #4F46E5; }}
        .card .label {{ font-size: 12px; color: #64748B; text-transform: uppercase; margin-top: 5px; }}
        h2 {{ color: #1E293B; border-bottom: 1px solid #E2E8F0; padding-bottom: 8px; margin-top: 30px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 14px; }}
        th, td {{ padding: 10px 14px; border: 1px solid #E2E8F0; text-align: left; }}
        th {{ background: #F8FAFC; color: #475569; font-weight: 600; }}
        .badge {{ background: #EEF2FF; color: #4F46E5; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }}
        .footer {{ margin-top: 40px; text-align: center; font-size: 12px; color: #94A3B8; border-top: 1px solid #E2E8F0; padding-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>DataCleaning4U Executive Report</h1>
            <p>Domain: <strong>{pipeline_result.domain}</strong> | Dataset: <strong>{p.file_name}</strong> | Generated automatically</p>
        </div>

        <div class="card-grid">
            <div class="card">
                <div class="number">{c.rows_after:,}</div>
                <div class="label">Cleaned Rows (Before: {c.rows_before:,})</div>
            </div>
            <div class="card">
                <div class="number">{c.total_missing_handled}</div>
                <div class="label">Missing Handled</div>
            </div>
            <div class="card">
                <div class="number">{anom.total_anomalies_found}</div>
                <div class="label">Outliers Flagged</div>
            </div>
        </div>

        <h2>Executive Summary</h2>
        <p style="line-height: 1.6; color: #334155;">{pipeline_result.summary_text.replace('\n', '<br>')}</p>

        <h2>Dataset Profile Summary</h2>
        <table>
            <thead>
                <tr>
                    <th>Column Name</th>
                    <th>Inferred Type</th>
                    <th>Missing Count</th>
                    <th>Unique Values</th>
                </tr>
            </thead>
            <tbody>
"""
    for col_name, col_prof in p.columns.items():
        html_content += f"""
                <tr>
                    <td><strong>{col_name}</strong></td>
                    <td><span class="badge">{col_prof.inferred_type}</span></td>
                    <td>{col_prof.missing_count} ({col_prof.missing_percentage}%)</td>
                    <td>{col_prof.unique_count}</td>
                </tr>
"""

    html_content += """
            </tbody>
        </table>

        <h2>Data Cleaning Operations</h2>
        <ul>
"""
    for step in c.cleaning_steps:
        html_content += f"<li><strong>{step['step']}</strong>: {', '.join(step['details'])}</li>"

    html_content += f"""
        </ul>

        <div class="footer">
            Report generated by DataCleaning4U &copy; 2026. From raw data to useful insights.
        </div>
    </div>
</body>
</html>
"""
    return html_content

def generate_pdf_report_bytes(pipeline_result: OverallPipelineResult) -> bytes:
    """
    Generates downloadable PDF report using ReportLab.
    """
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Heading1'],
            fontSize=22,
            leading=26,
            textColor=colors.HexColor('#4F46E5'),
            spaceAfter=12
        )
        heading_style = ParagraphStyle(
            'DocHeading',
            parent=styles['Heading2'],
            fontSize=14,
            leading=18,
            textColor=colors.HexColor('#1E293B'),
            spaceBefore=12,
            spaceAfter=6
        )
        body_style = ParagraphStyle(
            'DocBody',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#334155')
        )

        elements = []
        elements.append(Paragraph("DataCleaning4U Executive Report", title_style))
        elements.append(Paragraph(f"<b>Domain:</b> {pipeline_result.domain} | <b>File:</b> {pipeline_result.profile.file_name}", body_style))
        elements.append(Spacer(1, 12))

        # Metrics Table
        c = pipeline_result.cleaning_report
        anom = pipeline_result.anomaly_report
        summary_data = [
            ["Cleaned Rows", "Duplicates Removed", "Missing Handled", "Outliers Flagged"],
            [f"{c.rows_after:,}", f"{c.duplicates_removed}", f"{c.total_missing_handled}", f"{anom.total_anomalies_found}"]
        ]
        t = Table(summary_data, colWidths=[130, 130, 130, 130])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#EEF2FF')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#4F46E5')),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0'))
        ]))
        elements.append(t)
        elements.append(Spacer(1, 14))

        elements.append(Paragraph("Executive Summary", heading_style))
        for line in pipeline_result.summary_text.split('\n'):
            if line.strip():
                elements.append(Paragraph(line.replace('**', '<b>').replace('**', '</b>'), body_style))
                elements.append(Spacer(1, 4))

        elements.append(Spacer(1, 10))
        elements.append(Paragraph("Column Classification", heading_style))

        col_table_data = [["Column", "Type", "Missing", "Unique"]]
        for col_name, col_prof in list(pipeline_result.profile.columns.items())[:15]:
            col_table_data.append([col_name, col_prof.inferred_type, str(col_prof.missing_count), str(col_prof.unique_count)])

        ct = Table(col_table_data, colWidths=[160, 120, 120, 120])
        ct.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F8FAFC')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#475569')),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0'))
        ]))
        elements.append(ct)

        doc.build(elements)
        buffer.seek(0)
        return buffer.read()
    except Exception as e:
        # Fallback if ReportLab formatting fails
        return f"PDF Generation Warning: {str(e)}".encode('utf-8')
