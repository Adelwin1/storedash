from __future__ import annotations

import hashlib
import re
from difflib import SequenceMatcher
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


@dataclass
class ParsedMoneyMessage:
    direction: str
    amount: Decimal
    phone: str | None
    payer_name: str | None
    transaction_reference: str | None
    raw_text: str


def normalize_phone_from_text(
    value: str | None,
) -> str | None:
    if not value:
        return None

    digits = re.sub(
        r"\D",
        "",
        value,
    )

    if digits.startswith("0") and len(digits) == 10:
        return "233" + digits[1:]

    if digits.startswith("233") and len(digits) == 12:
        return digits

    return None


def normalize_payer_name(value: str | None) -> str:
    if not value:
        return ""

    cleaned = re.sub(
        r"[^a-z0-9\s]",
        " ",
        value.lower(),
    )

    return " ".join(
        cleaned.split()
    )


def payer_name_similarity(
    expected: str | None,
    received: str | None,
) -> float:
    left = normalize_payer_name(expected)
    right = normalize_payer_name(received)

    if not left or not right:
        return 0.0

    direct = SequenceMatcher(
        None,
        left,
        right,
    ).ratio()

    sorted_left = " ".join(
        sorted(left.split())
    )
    sorted_right = " ".join(
        sorted(right.split())
    )

    reordered = SequenceMatcher(
        None,
        sorted_left,
        sorted_right,
    ).ratio()

    return max(
        direct,
        reordered,
    )


def parse_money_sms(
    text: str,
) -> ParsedMoneyMessage | None:
    clean = " ".join(
        text.split()
    )

    lower = clean.lower()

    incoming_words = (
        "received",
        "credited",
        "money received",
        "payment received",
        "cash in",
        "paid in",
        "payment from",
        "ghipss payment from",
        "organisation payment from",
    )

    outgoing_words = (
        "sent",
        "paid",
        "debited",
        "transferred",
        "cash out",
        "payment of",
        "payment to",
        "transfer to",
    )

    direction = None

    if any(
        word in lower
        for word in incoming_words
    ):
        direction = "incoming"

    elif any(
        word in lower
        for word in outgoing_words
    ):
        direction = "outgoing"

    if direction is None:
        return None

    amount_match = re.search(
        r"(?:gh₵|ghc|ghs)\s*"
        r"([0-9][0-9,]*(?:\.[0-9]{1,2})?)",
        clean,
        re.IGNORECASE,
    )

    if amount_match is None:
        return None

    try:
        amount = Decimal(
            amount_match.group(1)
            .replace(",", "")
        ).quantize(
            Decimal("0.01")
        )

    except InvalidOperation:
        return None

    if amount <= 0:
        return None

    phone_match = re.search(
        r"(?<!\d)"
        r"(?:\+?233|0)"
        r"\s*\d{2}"
        r"(?:[\s-]*\d){7}"
        r"(?!\d)",
        clean,
    )

    phone = (
        normalize_phone_from_text(
            phone_match.group(0)
        )
        if phone_match
        else None
    )

    payer_name = None

    if direction == "incoming":
        name_match = re.search(
            r"\bfrom\s+(.+?)"
            r"(?=\s+(?:transaction|txn|reference|ref|receipt|financial)\b|$)",
            clean,
            re.IGNORECASE,
        )

        if name_match:
            candidate_name = (
                name_match.group(1)
                .strip()
                .strip(" .,-")
            )

            if (
                candidate_name
                and normalize_phone_from_text(
                    candidate_name
                ) is None
                and len(
                    re.sub(
                        r"[^A-Za-z]",
                        "",
                        candidate_name,
                    )
                ) >= 2
            ):
                payer_name = candidate_name

    reference_patterns = (
        r"(?:transaction|txn|reference|ref|receipt)"
        r"\s*(?:id|number|no\.?)?"
        r"\s*[:#-]?\s*"
        r"([A-Za-z0-9-]{5,80})",

        r"\bID\s*[:#-]?\s*"
        r"([A-Za-z0-9-]{5,80})",
    )

    reference = None

    for pattern in reference_patterns:
        match = re.search(
            pattern,
            clean,
            re.IGNORECASE,
        )

        if match:
            reference = (
                match.group(1)
                .strip()
            )
            break

    return ParsedMoneyMessage(
        direction=direction,
        amount=amount,
        phone=phone,
        payer_name=payer_name,
        transaction_reference=reference,
        raw_text=clean,
    )


def message_fingerprint(
    *,
    sender: str,
    body: str,
    received_at: str,
) -> str:
    raw = (
        sender.strip()
        + "|"
        + body.strip()
        + "|"
        + received_at.strip()
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()
