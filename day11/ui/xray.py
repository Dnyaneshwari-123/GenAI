import html
import re
from typing import Any

from app.tools import SAFE_PHRASES, scam_red_flag_score

HIGHLIGHT_GROUPS = [
    ("OTP / PIN", r"\b(otp|one[- ]time password|pin|cvv|password|passcode)\b"),
    ("KYC", r"\bkyc\b|\b(aadhaar|aadhar|pan card)\b"),
    ("Urgent", r"\b(urgent(ly)?|immediately|right now|at once|last chance|expires? today|final (notice|warning)|within \d+ ?(hours|hrs|minutes|mins)|blocked|suspended|deactivated)\b"),
    ("Link", r"https?://\S+|\b(bit\.ly|tinyurl\.com|goo\.gl|cutt\.ly|rb\.gy|is\.gd|shorturl\.at|ow\.ly|tiny\.cc|t\.ly|t\.co)/\S+"),
    ("Prize", r"\b(lottery|lucky draw|jackpot|prize|winner|congratulations|you (have )?won)\b"),
    ("Fee", r"\b(processing|registration|claim|release|clearance|delivery|customs|gst)\s+(fee|fees|charges?)\b"),
    ("UPI request", r"\b(collect request|request money|payment request|money request)\b"),
    ("Remote app", r"\b(anydesk|any desk|teamviewer|team viewer|quicksupport|quick support|airdroid|rustdesk|ultraviewer|screen ?shar\w*|remote (access|support|control))\b"),
]

RULE_TO_PATTERN = {
    "otp_or_pin_request": "vishing",
    "kyc_or_account_threat": "phishing",
    "shortened_link": "phishing",
    "lottery_or_prize": "lottery",
    "advance_fee": "lottery",
    "upi_collect_request": "online sales",
    "remote_access_app": "screen sharing",
}

LOSS_PATTERN = (
    r"\b(i|we)\s+(have\s+|had\s+|already\s+)*(paid|sent|transferred|lost|shared my (otp|pin|password|cvv))\b"
    r"|\bmy money\b"
    r"|\bmoney (was|got|has been|is)\s+(debited|deducted|stolen|gone|withdrawn|transferred)\b"
    r"|\b(was|got|been)\s+(debited|deducted|defrauded|cheated|scammed)\b"
    r"|\bunauthori[sz]ed (transaction|debit)\b"
)

LEVEL_COLOR = {"low": "#2e7d32", "medium": "#e65100", "high": "#b00020"}


def money_lost(text: str) -> bool:
    cleaned = str(text).replace("’", "'")
    return re.search(LOSS_PATTERN, cleaned, re.IGNORECASE) is not None


def highlight(text: str, fired: list[str] | None = None) -> tuple[str, list[dict[str, str]]]:
    text = str(text)
    matching = text.replace("’", "'")

    safe_spans = [m.span() for m in re.finditer(SAFE_PHRASES, matching, re.IGNORECASE)]

    found = []
    for category, pattern in HIGHLIGHT_GROUPS:
        if category == "OTP / PIN" and fired is not None and "otp_or_pin_request" not in fired:
            continue
        for m in re.finditer(pattern, matching, re.IGNORECASE):
            start, end = m.span()
            inside_safe = any(start < s_end and end > s_start for s_start, s_end in safe_spans)
            if not inside_safe:
                found.append((start, end, category))

    found.sort(key=lambda item: (item[0], -(item[1] - item[0])))

    kept = []
    last_end = 0
    for start, end, category in found:
        if start >= last_end:
            kept.append((start, end, category))
            last_end = end

    parts = []
    position = 0
    for start, end, category in kept:
        parts.append(html.escape(text[position:start]))
        parts.append(
            '<mark style="background:#ffd6d6;color:#b00020;border-radius:4px;padding:0 4px;font-weight:600" '
            'title="' + html.escape(category) + '">' + html.escape(text[start:end]) + "</mark>"
        )
        position = end
    parts.append(html.escape(text[position:]))

    page = "".join(parts).replace("\n", "<br>")
    hits = [{"category": category, "text": text[start:end]} for start, end, category in kept]
    return page, hits


def match_pattern(result: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any] | None:
    weights: dict[str, int] = {}
    for item in result["fired"]:
        keyword = RULE_TO_PATTERN.get(item["rule"])
        if keyword:
            weights[keyword] = weights.get(keyword, 0) + item["weight"]
    if not weights:
        return None

    best = max(weights, key=lambda keyword: weights[keyword])
    for record in records:
        if best in record["fraud_name"].lower():
            return record
    return None


def run_xray(text: str, records: list[dict[str, Any]], lost_checked: bool = False) -> dict[str, Any]:
    result = scam_red_flag_score(text)
    page, hits = highlight(text, [item["rule"] for item in result["fired"]])
    return {
        "score": result["score"],
        "level": result["level"],
        "advice": result["advice"],
        "fired": result["fired"],
        "html": page,
        "hits": hits,
        "pattern": match_pattern(result, records),
        "lost": bool(lost_checked) or money_lost(text),
    }


def call_1930_html() -> str:
    return (
        '<div style="background:#b00020;color:white;padding:24px;border-radius:16px;text-align:center;margin:8px 0 18px 0">'
        '<div style="font-size:14px;letter-spacing:2px;font-weight:600">MONEY ALREADY LOST?</div>'
        '<div style="font-size:46px;font-weight:800;margin:6px 0">📞 Call 1930 now</div>'
        '<a href="tel:1930" style="display:inline-block;background:white;color:#b00020;font-weight:700;'
        'padding:10px 26px;border-radius:30px;text-decoration:none;font-size:20px">Tap to call 1930</a>'
        '<div style="margin-top:14px;font-size:16px;line-height:1.5">'
        "1930 is the National Cyber Crime Helpline. Report quickly, because early reports give the best chance "
        "of stopping the money. Then report at cybercrime.gov.in, tell your bank to block the card or UPI, "
        "and keep screenshots and transaction IDs."
        "</div></div>"
    )