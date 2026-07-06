from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app.models import PaymentRequest, Transaction, Category
from app.extensions import db, csrf
from app.services.paystack_service import paystack_service
from datetime import datetime
import uuid

bp = Blueprint('payments', __name__, url_prefix='/payments')


@bp.route('/request', methods=['GET', 'POST'])
@login_required
def request_payment():
    """Business owner creates a payment link to send to a customer."""
    if request.method == 'POST':
        try:
            amount = float(request.form.get('amount'))
            description = request.form.get('description', '')
            category_id = request.form.get('category_id') or None
            customer_email = request.form.get('customer_email') or f"{current_user.phone_number}@ledgermate.local"
            customer_name = request.form.get('customer_name')

            pr = PaymentRequest(
                reference=f"lm-{uuid.uuid4().hex[:20]}",
                user_id=current_user.id,
                category_id=category_id,
                amount=amount,
                description=description,
                customer_email=customer_email,
                customer_name=customer_name,
                status='pending'
            )
            db.session.add(pr)
            db.session.commit()

            callback_url = url_for('payments.callback', reference=pr.reference, _external=True)

            checkout = paystack_service.initialize_transaction(
                email=customer_email,
                amount_kes=amount,
                reference=pr.reference,
                callback_url=callback_url,
                metadata={"user_id": current_user.id, "description": description}
            )

            return redirect(checkout['authorization_url'])

        except Exception as e:
            flash(f"Could not create payment link: {str(e)}", 'danger')
            return redirect(url_for('payments.request_payment'))

    categories = Category.query.filter_by(user_id=current_user.id, type='income').all()
    recent_requests = PaymentRequest.query.filter_by(user_id=current_user.id).order_by(
        PaymentRequest.created_at.desc()
    ).limit(10).all()
    return render_template('payments/request_payment.html', categories=categories, recent_requests=recent_requests)


@bp.route('/callback')
def callback():
    """
    Customer lands here after paying (or cancelling) on Paystack.
    We double check status directly with Paystack as a safety net, but the
    webhook below is the authoritative place transactions get created -
    this just gives the payer/owner a friendly confirmation screen.
    """
    reference = request.args.get('reference') or request.args.get('trxref')
    verified = False
    pr = PaymentRequest.query.filter_by(reference=reference).first() if reference else None

    if reference:
        try:
            data = paystack_service.verify_transaction(reference)
            verified = data.get('status') == 'success'
            if verified and pr:
                _record_successful_payment(pr, data)
        except Exception as e:
            current_app.logger.warning(f"Paystack verify failed for {reference}: {e}")

    return render_template('payments/callback.html', verified=verified, payment_request=pr)


@bp.route('/webhook', methods=['POST'])
@csrf.exempt
def webhook():
    """
    Paystack -> us. This is the real source of automatic transaction
    detection: no one types anything, Paystack tells us a payment cleared
    and we file it into the ledger ourselves.
    Configure this URL (https://yourdomain.com/payments/webhook) in the
    Paystack dashboard under Settings > API Keys & Webhooks.
    """
    signature = request.headers.get('x-paystack-signature')
    if not paystack_service.verify_webhook_signature(request.get_data(), signature):
        return jsonify({'error': 'invalid signature'}), 401

    event = request.get_json(silent=True) or {}

    if event.get('event') == 'charge.success':
        data = event.get('data', {})
        reference = data.get('reference')
        pr = PaymentRequest.query.filter_by(reference=reference).first()
        if pr:
            _record_successful_payment(pr, data)

    return jsonify({'status': 'ok'}), 200


def _record_successful_payment(payment_request, paystack_data):
    """Idempotently turn a confirmed Paystack payment into a ledger Transaction."""
    if payment_request.status == 'success' and payment_request.transaction_id:
        return  # already recorded, avoid duplicates if webhook fires twice

    category_id = payment_request.category_id
    if not category_id:
        default_cat = Category.query.filter_by(
            user_id=payment_request.user_id,
            type='income'
        ).first()
        category_id = default_cat.id if default_cat else None

    customer = paystack_data.get('customer', {}) or {}

    txn = Transaction(
        public_id=str(uuid.uuid4()),
        user_id=payment_request.user_id,
        category_id=category_id,
        type='income',
        amount=payment_request.amount,
        payment_method='paystack',
        description=payment_request.description or 'Paystack payment',
        paystack_reference=payment_request.reference,
        paystack_status='success',
        payer_email=customer.get('email') or payment_request.customer_email,
        payer_name=payment_request.customer_name,
        transaction_date=datetime.utcnow()
    )
    db.session.add(txn)
    db.session.flush()

    payment_request.status = 'success'
    payment_request.transaction_id = txn.id
    db.session.commit()
