from flask import Blueprint, request, jsonify, redirect, url_for, current_app
from flask_login import login_required, current_user
from app.extensions import csrf
from app.services.paystack_service import paystack_service, PayStackError

bp = Blueprint('paystack', __name__, url_prefix='/paystack')


@bp.route('/initialize', methods=['POST'])
@login_required
def initialize_payment():
    """Initialize a PayStack payment.
    
    Body JSON: {
        "email": "user@example.com",
        "amount": 50000,
        "description": "Payment for invoice #123"
    }
    """
    try:
        data = request.get_json() or {}
        email = data.get('email')
        amount = data.get('amount')
        description = data.get('description', 'Payment')
        
        if not email or not amount:
            return jsonify({
                'success': False,
                'error': 'email and amount are required'
            }), 400
        
        # Validate amount
        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError("Amount must be positive")
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Invalid amount'
            }), 400
        
        # Initialize payment
        result = paystack_service.create_paystack_payment(
            user_id=current_user.id,
            email=email,
            amount=amount,
            description=description
        )
        
        return jsonify({
            'success': True,
            'data': {
                'authorization_url': result['authorization_url'],
                'reference': result['reference'],
                'access_code': result['access_code']
            }
        })
        
    except PayStackError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        current_app.logger.error(f"Payment initialization error: {e}")
        return jsonify({
            'success': False,
            'error': f'Unexpected error: {str(e)}'
        }), 500


@bp.route('/verify/<reference>', methods=['GET'])
@login_required
def verify_transaction(reference):
    """Verify a PayStack transaction.
    
    Args:
        reference: Transaction reference
    """
    try:
        result = paystack_service.verify_transaction(reference)
        return jsonify({
            'success': True,
            'data': result
        })
    except PayStackError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        current_app.logger.error(f"Transaction verification error: {e}")
        return jsonify({
            'success': False,
            'error': f'Unexpected error: {str(e)}'
        }), 500


@bp.route('/callback', methods=['GET', 'POST'])
def paystack_callback():
    """Handle PayStack redirect callback after payment."""
    try:
        # Get reference from query parameters (GET) or body (POST)
        if request.method == 'GET':
            reference = request.args.get('reference')
        else:
            data = request.get_json() or {}
            reference = data.get('reference')
        
        if not reference:
            return jsonify({
                'success': False,
                'error': 'No reference provided'
            }), 400
        
        # Verify the transaction
        result = paystack_service.verify_transaction(reference)
        
        if result['success'] and result.get('status') == 'success':
            # Redirect to success page or return success response
            return jsonify({
                'success': True,
                'message': 'Payment verified successfully',
                'data': result
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Payment verification failed',
                'data': result
            }), 400
            
    except PayStackError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        current_app.logger.error(f"Callback error: {e}")
        return jsonify({
            'success': False,
            'error': f'Unexpected error: {str(e)}'
        }), 500


@bp.route('/webhook', methods=['POST'])
@csrf.exempt
def webhook():
    """Handle PayStack webhook events.
    
    PayStack sends POST requests with signature header for verification.
    This endpoint must be publicly accessible.
    """
    try:
        payload = request.get_data(as_text=True)
        signature = request.headers.get('x-paystack-signature')
        
        if not signature:
            current_app.logger.warning("No signature header in webhook request")
            return jsonify({
                'status': 'error',
                'message': 'Missing signature'
            }), 400
        
        # Process webhook
        result = paystack_service.handle_webhook(payload, signature)
        
        if result.get('success'):
            return jsonify({
                'status': 'success',
                'message': result.get('message', 'Webhook processed successfully')
            })
        else:
            return jsonify({
                'status': 'error',
                'message': result.get('error', 'Webhook processing failed')
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"Webhook error: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Webhook processing error'
        }), 500


@bp.route('/payment-status/<reference>', methods=['GET'])
@login_required
def get_payment_status(reference):
    """Get payment status for a transaction."""
    try:
        transaction = Transaction.query.filter_by(
            reference=reference,
            user_id=current_user.id
        ).first()
        
        if not transaction:
            return jsonify({
                'success': False,
                'error': 'Transaction not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': {
                'reference': transaction.reference,
                'status': transaction.status,
                'amount': transaction.amount,
                'paid_at': transaction.paid_at.isoformat() if transaction.paid_at else None,
                'is_paid': transaction.is_paid
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Payment status error: {e}")
        return jsonify({
            'success': False,
            'error': f'Unexpected error: {str(e)}'
        }), 500