import csv
import io
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime
import os

class ExportService:
    """Service for exporting reports in various formats"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        
    def export_to_csv(self, data, filename=None):
        """Export report data to CSV"""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow(['Date', 'Type', 'Category', 'Description', 'Payment Method', 'Amount (KES)', 'M-Pesa Code'])
        
        # Write transactions
        for t in data.get('transactions', []):
            writer.writerow([
                t.get('date', ''),
                t.get('type', '').capitalize(),
                self._get_category_name(t.get('category_id')),
                t.get('description', ''),
                t.get('payment_method', '').capitalize(),
                f"{t.get('amount', 0):,.2f}",
                t.get('mpesa_code', '')
            ])
        
        # Add summary at the end
        writer.writerow([])
        writer.writerow(['SUMMARY'])
        writer.writerow(['Period:', f"{data.get('from_date', '')} to {data.get('to_date', '')}"])
        writer.writerow(['Total Income:', f"KES {data['summary']['income']:,.2f}"])
        writer.writerow(['Total Expense:', f"KES {data['summary']['expense']:,.2f}"])
        writer.writerow(['Net Balance:', f"KES {data['summary']['net']:,.2f}"])
        writer.writerow(['Transaction Count:', data['summary']['transaction_count']])
        
        # Get the value
        csv_data = output.getvalue()
        output.close()
        
        return csv_data
    
    def export_to_excel(self, data, filename=None):
        """Export report data to Excel"""
        output = io.BytesIO()
        
        # Create a Pandas Excel writer
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Transactions sheet
            transactions_data = []
            for t in data.get('transactions', []):
                transactions_data.append({
                    'Date': t.get('date', ''),
                    'Type': t.get('type', '').capitalize(),
                    'Category': self._get_category_name(t.get('category_id')),
                    'Description': t.get('description', ''),
                    'Payment Method': t.get('payment_method', '').capitalize(),
                    'Amount (KES)': t.get('amount', 0),
                    'M-Pesa Code': t.get('mpesa_code', '')
                })
            
            df_transactions = pd.DataFrame(transactions_data)
            df_transactions.to_excel(writer, sheet_name='Transactions', index=False)
            
            # Summary sheet
            summary_data = {
                'Metric': ['Period', 'Total Income', 'Total Expense', 'Net Balance', 'Transaction Count'],
                'Value': [
                    f"{data.get('from_date', '')} to {data.get('to_date', '')}",
                    f"KES {data['summary']['income']:,.2f}",
                    f"KES {data['summary']['expense']:,.2f}",
                    f"KES {data['summary']['net']:,.2f}",
                    data['summary']['transaction_count']
                ]
            }
            df_summary = pd.DataFrame(summary_data)
            df_summary.to_excel(writer, sheet_name='Summary', index=False)
            
            # Category breakdown sheet
            category_data = []
            for cat_id, cat_info in data.get('category_breakdown', {}).items():
                category_data.append({
                    'Category': cat_info['name'],
                    'Type': cat_info['type'].capitalize(),
                    'Income': cat_info['income'],
                    'Expense': cat_info['expense'],
                    'Transactions': cat_info['count']
                })
            
            if category_data:
                df_categories = pd.DataFrame(category_data)
                df_categories.to_excel(writer, sheet_name='Categories', index=False)
        
        excel_data = output.getvalue()
        output.close()
        
        return excel_data
    
    def export_to_pdf(self, data, business_name=None, filename=None):
        """Export report data to PDF"""
        buffer = io.BytesIO()
        
        # Create the PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72,
        )
        
        # Container for the 'Flowable' objects
        elements = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1,  # Center alignment
            textColor=colors.HexColor('#667eea')
        )
        
        title = Paragraph(f"LedgerMate Financial Report", title_style)
        elements.append(title)
        
        # Business name
        if business_name:
            business_style = ParagraphStyle(
                'Business',
                parent=self.styles['Normal'],
                fontSize=16,
                spaceAfter=20,
                alignment=1,
                textColor=colors.HexColor('#764ba2')
            )
            elements.append(Paragraph(business_name, business_style))
        
        # Period
        period_text = f"Period: {data.get('from_date', '')} to {data.get('to_date', '')}"
        elements.append(Paragraph(period_text, self.styles['Normal']))
        elements.append(Spacer(1, 20))
        
        # Summary Section
        elements.append(Paragraph("Summary", self.styles['Heading2']))
        elements.append(Spacer(1, 10))
        
        summary_data = [
            ['Metric', 'Amount (KES)'],
            ['Total Income', f"{data['summary']['income']:,.2f}"],
            ['Total Expense', f"{data['summary']['expense']:,.2f}"],
            ['Net Balance', f"{data['summary']['net']:,.2f}"],
            ['Transaction Count', str(data['summary']['transaction_count'])]
        ]
        
        summary_table = Table(summary_data, colWidths=[200, 200])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (2, 2), (2, 2), colors.HexColor('#27ae60') if data['summary']['net'] >= 0 else colors.HexColor('#e74c3c')),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 30))
        
        # Category Breakdown
        elements.append(Paragraph("Category Breakdown", self.styles['Heading2']))
        elements.append(Spacer(1, 10))
        
        category_table_data = [['Category', 'Type', 'Income', 'Expense', 'Count']]
        
        for cat_id, cat_info in data.get('category_breakdown', {}).items():
            category_table_data.append([
                cat_info['name'],
                cat_info['type'].capitalize(),
                f"{cat_info['income']:,.2f}",
                f"{cat_info['expense']:,.2f}",
                str(cat_info['count'])
            ])
        
        if len(category_table_data) > 1:
            category_table = Table(category_table_data, colWidths=[100, 80, 100, 100, 60])
            category_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#764ba2')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('FONTNAME', (0, 1), (0, -1), 'Helvetica'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(category_table)
            elements.append(Spacer(1, 30))
        
        # Transactions
        elements.append(Paragraph("Transaction Details", self.styles['Heading2']))
        elements.append(Spacer(1, 10))
        
        transaction_table_data = [['Date', 'Type', 'Category', 'Description', 'Payment', 'Amount']]
        
        for t in data.get('transactions', [])[:50]:  # Limit to 50 transactions for PDF
            transaction_table_data.append([
                t.get('date', ''),
                'INC' if t.get('type') == 'income' else 'EXP',
                self._get_category_name(t.get('category_id'))[:15],
                (t.get('description', '') or '')[:20],
                t.get('payment_method', '')[:5],
                f"{t.get('amount', 0):,.2f}"
            ])
        
        if len(transaction_table_data) > 50:
            elements.append(Paragraph(f"Showing 50 of {len(data.get('transactions', []))} transactions", 
                                     self.styles['Italic']))
        
        transaction_table = Table(transaction_table_data, colWidths=[70, 40, 80, 100, 60, 80])
        transaction_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(transaction_table)
        
        # Footer with generation time
        elements.append(Spacer(1, 30))
        footer_text = f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')} by LedgerMate"
        elements.append(Paragraph(footer_text, self.styles['Italic']))
        
        # Build PDF
        doc.build(elements)
        
        pdf_data = buffer.getvalue()
        buffer.close()
        
        return pdf_data
    
    def _get_category_name(self, category_id):
        """Get category name by ID"""
        from app.models import Category
        category = Category.query.get(category_id)
        return category.name if category else 'Unknown'
    
    def get_filename(self, prefix, extension, data=None):
        """Generate filename for export"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if data and 'from_date' in data and 'to_date' in data:
            period = f"{data['from_date']}_to_{data['to_date']}"
            return f"{prefix}_{period}_{timestamp}.{extension}"
        
        return f"{prefix}_{timestamp}.{extension}"

# Create singleton instance
export_service = ExportService()