import io
from typing import Dict, Any, List, Optional
import pandas as pd
from models.result_models import (
    DatasetProfile,
    CleaningReport,
    AnalysisReport,
    AnomalyReport,
    OverallPipelineResult,
    TableSummary,
    Finding
)

def build_table_summary(
    table_name: str,
    profile: DatasetProfile,
    cleaning: CleaningReport,
    analysis: AnalysisReport,
    anomaly: AnomalyReport
) -> TableSummary:
    """
    Constructs a structured TableSummary object for a specific table or Excel worksheet.
    """
    # Calculate Data Quality Score (0 to 100)
    total_cells = profile.total_rows * profile.total_columns if profile.total_rows > 0 and profile.total_columns > 0 else 1
    total_missing = cleaning.total_missing_handled
    dq_deduction = min(50.0, (total_missing / total_cells) * 100 * 5)
    dup_deduction = min(30.0, (cleaning.duplicates_removed / max(1, cleaning.rows_before)) * 100 * 2)
    anom_deduction = min(20.0, anomaly.total_anomalies_found * 2)
    dq_score = max(10.0, round(100.0 - dq_deduction - dup_deduction - anom_deduction, 1))

    # Extract key metrics
    key_metrics = {}
    for col, s in list(analysis.numerical_summary.items())[:4]:
        key_metrics[col] = {
            "mean": s.get("mean"),
            "median": s.get("median"),
            "min": s.get("min"),
            "max": s.get("max"),
            "std": s.get("std")
        }

    # Recommended charts
    rec_charts = []
    if profile.datetime_columns and profile.numerical_columns:
        rec_charts.append(f"Line Chart ({profile.numerical_columns[0]} over time)")
    if profile.categorical_columns and profile.numerical_columns:
        rec_charts.append(f"Bar Chart ({profile.numerical_columns[0]} by {profile.categorical_columns[0]})")
    if len(profile.numerical_columns) >= 2:
        rec_charts.append("Correlation Heatmap")

    return TableSummary(
        table_name=table_name,
        total_rows=cleaning.rows_after,
        total_columns=cleaning.cols_after,
        data_quality_score=dq_score,
        key_metrics=key_metrics,
        top_findings=analysis.findings[:5],
        anomaly_count=anomaly.total_anomalies_found,
        recommended_charts=rec_charts
    )

