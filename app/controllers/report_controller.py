from flask import Blueprint, render_template, request, jsonify, send_file, session
from flask_login import login_required, current_user
from app.services.report_service import report_service
from app.services.export_service import export_service
from app.services.forecast_service import forecast_service
from app.models import Liability
from app.extensions import db, csrf
from datetime import datetime, timedelta
import io
import uuid

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
        
        # Generate report from service
        report = report_service.generate_report(
            user_id=current_user.id,
            period=period,
            from_date=from_date,
            to_date=to_date,
            transaction_type=transaction_type,
            category_id=category_id if category_id != 'all' else None
        )
        
        # --- Format transactions to ensure category_name is passed to the frontend ---
        formatted_transactions = []
        for t in report.get('transactions', []):
            # Resolve Category Name
            cat_name = "General"
            if isinstance(t, dict):
                # Try common keys returned by services
                cat_name = t.get('category_name') or t.get('category') or "General"
            elif hasattr(t, 'category') and t.category:
                cat_name = t.category.name

            # Build standardized dictionary for the frontend AJAX call
            formatted_transactions.append({
                'date': t['date'] if isinstance(t, dict) else t.date.strftime('%Y-%m-%d'),
                'type': t['type'] if isinstance(t, dict) else t.type,
                'category_name': cat_name,
                'description': t.get('description', '-') if isinstance(t, dict) else (t.description or '-'),
                'payment_method': t.get('payment_method', 'Cash') if isinstance(t, dict) else (t.payment_method or 'Cash'),
                'amount': float(t['amount']) if isinstance(t, dict) else float(t.amount)
            })
        
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
            'transactions': formatted_transactions,
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
        
        p1_start = datetime.strptime(period1_start, '%Y-%m-%d').date()
        p1_end = datetime.strptime(period1_end, '%Y-%m-%d').date()
        p2_start = datetime.strptime(period2_start, '%Y-%m-%d').date()
        p2_end = datetime.strptime(period2_end, '%Y-%m-%d').date()
        
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

@bp.route('/api/profit-loss')
@login_required
def profit_loss():
    """Profit & Loss statement"""
    try:
        from_date_str = request.args.get('from_date')
        to_date_str = request.args.get('to_date')
        from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date() if from_date_str else None
        to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date() if to_date_str else None

        pl = report_service.generate_profit_loss(current_user.id, from_date=from_date, to_date=to_date)
        return jsonify({'success': True, 'profit_loss': pl})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/balance-sheet')
@login_required
def balance_sheet():
    """Balance sheet as of today (or a given date)"""
    try:
        as_of_str = request.args.get('as_of_date')
        as_of_date = datetime.strptime(as_of_str, '%Y-%m-%d').date() if as_of_str else None

        bs = report_service.generate_balance_sheet(current_user.id, as_of_date=as_of_date)
        return jsonify({'success': True, 'balance_sheet': bs})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/liabilities', methods=['GET', 'POST'])
@csrf.exempt
@login_required
def liabilities():
    """List or add loans/payables used by the balance sheet"""
    if request.method == 'POST':
        try:
            payload = request.get_json() or request.form
            liability = Liability(
                public_id=str(uuid.uuid4()),
                user_id=current_user.id,
                name=payload.get('name'),
                liability_type=payload.get('type', 'other'),
                amount=float(payload.get('amount') or 0)
            )
            db.session.add(liability)
            db.session.commit()
            return jsonify({'success': True, 'liability': liability.to_dict()})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 400

    items = Liability.query.filter_by(user_id=current_user.id, is_deleted=False).all()
    return jsonify({'success': True, 'liabilities': [l.to_dict() for l in items]})


@bp.route('/api/liabilities/<public_id>/delete', methods=['POST'])
@csrf.exempt
@login_required
def delete_liability(public_id):
    liability = Liability.query.filter_by(public_id=public_id, user_id=current_user.id).first()
    if liability:
        liability.is_deleted = True
        db.session.commit()
    return jsonify({'success': True})


@bp.route('/api/forecast')
@login_required
def forecast():
    """AI-driven income/expense forecast for upcoming months"""
    try:
        months_ahead = request.args.get('months', 3, type=int)
        data = forecast_service.generate_forecast(current_user.id, months_ahead=months_ahead)
        return jsonify({'success': True, 'forecast': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/insights')
@login_required
def get_insights():
    """Get financial insights and trends"""
    try:
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
        
        daily_data = report.get('daily_breakdown', [])
        if daily_data:
            total_income = sum(d['income'] for d in daily_data)
            total_expense = sum(d['expense'] for d in daily_data)
            days = len(daily_data)
            
            insights['average_daily_income'] = total_income / days if days > 0 else 0
            insights['average_daily_expense'] = total_expense / days if days > 0 else 0
            
            if daily_data:
                insights['highest_income_day'] = max(daily_data, key=lambda x: x['income'])
                insights['highest_expense_day'] = max(daily_data, key=lambda x: x['expense'])
        
        categories = report.get('category_breakdown', {})
        if categories:
            insights['most_used_category'] = max(
                categories.items(), 
                key=lambda x: x[1]['count']
            )[1]['name']
        
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