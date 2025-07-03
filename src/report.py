# src/report.py (Slightly Improved Version)

import pandas as pd
import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image, 
                                PageBreak, Table, TableStyle, ListFlowable, ListItem)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from src import analysis

def generate_pdf_report_phase2(
    system_info, insights, analysis_df, conclusion_text_list,
    sensor_health_plot_buf, weather_analysis_plot_buf,
    system_performance_plot_buf, yield_analysis_plot_buf,
    guarantee_plot_buf, overall_loss_breakdown_plot_buf, # Assuming you might add these later
    latest_month_loss_breakdown_plot_buf, forecast_plot_buf
):
    """
    Generates a PDF report for the Studio OM V2 analysis results.
    """
    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=letter,
                          rightMargin=72, leftMargin=72,
                          topMargin=72, bottomMargin=18)
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Justify', alignment=4)) # Justify text
    styles.add(ParagraphStyle(name='H4_custom', parent=styles['h4'], spaceBefore=6, spaceAfter=6))


    story = []

    # --- Cover Page ---
    story.append(Paragraph("Studio OM V2 - Performance Analysis Report", styles['h1']))
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph(f"Project: {system_info.get('project_name', 'N/A')}", styles['h2']))
    story.append(Paragraph(f"Owner: {system_info.get('owner_name', 'N/A')}", styles['h2']))
    story.append(Spacer(1, 2 * inch))
    story.append(Paragraph(f"Report Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    story.append(PageBreak())

    # --- Section 1: Executive Summary ---
    if conclusion_text_list:
        story.append(Paragraph("1. Executive Summary and Recommendations", styles['h2']))
        
        bullet_items = []
        for style_key, text in conclusion_text_list:
            # If a new section starts, render the previous bullet list first
            if style_key != 'bullet' and bullet_items:
                story.append(ListFlowable(bullet_items, bulletType='bullet', leftIndent=20, spaceBefore=5, spaceAfter=5))
                bullet_items = []

            if style_key == 'h3':
                story.append(Spacer(1, 0.2 * inch))
                story.append(Paragraph(text, styles['h3']))
            elif style_key == 'h4':
                # Special handling for our new forecast header
                if "Next Month Forecast" in text:
                    story.append(Spacer(1, 0.15 * inch))
                    story.append(Paragraph(text, styles['H4_custom']))
                else:
                    story.append(Paragraph(text, styles['h4']))
            elif style_key == 'bullet':
                # Use justified text for better look in PDF
                bullet_items.append(ListItem(Paragraph(text, styles['Justify']), value='-'))
            else: # 'body'
                story.append(Paragraph(text, styles['Justify']))
        
        # Render any remaining bullet items
        if bullet_items:
            story.append(ListFlowable(bullet_items, bulletType='bullet', leftIndent=20))
        
        story.append(PageBreak())

    # --- Section 2: Key Performance Insights ---
    story.append(Paragraph("2. Key Performance Insights", styles['h2']))
    summary_table_df = analysis.create_summary_table(insights)
    summary_table_data = [summary_table_df.columns.values.tolist()] + summary_table_df.values.tolist()
    summary_table = Table(summary_table_data, colWidths=[3.0 * inch, 3.5 * inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(summary_table)
    story.append(PageBreak())

    # --- Section 3: Performance Charts ---
    story.append(Paragraph("3. Performance Charts", styles['h2']))
    
    # You would need to pass these buffers from app_pages.py when calling this function
    if latest_month_loss_breakdown_plot_buf:
        story.append(Image(latest_month_loss_breakdown_plot_buf, width=6.5*inch, height=3.25*inch))
        story.append(Spacer(1, 0.2 * inch))
    if overall_loss_breakdown_plot_buf:
        story.append(Image(overall_loss_breakdown_plot_buf, width=6.5*inch, height=3.25*inch))
        story.append(PageBreak())

    if system_performance_plot_buf:
        story.append(Image(system_performance_plot_buf, width=6.5*inch, height=3.25*inch))
        story.append(Spacer(1, 0.2 * inch))
    if yield_analysis_plot_buf:
        story.append(Image(yield_analysis_plot_buf, width=6.5*inch, height=3.25*inch))
        story.append(PageBreak())

    if forecast_plot_buf:
        story.append(Paragraph("Long-term Forecast vs. Guarantee", styles['h3']))
        story.append(Image(forecast_plot_buf, width=6.5*inch, height=3.25*inch))
        story.append(PageBreak())

    # ... The rest of the report generation ...
    # ... (Detailed Data Table, etc.) ...

    doc.build(story)
    output.seek(0)
    return output