def generate_non_ai_summary(
    domain: str,
    profile: DatasetProfile,
    cleaning: CleaningReport,
    analysis: AnalysisReport,
    anomaly: AnomalyReport,
    findings: Optional[List[Finding]] = None
) -> str:
    """
    Generates a deterministic, natural-language executive summary prioritizing:
    1. Overall dataset scale and data quality hygiene
    2. High-severity structured findings (trends, disparities, correlations)
    3. Anomaly audit and critical outliers
    4. Domain-specific performance takeaways
    """
    summary_parts = []
    summary_parts.append(
        f"### 📋 Executive Summary: {domain}\n\n"
    )
    summary_parts.append(
        f"The dataset **'{profile.file_name}'** was successfully ingested and cleaned, yielding **{cleaning.rows_after:,} valid records** across **{cleaning.cols_after} attributes** "
        f"({len(profile.numerical_columns)} numerical measures, {len(profile.categorical_columns)} categorical dimensions, "
        f"{len(profile.datetime_columns)} temporal fields, and {len(profile.identifier_columns)} identifier keys).\n\n"
    )

    # 1. Data Cleaning Audit
    summary_parts.append("**🧹 Data Hygiene & Cleaning Operations:**\n")
    summary_parts.append(
        f"- **Duplicates:** Detected and removed **{cleaning.duplicates_removed} duplicate row(s)**.\n"
        f"- **Missing Value Imputation:** Handled **{cleaning.total_missing_handled} missing cell(s)** across attributes.\n"
        f"- **Schema Conversions:** Standardized **{len(cleaning.datatype_conversions)} column(s)** into native numeric/datetime types.\n"
        f"- **Statistical Outliers:** Flagged **{cleaning.outliers_flagged_count} row(s)** for auditing without data loss.\n\n"
    )

    # 2. Key Machine-Readable Findings
    f_list = findings if findings is not None else analysis.findings
    if f_list:
        summary_parts.append("**🔍 Key Analytical Findings & Evidence:**\n")
        for f in f_list[:6]:
            icon = "📈" if f.type in ["TREND", "SIGNIFICANT_CHANGE"] else "📊" if f.type == "COMPARISON" else "🔗" if f.type == "CORRELATION" else "⚠️" if f.type == "ANOMALY" else "📌"
            summary_parts.append(
                f"- {icon} **{f.title}** ({f.severity} Priority):\n  {f.description}\n  *Evidence: {f.evidence}*\n"
            )
        summary_parts.append("\n")
    else:
        # Fallback to direct stats if findings list empty
        if analysis.group_aggregations and "top_group" in analysis.group_aggregations:
            grp = analysis.group_aggregations
            top = grp["top_group"]
            summary_parts.append(
                f"- **Categorical Benchmark:** Category **'{top.get('category')}'** lead cumulative **'{grp.get('target_metric')}'** with **{top.get('total_sum'):,.2f}** (avg: {top.get('mean'):,.2f}).\n"
            )
        if analysis.trends and "trend_direction" in analysis.trends:
            tr = analysis.trends
            summary_parts.append(
                f"- **Timeline Trend:** Primary measure **'{tr.get('metric_column')}'** showed a **{tr.get('trend_direction')}** trajectory ({tr.get('percentage_change'):+.1f}% change).\n"
            )

    # 3. Anomaly & Risk Audit
    summary_parts.append(
        f"**⚠️ Anomaly & Risk Audit:**\n"
        f"- **{anomaly.total_anomalies_found} statistical outlier(s)** detected across IQR, Z-Score, and Isolation Forest algorithms.\n"
        f"- **{len(anomaly.data_quality_issues)} potential data quality defect(s)** recorded.\n"
    )
    if anomaly.statistical_anomalies:
        top_anom = max(anomaly.statistical_anomalies, key=lambda x: x.score)
        summary_parts.append(
            f"- *Critical Outlier:* {top_anom.explanation}\n"
        )

    summary_parts.append(
        "\n---\n*This structured audit is generated autonomously from calculated statistical facts.*"
    )

    return "".join(summary_parts)

