from flask import Blueprint, render_template, request, jsonify, send_file, session
from flask_login import login_required, current_user
from app.services.report_service import report_service
from app.services.export_service import export_service
from datetime import datetime
import io

bp = Blueprint('reports', __name__, url_prefix='/reports')

@bp.route('/')
@login_required
def reports():
    """Reports page"""
    return render_template('reports/reports.html')

@bp.route('/api/generate')
@login_required
def generate_report():
    """API endpoint to generate report"""
    try:
        # Get parameters
        period = request.args.get('period', 'monthly')
        transaction_type = request.args.get('type', 'all')
        category_id = request.args.get('category', 'all')
        
        # Parse dates for custom period
        from_date = None
        to_date = None
        if period == 'custom':
            from_date_str = request.args.get('from_date')
            to_date_str = request.args.get('to_date')
            
            if from_date_str:
                from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
            if to_date_str:
                to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date()
        
        # Generate report
        report = report_service.generate_report(
            user_id=current_user.id,
            period=period,
            from_date=from_date,
            to_date=to_date,
            transaction_type=transaction_type,
            category_id=category_id if category_id != 'all' else None
        )
        
        # Prepare chart data
        chart_data = {
            'labels': [],
            'income': [],
            'expense': []
        }
        
        for day in report.get('daily_breakdown', []):
            chart_data['labels'].append(day['date'][5:])  # MM-DD format
            chart_data['income'].append(day['income'])
            chart_data['expense'].append(day['expense'])
        
        return jsonify({
            'success': True,
            'summary': report['summary'],
            'category_breakdown': report['category_breakdown'],
            'transactions': report['transactions'],
            'chart_data': chart_data,
            'period': report['period'],
            'from_date': report['from_date'],
            'to_date': report['to_date']
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/export')
@login_required
def export_report():
    """Export report in specified format"""
    try:
        # Get parameters
        period = request.args.get('period', 'monthly')
        format_type = request.args.get('format', 'pdf')
        transaction_type = request.args.get('type', 'all')
        category_id = request.args.get('category', 'all')
        
        # Parse dates for custom period
        from_date = None
        to_date = None
        if period == 'custom':
            from_date_str = request.args.get('from_date')
            to_date_str = request.args.get('to_date')
            
            if from_date_str:
                from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
            if to_date_str:
                to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date()
        
        # Generate report data
        report = report_service.generate_report(
            user_id=current_user.id,
            period=period,
            from_date=from_date,
            to_date=to_date,
            transaction_type=transaction_type,
            category_id=category_id if category_id != 'all' else None
        )
        
        # Export based on format
        filename = export_service.get_filename(
            f"ledgermate_report_{period}", 
            format_type, 
            report
        )
        
        if format_type == 'csv':
            csv_data = export_service.export_to_csv(report)
            return send_file(
                io.BytesIO(csv_data.encode('utf-8')),
                mimetype='text/csv',
                as_attachment=True,
                download_name=filename
            )
            
        elif format_type == 'excel':
            excel_data = export_service.export_to_excel(report)
            return send_file(
                io.BytesIO(excel_data),
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=filename.replace('excel', 'xlsx')
            )
            
        elif format_type == 'pdf':
            pdf_data = export_service.export_to_pdf(
                report, 
                business_name=current_user.business_name
            )
            return send_file(
                io.BytesIO(pdf_data),
                mimetype='application/pdf',
                as_attachment=True,
                download_name=filename
            )
            
        elif format_type == 'print':
            # For print, return HTML that's optimized for printing
            return render_template(
                'reports/print_report.html',
                report=report,
                business_name=current_user.business_name,
                generated_at=datetime.now().strftime('%Y-%m-%d %H:%M')
            )
        
        else:
            return jsonify({
                'success': False,
                'error': f'Unsupported format: {format_type}'
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/monthly/<int:year>/<int:month>')
@login_required
def monthly_report(year, month):
    """Get monthly report for specific month"""
    try:
        report = report_service.get_monthly_summary(current_user.id, year, month)
        
        return jsonify({
            'success': True,
            'report': report
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/yearly/<int:year>')
@login_required
def yearly_report(year):
    """Get yearly report"""
    try:
        report = report_service.get_year_summary(current_user.id, year)
        
        return jsonify({
            'success': True,
            'report': report
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/compare')
@login_required
def compare_periods():
    """Compare two time periods"""
    try:
        period1_start = request.args.get('period1_start')
        period1_end = request.args.get('period1_end')
        period2_start = request.args.get('period2_start')
        period2_end = request.args.get('period2_end')
        
        if not all([period1_start, period1_end, period2_start, period2_end]):
            return jsonify({
                'success': False,
                'error': 'All period dates are required'
            }), 400
        
        # Parse dates
        p1_start = datetime.strptime(period1_start, '%Y-%m-%d').date()
        p1_end = datetime.strptime(period1_end, '%Y-%m-%d').date()
        p2_start = datetime.strptime(period2_start, '%Y-%m-%d').date()
        p2_end = datetime.strptime(period2_end, '%Y-%m-%d').date()
        
        # Compare periods
        comparison = report_service.compare_periods(
            current_user.id,
            p1_start, p1_end,
            p2_start, p2_end
        )
        
        return jsonify({
            'success': True,
            'comparison': comparison
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/api/insights')
@login_required
def get_insights():
    """Get financial insights and trends"""
    try:
        # Get last 3 months of data
        today = datetime.utcnow().date()
        three_months_ago = today - timedelta(days=90)
        
        report = report_service.generate_report(
            user_id=current_user.id,
            period='custom',
            from_date=three_months_ago,
            to_date=today
        )
        
        insights = {
            'highest_income_day': None,
            'highest_expense_day': None,
            'average_daily_income': 0,
            'average_daily_expense': 0,
            'most_used_category': None,
            'trend': 'stable'
        }
        
        # Calculate averages
        daily_data = report.get('daily_breakdown', [])
        if daily_data:
            total_income = sum(d['income'] for d in daily_data)
            total_expense = sum(d['expense'] for d in daily_data)
            days = len(daily_data)
            
            insights['average_daily_income'] = total_income / days if days > 0 else 0
            insights['average_daily_expense'] = total_expense / days if days > 0 else 0
            
            # Find highest days
            if daily_data:
                insights['highest_income_day'] = max(daily_data, key=lambda x: x['income'])
                insights['highest_expense_day'] = max(daily_data, key=lambda x: x['expense'])
        
        # Find most used category
        categories = report.get('category_breakdown', {})
        if categories:
            insights['most_used_category'] = max(
                categories.items(), 
                key=lambda x: x[1]['count']
            )[1]['name']
        
        # Determine trend
        if len(daily_data) >= 30:
            first_half = daily_data[:15]
            second_half = daily_data[-15:]
            
            first_avg_income = sum(d['income'] for d in first_half) / len(first_half)
            second_avg_income = sum(d['income'] for d in second_half) / len(second_half)
            
            if second_avg_income > first_avg_income * 1.1:
                insights['trend'] = 'increasing'
            elif second_avg_income < first_avg_income * 0.9:
                insights['trend'] = 'decreasing'
            else:
                insights['trend'] = 'stable'
        
        return jsonify({
            'success': True,
            'insights': insights
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500