import logging
import json
import hashlib
import hmac
from flask import current_app, url_for
from paystackapi.paystack import Paystack
from app.models import Transaction, User, db
from decimal import Decimal
from datetime import datetime

logger = logging.getLogger(__name__)


class PayStackError(Exception):
    """Custom exception for PayStack errors."""
    pass


class PayStackService:
    def __init__(self):
        self.secret_key = None
        self.public_key = None
        self.environment = None
        self.paystack = None
        self._initialize()

    def _initialize(self):
        """Initialize PayStack with configuration."""
        try:
            self.secret_key = current_app.config.get('PAYSTACK_SECRET_KEY')
            self.public_key = current_app.config.get('PAYSTACK_PUBLIC_KEY')
            self.environment = current_app.config.get('PAYSTACK_ENV', 'sandbox')
            
            if not self.secret_key:
                raise PayStackError("PAYSTACK_SECRET_KEY not configured")
            
            # Initialize PayStack client
            self.paystack = Paystack(secret_key=self.secret_key)
            logger.info(f"PayStack initialized in {self.environment} mode")
        except Exception as e:
            logger.error(f"Failed to initialize PayStack: {e}")
            raise PayStackError(f"PayStack initialization failed: {e}")

    def initialize_transaction(self, user_id, email, amount, reference=None, 
                               callback_url=None, metadata=None):
        """
        Initialize a PayStack transaction.
        
        Args:
            user_id: User ID
            email: Customer email
            amount: Amount in kobo (lowest currency unit)
            reference: Optional unique reference
            callback_url: Optional callback URL
            metadata: Optional additional data
        
        Returns:
            dict: Transaction initialization response
        """
        try:
            user = User.query.get(user_id)
            if not user:
                raise PayStackError("User not found")

            # Amount should be in kobo (for NGN) or smallest currency unit
            # PayStack expects amount in kobo (multiply by 100 for Naira)
            amount_in_kobo = int(amount * 100)
            
            # Generate reference if not provided
            if not reference:
                reference = f"PAY-{user.public_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            
            # Prepare transaction data
            transaction_data = {
                'amount': amount_in_kobo,
                'email': email,
                'reference': reference,
                'callback_url': callback_url or url_for('paystack.paystack_callback', _external=True),
                'metadata': metadata or {
                    'user_id': user_id,
                    'user_public_id': user.public_id
                }
            }
            
            # Initialize transaction with PayStack
            response = self.paystack.transaction.initialize(**transaction_data)
            
            if response.get('status'):
                data = response.get('data', {})
                
                # Create transaction record in database
                transaction = Transaction(
                    user_id=user_id,
                    reference=reference,
                    amount=amount,
                    status='pending',
                    payment_method='paystack',
                    transaction_type='deposit',
                    paystack_access_code=data.get('access_code'),
                    paystack_reference=reference,
                    metadata=json.dumps(metadata) if metadata else None
                )
                db.session.add(transaction)
                db.session.commit()
                
                return {
                    'success': True,
                    'authorization_url': data.get('authorization_url'),
                    'access_code': data.get('access_code'),
                    'reference': reference,
                    'transaction_id': transaction.id
                }
            else:
                error_message = response.get('message', 'Transaction initialization failed')
                logger.error(f"PayStack initialization failed: {error_message}")
                raise PayStackError(error_message)
                
        except Exception as e:
            logger.error(f"PayStack transaction initialization error: {e}")
            raise PayStackError(f"Failed to initialize transaction: {str(e)}")

    def verify_transaction(self, reference):
        """
        Verify a PayStack transaction.
        
        Args:
            reference: Transaction reference
        
        Returns:
            dict: Verification result
        """
        try:
            response = self.paystack.transaction.verify(reference)
            
            if response.get('status'):
                data = response.get('data', {})
                
                # Update transaction status
                transaction = Transaction.query.filter_by(reference=reference).first()
                if transaction:
                    transaction.status = data.get('status')
                    transaction.gateway_response = json.dumps(data)
                    transaction.paid_at = datetime.fromisoformat(
                        data.get('paid_at').replace('Z', '+00:00')
                    ) if data.get('paid_at') else None
                    
                    if data.get('status') == 'success':
                        # Process successful payment
                        transaction.is_paid = True
                        # Update user balance if applicable
                        user = User.query.get(transaction.user_id)
                        if user:
                            user.balance = (user.balance or 0) + transaction.amount
                        logger.info(f"Transaction {reference} verified successfully")
                    else:
                        logger.warning(f"Transaction {reference} verification failed with status: {data.get('status')}")
                    
                    db.session.commit()
                
                return {
                    'success': True,
                    'status': data.get('status'),
                    'amount': data.get('amount'),
                    'reference': reference
                }
            else:
                error_message = response.get('message', 'Transaction verification failed')
                logger.error(f"Transaction verification failed: {error_message}")
                raise PayStackError(error_message)
                
        except Exception as e:
            logger.error(f"Transaction verification error: {e}")
            raise PayStackError(f"Failed to verify transaction: {str(e)}")

    def handle_webhook(self, payload, signature_header):
        """
        Handle PayStack webhook events.
        
        Args:
            payload: Webhook payload
            signature_header: Signature header from PayStack
        
        Returns:
            dict: Webhook processing result
        """
        try:
            # Verify webhook signature
            if not self.verify_webhook_signature(payload, signature_header):
                logger.warning("Invalid webhook signature")
                return {'success': False, 'error': 'Invalid signature'}
            
            # Parse payload
            event_data = json.loads(payload)
            event_type = event_data.get('event')
            
            if event_type == 'charge.success':
                return self.handle_charge_success(event_data)
            elif event_type == 'transfer.success':
                return self.handle_transfer_success(event_data)
            elif event_type == 'transfer.failed':
                return self.handle_transfer_failed(event_data)
            else:
                logger.info(f"Unhandled webhook event: {event_type}")
                return {'success': True, 'message': 'Event received but not processed'}
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON payload: {e}")
            raise PayStackError("Invalid JSON payload")
        except Exception as e:
            logger.error(f"Webhook processing error: {e}")
            raise PayStackError(f"Webhook processing failed: {str(e)}")

    def verify_webhook_signature(self, payload, signature_header):
        """
        Verify PayStack webhook signature.
        
        Args:
            payload: Raw webhook payload
            signature_header: Signature header value
        
        Returns:
            bool: True if signature is valid
        """
        try:
            if not signature_header:
                return False
            
            # Compute expected signature
            expected_signature = hmac.new(
                self.secret_key.encode('utf-8'),
                payload.encode('utf-8'),
                hashlib.sha512
            ).hexdigest()
            
            return hmac.compare_digest(expected_signature, signature_header)
            
        except Exception as e:
            logger.error(f"Signature verification error: {e}")
            return False

    def handle_charge_success(self, event_data):
        """
        Handle successful charge webhook.
        
        Args:
            event_data: Webhook data for charge.success event
        
        Returns:
            dict: Processing result
        """
        try:
            data = event_data.get('data', {})
            reference = data.get('reference')
            
            if not reference:
                logger.warning("No reference in charge.success webhook")
                return {'success': True, 'message': 'No reference found'}
            
            # Find and update transaction
            transaction = Transaction.query.filter_by(reference=reference).first()
            if transaction:
                transaction.status = 'success'
                transaction.is_paid = True
                transaction.gateway_response = json.dumps(data)
                transaction.paid_at = datetime.now()
                
                # Update user balance
                user = User.query.get(transaction.user_id)
                if user:
                    user.balance = (user.balance or 0) + transaction.amount
                
                db.session.commit()
                logger.info(f"Webhook processed successfully for transaction {reference}")
                return {'success': True, 'message': f'Transaction {reference} updated'}
            else:
                logger.warning(f"Transaction {reference} not found in database")
                return {'success': True, 'message': f'Transaction {reference} not found'}
                
        except Exception as e:
            logger.error(f"Charge success processing error: {e}")
            raise PayStackError(f"Failed to process charge success: {str(e)}")

    def handle_transfer_success(self, event_data):
        """Handle successful transfer webhook."""
        logger.info(f"Transfer success webhook received")
        # Implement transfer handling logic here
        return {'success': True}

    def handle_transfer_failed(self, event_data):
        """Handle failed transfer webhook."""
        logger.warning(f"Transfer failed webhook received")
        # Implement failed transfer handling logic here
        return {'success': True}

    def create_paystack_payment(self, user_id, amount, email, description=None):
        """
        Create a payment intent with PayStack (simplified version).
        
        Args:
            user_id: User ID
            amount: Amount to charge
            email: User email
            description: Optional description
        
        Returns:
            dict: Payment initialization result
        """
        try:
            metadata = {
                'description': description or 'Payment to LedgerMate',
                'user_id': user_id
            }
            
            result = self.initialize_transaction(
                user_id=user_id,
                email=email,
                amount=amount,
                metadata=metadata
            )
            
            return {
                'success': True,
                'authorization_url': result['authorization_url'],
                'reference': result['reference'],
                'access_code': result['access_code']
            }
            
        except Exception as e:
            logger.error(f"Payment creation error: {e}")
            raise PayStackError(f"Failed to create payment: {str(e)}")


# Singleton instance
paystack_service = PayStackService()