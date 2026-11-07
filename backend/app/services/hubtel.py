from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

import httpx

from app.core.config import settings


class HubtelError(RuntimeError):
    pass


def normalize_ghana_phone(value: str) -> str:
    phone = (
        value.strip()
        .replace(" ", "")
        .replace("-", "")
        .replace("(", "")
        .replace(")", "")
    )

    if phone.startswith("+"):
        phone = phone[1:]

    if phone.startswith("0") and len(phone) == 10:
        phone = "233" + phone[1:]

    if not phone.startswith("233") or len(phone) != 12:
        raise ValueError(
            "Ghana phone number must look like "
            "0241234567 or 233241234567."
        )

    if not phone.isdigit():
        raise ValueError("Phone number must contain only digits.")

    return phone


def normalize_momo_channel(value: str) -> str:
    channel = value.strip().lower()

    aliases = {
        "mtn": "mtn-gh",
        "mtn-gh": "mtn-gh",
        "telecel": "vodafone-gh",
        "vodafone": "vodafone-gh",
        "vodafone-gh": "vodafone-gh",
        "airteltigo": "tigo-gh",
        "airtel-tigo": "tigo-gh",
        "tigo": "tigo-gh",
        "tigo-gh": "tigo-gh",
    }

    try:
        return aliases[channel]
    except KeyError as exc:
        raise ValueError(
            "Unsupported MoMo network. "
            "Use MTN, Telecel, or AirtelTigo."
        ) from exc


def money(value: Decimal | float | str) -> Decimal:
    amount = Decimal(str(value)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )

    if amount <= 0:
        raise ValueError("Amount must be greater than zero.")

    return amount


class HubtelClient:
    def __init__(self) -> None:
        self.auth = httpx.BasicAuth(
            settings.hubtel_api_id,
            settings.hubtel_api_key,
        )

    def _require_enabled(self) -> None:
        if not settings.hubtel_enabled:
            raise HubtelError(
                "Hubtel is disabled. "
                "Set HUBTEL_ENABLED=true only when credentials are ready."
            )

        missing = []

        for name, value in {
            "HUBTEL_API_ID": settings.hubtel_api_id,
            "HUBTEL_API_KEY": settings.hubtel_api_key,
            "HUBTEL_COLLECTION_ACCOUNT":
                settings.hubtel_collection_account,
            "HUBTEL_DISBURSEMENT_ACCOUNT":
                settings.hubtel_disbursement_account,
        }.items():
            if not value:
                missing.append(name)

        if missing:
            raise HubtelError(
                "Missing Hubtel configuration: "
                + ", ".join(missing)
            )

    def _request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        self._require_enabled()

        try:
            with httpx.Client(
                auth=self.auth,
                timeout=settings.hubtel_timeout_seconds,
            ) as client:
                response = client.request(
                    method,
                    url,
                    **kwargs,
                )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise HubtelError(
                "Hubtel request timed out. "
                "Do not blindly retry; reconcile by reference."
            ) from exc
        except httpx.HTTPError as exc:
            raise HubtelError(
                f"Hubtel HTTP request failed: {exc}"
            ) from exc

        try:
            body = response.json()
        except ValueError as exc:
            raise HubtelError(
                "Hubtel returned a non-JSON response."
            ) from exc

        if not isinstance(body, dict):
            raise HubtelError(
                "Hubtel returned an unexpected response body."
            )

        return body

    def receive_money(
        self,
        *,
        customer_phone: str,
        channel: str,
        amount: Decimal | float | str,
        description: str,
        client_reference: str,
        callback_url: str,
    ) -> dict[str, Any]:
        if not client_reference or len(client_reference) > 36:
            raise ValueError(
                "Hubtel collection ClientReference "
                "must be 1-36 characters."
            )

        phone = normalize_ghana_phone(customer_phone)
        momo_channel = normalize_momo_channel(channel)
        total = money(amount)

        url = (
            settings.hubtel_receive_base_url.rstrip("/")
            + "/merchantaccount/merchants/"
            + settings.hubtel_collection_account
            + "/receive/mobilemoney"
        )

        payload = {
            "CustomerMsisdn": phone,
            "Channel": momo_channel,
            "Amount": float(total),
            "Description": description[:255],
            "ClientReference": client_reference,
            "PrimaryCallbackUrl": callback_url,
        }

        return self._request(
            "POST",
            url,
            json=payload,
        )

    def check_collection_status(
        self,
        *,
        client_reference: str,
    ) -> dict[str, Any]:
        if not client_reference:
            raise ValueError("Client reference is required.")

        url = (
            settings.hubtel_status_base_url.rstrip("/")
            + "/transactions/"
            + settings.hubtel_collection_account
            + "/status"
        )

        return self._request(
            "GET",
            url,
            params={
                "clientReference": client_reference,
            },
        )


    def verify_mobile_wallet(
        self,
        *,
        phone: str,
        channel: str,
    ) -> dict[str, Any]:
        msisdn = normalize_ghana_phone(phone)
        momo_channel = normalize_momo_channel(channel)

        url = (
            settings.hubtel_verification_base_url.rstrip("/")
            + "/v2/merchantaccount/merchants/"
            + settings.hubtel_collection_account
            + "/mobilemoney/verify"
        )

        return self._request(
            "GET",
            url,
            params={
                "channel": momo_channel,
                "customerMsisdn": msisdn,
            },
        )

    def send_money(
        self,
        *,
        recipient_name: str,
        recipient_phone: str,
        channel: str,
        amount: Decimal | float | str,
        description: str,
        client_reference: str,
        callback_url: str,
    ) -> dict[str, Any]:
        if not client_reference:
            raise ValueError("Client reference is required.")

        phone = normalize_ghana_phone(recipient_phone)
        momo_channel = normalize_momo_channel(channel)
        total = money(amount)

        url = (
            settings.hubtel_send_base_url.rstrip("/")
            + "/api/merchants/"
            + settings.hubtel_disbursement_account
            + "/send/mobilemoney"
        )

        payload = {
            "RecipientName": recipient_name.strip(),
            "RecipientMsisdn": phone,
            "Channel": momo_channel,
            "Amount": float(total),
            "Description": description[:255],
            "ClientReference": client_reference,
            "PrimaryCallbackURL": callback_url,
        }

        return self._request(
            "POST",
            url,
            json=payload,
        )


hubtel = HubtelClient()