def generate_html_report(pipeline_result: OverallPipelineResult) -> str:
    """
    Generates a modern, comprehensive standalone HTML report for download.
    """
    p = pipeline_result.profile
    c = pipeline_result.cleaning_report
    a = pipeline_result.analysis_report
    anom = pipeline_result.anomaly_report
    findings = pipeline_result.findings or a.findings

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DC4X Audit Report - {p.file_name}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background: #0F172A; color: #F1F5F9; margin: 0; padding: 40px; line-height: 1.5; }}
        .container {{ max-width: 960px; margin: 0 auto; background: #1E293B; border-radius: 12px; box-shadow: 0 4px 24px rgba(0,0,0,0.4); padding: 40px; border: 1px solid #334155; }}
        .header {{ border-bottom: 2px solid #334155; padding-bottom: 20px; margin-bottom: 30px; }}
        .header h1 {{ color: #00E5FF; margin: 0 0 8px 0; font-size: 30px; font-weight: 800; }}
        .header p {{ color: #94A3B8; margin: 0; font-size: 15px; font-weight: 500; }}
        .card-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 30px; }}
        .card {{ background: #0F172A; border: 1px solid #334155; border-radius: 8px; padding: 18px; text-align: center; }}
        .card .number {{ font-size: 24px; font-weight: 700; color: #00E5FF; }}
        .card .label {{ font-size: 12px; color: #94A3B8; text-transform: uppercase; margin-top: 4px; font-weight: 600; letter-spacing: 0.5px; }}
        h2 {{ color: #F1F5F9; border-bottom: 1px solid #334155; padding-bottom: 8px; margin-top: 35px; font-size: 20px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 14px; }}
        th, td {{ padding: 10px 14px; border: 1px solid #334155; text-align: left; }}
        th {{ background: #0F172A; color: #00E5FF; font-weight: 600; }}
        .badge {{ background: #1E1B4B; color: #818CF8; padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }}
        .badge-high {{ background: #450A0A; color: #F87171; padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }}
        .badge-med {{ background: #451A03; color: #FBBF24; padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }}
        .badge-info {{ background: #082F49; color: #38BDF8; padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }}
        .finding-card {{ background: #0F172A; border-left: 4px solid #00E5FF; border-radius: 0 8px 8px 0; padding: 16px; margin-bottom: 14px; border: 1px solid #334155; border-left-width: 4px; }}
        .finding-title {{ font-size: 15px; font-weight: 700; color: #F1F5F9; margin-bottom: 6px; }}
        .finding-desc {{ font-size: 14px; color: #CBD5E1; margin-bottom: 6px; }}
        .finding-evidence {{ font-size: 12px; color: #94A3B8; font-style: italic; }}
        .footer {{ margin-top: 50px; text-align: center; font-size: 13px; color: #64748B; border-top: 1px solid #334155; padding-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>DC4X Executive Audit Report</h1>
            <p><strong>Data Cleaning For You</strong> | Domain: <strong>{pipeline_result.domain}</strong> | Dataset: <strong>{p.file_name}</strong> {f'(Sheet: {pipeline_result.sheet_name})' if pipeline_result.sheet_name else ''}</p>
        </div>

        <div class="card-grid">
            <div class="card">
                <div class="number">{c.rows_after:,}</div>
                <div class="label">Cleaned Records</div>
            </div>
            <div class="card">
                <div class="number">{c.duplicates_removed}</div>
                <div class="label">Duplicates Removed</div>
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

        <h2>1. Executive Summary</h2>
        <div style="background: #F1F5F9; padding: 20px; border-radius: 8px; border-left: 4px solid #10B981;">
            {pipeline_result.summary_text.replace(chr(10), '<br>')}
        </div>

        <h2>2. Key Structured Findings</h2>
"""
    if findings:
        for f in findings:
            badge_class = "badge-high" if f.severity == "High" else "badge-med" if f.severity == "Medium" else "badge-info"
            html_content += f"""
        <div class="finding-card">
            <div class="finding-title">
                <span class="{badge_class}">{f.severity}</span> <strong>{f.title}</strong> [{f.type}]
            </div>
            <div class="finding-desc">{f.description}</div>
            <div class="finding-evidence">Evidence: {f.evidence}</div>
        </div>
"""
    else:
        html_content += "<p>No notable findings generated for this dataset.</p>"

    html_content += """
        <h2>3. Dataset Profiling & Taxonomy</h2>
        <table>
            <thead>
                <tr>
                    <th>Column Name</th>
                    <th>Inferred Type</th>
                    <th>Role</th>
                    <th>Missing Count</th>
                    <th>Unique Values</th>
                    <th>Suitability</th>
                </tr>
            </thead>
            <tbody>
"""
    for col_name, col_prof in p.columns.items():
        suit_flags = []
        if col_prof.suitable_for_measurement:
            suit_flags.append("Measure")
        if col_prof.suitable_for_grouping:
            suit_flags.append("Group")
        if col_prof.suitable_for_timeseries:
            suit_flags.append("Time")
        suit_str = ", ".join(suit_flags) if suit_flags else "General"

        html_content += f"""
                <tr>
                    <td><strong>{col_name}</strong></td>
                    <td><span class="badge">{col_prof.inferred_type}</span></td>
                    <td>{col_prof.role}</td>
                    <td>{col_prof.missing_count} ({col_prof.missing_percentage}%)</td>
                    <td>{col_prof.unique_count}</td>
                    <td>{suit_str}</td>
                </tr>
"""

    html_content += """
            </tbody>
        </table>

        <h2>4. Data Cleaning Audit Trail</h2>
        <ul>
"""
    for step in c.cleaning_steps:
        html_content += f"<li><strong>{step['step']}</strong>: {', '.join(step['details'])}</li>"

    html_content += f"""
        </ul>

        <h2>5. Anomaly & Risk Observations</h2>
        <table>
            <thead>
                <tr>
                    <th>Method</th>
                    <th>Column</th>
                    <th>Row</th>
                    <th>Observed Value</th>
                    <th>Explanation</th>
                </tr>
            </thead>
            <tbody>
"""
    for item in anom.statistical_anomalies[:12]:
        html_content += f"""
                <tr>
                    <td><span class="badge">{item.method}</span></td>
                    <td><strong>{item.column}</strong></td>
                    <td>{item.row_index}</td>
                    <td>{item.value}</td>
                    <td>{item.explanation}</td>
                </tr>
"""
    html_content += f"""
            </tbody>
        </table>

        <div class="footer">
            Generated by DC4X (Data Cleaning For You) &copy; 2026.
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
            fontSize=20,
            leading=24,
            textColor=colors.HexColor('#00E5FF'),
            spaceAfter=8
        )
        heading_style = ParagraphStyle(
            'DocHeading',
            parent=styles['Heading2'],
            fontSize=13,
            leading=16,
            textColor=colors.HexColor('#1E293B'),
            spaceBefore=12,
            spaceAfter=6
        )
        body_style = ParagraphStyle(
            'DocBody',
            parent=styles['Normal'],
            fontSize=9,
            leading=13,
            textColor=colors.HexColor('#334155')
        )
        finding_style = ParagraphStyle(
            'DocFinding',
            parent=styles['Normal'],
            fontSize=9,
            leading=13,
            textColor=colors.HexColor('#0F172A'),
            spaceAfter=4
        )

        elements = []
        elements.append(Paragraph("DC4X Executive Audit Report", title_style))
        elements.append(Paragraph(f"<b>Data Cleaning For You</b> | <b>Domain:</b> {pipeline_result.domain} | <b>File:</b> {pipeline_result.profile.file_name}", body_style))
        elements.append(Spacer(1, 10))

        # Metrics Card Table
        c = pipeline_result.cleaning_report
        anom = pipeline_result.anomaly_report
        summary_data = [
            ["Cleaned Rows", "Duplicates Removed", "Missing Imputed", "Outliers Flagged"],
            [f"{c.rows_after:,}", f"{c.duplicates_removed}", f"{c.total_missing_handled}", f"{anom.total_anomalies_found}"]
        ]
        t = Table(summary_data, colWidths=[135, 135, 135, 135])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#EEF2FF')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#4F46E5')),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0'))
        ]))
        elements.append(t)
        elements.append(Spacer(1, 12))

        # Structured Findings Section
        elements.append(Paragraph("Key Structured Findings", heading_style))
        findings = pipeline_result.findings or pipeline_result.analysis_report.findings
        for f in findings[:5]:
            f_text = f"<b>[{f.severity}] {f.title}</b><br/>{f.description}<br/><i>Evidence: {f.evidence}</i>"
            elements.append(Paragraph(f_text, finding_style))
            elements.append(Spacer(1, 4))

        elements.append(Spacer(1, 8))
        elements.append(Paragraph("Column Classifications", heading_style))

        col_table_data = [["Column", "Inferred Type", "Role", "Missing", "Unique"]]
        for col_name, col_prof in list(pipeline_result.profile.columns.items())[:12]:
            col_table_data.append([
                col_name,
                col_prof.inferred_type,
                col_prof.role,
                f"{col_prof.missing_count} ({col_prof.missing_percentage}%)",
                str(col_prof.unique_count)
            ])

        ct = Table(col_table_data, colWidths=[130, 95, 95, 110, 110])
        ct.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F8FAFC')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#475569')),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0'))
        ]))
        elements.append(ct)

        doc.build(elements)
        buffer.seek(0)
        return buffer.read()
    except Exception as e:
        return f"PDF Generation Notice: {str(e)}".encode('utf-8')
