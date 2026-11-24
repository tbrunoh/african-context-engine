"""M-Pesa STK Push (Lipa na M-Pesa Online) through Safaricom's Daraja API.

Builds the documented request body. Sending needs credentials from a Daraja
app and an HTTP client injected by the deployment; this module never stores
secrets and never sends anything on import.
"""
from __future__ import annotations

import base64
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any

from .base import PaymentRequest

SANDBOX_URL = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
EAT = timezone(timedelta(hours=3))  # Daraja timestamps use East Africa Time


class MpesaStkPush:
    name = "mpesa"

    def __init__(self, shortcode: str, passkey: str, callback_url: str,
                 http_post: Callable[[str, dict[str, Any], dict[str, str]], dict[str, Any]] | None = None,
                 token_provider: Callable[[], str] | None = None,
                 endpoint: str = SANDBOX_URL,
                 clock: Callable[[], datetime] | None = None) -> None:
        self.shortcode = shortcode
        self.passkey = passkey
        self.callback_url = callback_url
        self.http_post = http_post
        self.token_provider = token_provider
        self.endpoint = endpoint
        self.clock = clock or (lambda: datetime.now(EAT))

    def _password(self, timestamp: str) -> str:
        return base64.b64encode(f"{self.shortcode}{self.passkey}{timestamp}".encode()).decode()

    def build_request(self, req: PaymentRequest) -> dict[str, Any]:
        if req.amount <= 0:
            raise ValueError("Amount must be positive")
        phone = req.msisdn.lstrip("+")
        timestamp = self.clock().strftime("%Y%m%d%H%M%S")
        return {
            "BusinessShortCode": self.shortcode,
            "Password": self._password(timestamp),
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(req.amount),
            "PartyA": phone,
            "PartyB": self.shortcode,
            "PhoneNumber": phone,
            "CallBackURL": self.callback_url,
            "AccountReference": req.reference[:12],
            "TransactionDesc": req.description[:13],
        }

    def send(self, req: PaymentRequest) -> dict[str, Any]:
        if self.http_post is None or self.token_provider is None:
            raise RuntimeError("Configure http_post and token_provider to send payments")
        headers = {"Authorization": f"Bearer {self.token_provider()}", "Content-Type": "application/json"}
        return self.http_post(self.endpoint, self.build_request(req), headers)
