from flask import Blueprint, request, jsonify, session
from flask_login import login_required, current_user
from app.services.chatbot_service import chatbot_service
from app.models import ChatHistory, Transaction
from app.extensions import db
from datetime import datetime, timedelta
from sqlalchemy import func
import uuid

bp = Blueprint('chatbot', __name__, url_prefix='/chatbot')

@bp.route('/message', methods=['POST'])
def send_message():
    """Process chatbot messages"""
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        session_id = data.get('session_id', str(uuid.uuid4()))
        language = session.get('language', 'en')
        
        if not message:
            return jsonify({
                'success': False,
                'response': 'Please type a message.' if language == 'en' else 'Tafadhali andika ujumbe.'
            }), 400
        
        # Get conversation history
        history = ChatHistory.query.filter_by(
            session_id=session_id
        ).order_by(ChatHistory.created_at.desc()).limit(5).all()
        
        conversation_history = []
        for h in reversed(history):
            conversation_history.append({
                'message': h.message,
                'response': h.response,
                'intent': h.intent
            })
        
        # Check for follow-up
        follow_up_response = chatbot_service.handle_follow_up(
            message, conversation_history, language
        )
        
        if follow_up_response:
            response = follow_up_response
            intent = 'follow_up'
        else:
            # Get regular response
            response = chatbot_service.get_response(message, language)
            
            # Detect intent for tracking
            intent = 'general'
            for possible_intent, keywords in chatbot_service.intents.items():
                if any(keyword in message.lower() for keyword in keywords):
                    intent = possible_intent
                    break
        
        # Get contextual help if on specific page
        page = data.get('page', '')
        if page and 'help' in message.lower():
            contextual = chatbot_service.get_contextual_help(page, language)
            if contextual:
                response += "\n\n" + contextual
        
        # Get financial advice if requested
        if any(word in message.lower() for word in ['advice', 'insight', 'suggest', 'ushauri', 'shauri']):
            if current_user.is_authenticated:
                # Get user's recent financial data
                thirty_days_ago = datetime.utcnow() - timedelta(days=30)
                
                income_total = db.session.query(func.sum(Transaction.amount)).filter(
                    Transaction.user_id == current_user.id,
                    Transaction.type == 'income',
                    Transaction.transaction_date >= thirty_days_ago,
                    Transaction.is_deleted == False
                ).scalar() or 0
                
                expense_total = db.session.query(func.sum(Transaction.amount)).filter(
                    Transaction.user_id == current_user.id,
                    Transaction.type == 'expense',
                    Transaction.transaction_date >= thirty_days_ago,
                    Transaction.is_deleted == False
                ).scalar() or 0
                
                transactions_data = {
                    'total_income': float(income_total),
                    'total_expense': float(expense_total)
                }
                
                advice = chatbot_service.get_financial_advice(transactions_data, language)
                response += "\n\n" + advice
        
        # Save to history
        chat_history = ChatHistory(
            user_id=current_user.id if current_user.is_authenticated else None,
            session_id=session_id,
            message=message,
            response=response,
            intent=intent
        )
        db.session.add(chat_history)
        db.session.commit()
        
        # Get quick replies for next message
        quick_replies = chatbot_service.get_quick_replies(language)
        
        return jsonify({
            'success': True,
            'response': response,
            'session_id': session_id,
            'quick_replies': quick_replies,
            'intent': intent
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'response': 'Sorry, an error occurred. Please try again.' if language == 'en' else 'Samahani, hitilafu imetokea. Tafadhali jaribu tena.'
        }), 500

@bp.route('/history', methods=['GET'])
@login_required
def get_history():
    """Get user's chat history"""
    try:
        session_id = request.args.get('session_id')
        language = session.get('language', 'en')
        
        query = ChatHistory.query.filter_by(user_id=current_user.id)
        
        if session_id:
            query = query.filter_by(session_id=session_id)
        
        history = query.order_by(ChatHistory.created_at.desc()).limit(50).all()
        
        history_data = []
        for h in history:
            history_data.append({
                'id': h.id,
                'message': h.message,
                'response': h.response,
                'intent': h.intent,
                'time': h.created_at.strftime('%Y-%m-%d %H:%M')
            })
        
        return jsonify({
            'success': True,
            'history': history_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/clear', methods=['POST'])
@login_required
def clear_history():
    """Clear chat history"""
    try:
        session_id = request.json.get('session_id')
        language = session.get('language', 'en')
        
        query = ChatHistory.query.filter_by(user_id=current_user.id)
        
        if session_id:
            query = query.filter_by(session_id=session_id)
        
        query.delete()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'History cleared' if language == 'en' else 'Historia imefutwa'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/feedback', methods=['POST'])
@login_required
def submit_feedback():
    """Submit feedback on chatbot response"""
    try:
        data = request.json
        chat_id = data.get('chat_id')
        helpful = data.get('helpful')
        feedback = data.get('feedback', '')
        
        chat = ChatHistory.query.filter_by(
            id=chat_id,
            user_id=current_user.id
        ).first()
        
        if chat:
            # Store feedback (you might want to add a feedback field to model)
            # For now, just log it
            app.logger.info(f"Chatbot feedback - Chat {chat_id}: Helpful={helpful}, Feedback={feedback}")
            
            return jsonify({
                'success': True,
                'message': 'Thank you for your feedback!'
            })
        
        return jsonify({
            'success': False,
            'message': 'Chat not found'
        }), 404
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/suggestions', methods=['GET'])
def get_suggestions():
    """Get quick reply suggestions"""
    try:
        language = session.get('language', 'en')
        page = request.args.get('page', '')
        
        suggestions = chatbot_service.get_quick_replies(language)
        
        # Add page-specific suggestions
        if page == 'dashboard':
            page_suggestions = [
                'Show me today\'s summary',
                'Explain the chart',
                'Recent transactions'
            ] if language == 'en' else [
                'Nionyeshe muhtasari wa leo',
                'Eleza chati',
                'Miamala ya karibuni'
            ]
            suggestions = page_suggestions + suggestions[:3]
        
        elif page == 'transactions':
            page_suggestions = [
                'How to add transaction?',
                'Search for M-Pesa transaction',
                'Filter by category'
            ] if language == 'en' else [
                'Jinsi ya kuongeza muamala?',
                'Tafuta muamala wa M-Pesa',
                'Chuja kwa aina'
            ]
            suggestions = page_suggestions + suggestions[:3]
        
        elif page == 'reports':
            page_suggestions = [
                'Generate monthly report',
                'Export as PDF',
                'Compare income and expense'
            ] if language == 'en' else [
                'Tengeneza ripoti ya mwezi',
                'Hamisha kama PDF',
                'Linganisha mapato na matumizi'
            ]
            suggestions = page_suggestions + suggestions[:3]
        
        return jsonify({
            'success': True,
            'suggestions': suggestions
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500