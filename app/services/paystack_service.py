"""
Paystack payment gateway integration.

Replaces the old manual "type in your M-Pesa code" flow: a payment request
is created, the customer pays via Paystack's checkout (card, or M-Pesa /
mobile money where supported), and Paystack notifies us via webhook. The
webhook handler is what actually creates the ledger Transaction - nobody
has to type anything in.

Docs: https://paystack.com/docs/payments/accept-payments/
"""
import hashlib
import hmac
import requests
from flask import current_app

PAYSTACK_BASE_URL = "https://api.paystack.co"


class PaystackService:

    def _headers(self):
        secret_key = current_app.config.get('PAYSTACK_SECRET_KEY')
        if not secret_key:
            raise RuntimeError(
                "PAYSTACK_SECRET_KEY is not configured. Set it as an environment "
                "variable (see SETUP_PAYSTACK.md)."
            )
        return {
            "Authorization": f"Bearer {secret_key}",
            "Content-Type": "application/json",
        }

    def initialize_transaction(self, email, amount_kes, reference, callback_url, metadata=None):
        """
        Create a Paystack checkout session for a given amount.
        amount_kes is in whole currency units (e.g. 500.00 KES); Paystack
        expects the minor unit (cents), so we multiply by 100.
        Returns dict with 'authorization_url', 'access_code', 'reference'.
        """
        payload = {
            "email": email,
            "amount": int(round(float(amount_kes) * 100)),
            "reference": reference,
            "callback_url": callback_url,
            "currency": "KES",
        }
        if metadata:
            payload["metadata"] = metadata

        resp = requests.post(
            f"{PAYSTACK_BASE_URL}/transaction/initialize",
            json=payload,
            headers=self._headers(),
            timeout=15,
        )
        data = resp.json()
        if not resp.ok or not data.get("status"):
            raise RuntimeError(data.get("message", "Failed to initialize Paystack transaction"))
        return data["data"]

    def verify_transaction(self, reference):
        """Confirm a transaction's real status directly with Paystack (source of truth)."""
        resp = requests.get(
            f"{PAYSTACK_BASE_URL}/transaction/verify/{reference}",
            headers=self._headers(),
            timeout=15,
        )
        data = resp.json()
        if not resp.ok or not data.get("status"):
            raise RuntimeError(data.get("message", "Failed to verify Paystack transaction"))
        return data["data"]

    def verify_webhook_signature(self, request_body_bytes, signature_header):
        """
        Paystack signs webhook payloads with HMAC SHA512 of the raw body,
        using your secret key. This MUST pass before we trust a webhook,
        otherwise anyone could POST fake "payment successful" events.
        """
        secret_key = current_app.config.get('PAYSTACK_SECRET_KEY')
        if not secret_key or not signature_header:
            return False
        computed = hmac.new(
            secret_key.encode('utf-8'),
            request_body_bytes,
            hashlib.sha512
        ).hexdigest()
        return hmac.compare_digest(computed, signature_header)


paystack_service = PaystackService()
