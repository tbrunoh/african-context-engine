from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class PaymentRequest:
    msisdn: str          # E.164
    amount: int          # whole units of local currency
    reference: str       # order or account reference shown to the payer
    description: str


class PaymentProvider(Protocol):
    name: str

    def build_request(self, req: PaymentRequest) -> dict[str, Any]:
        """Return the provider specific request body, without sending it."""

    def send(self, req: PaymentRequest) -> dict[str, Any]:
        """Send the request through an injected HTTP client and return the response."""
