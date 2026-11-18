import re

SAFE_PHRASES = r"\b(do not|don't|dont|never)\s+(share|disclose|give|tell|reveal)\b[^.!\n]{0,60}"

RULES = [
    {
        "name": "otp_or_pin_request",
        "weight": 35,
        "pattern": r"\b(share|send|tell|give|enter|provide|confirm|forward|reply|read out)\b.{0,40}\b(otp|pin|cvv|password|passcode)\b"
                   r"|\b(otp|pin|cvv|password|passcode)\b.{0,40}\b(share|send|tell|give|forward|reply)\b",
    },
    {
        "name": "kyc_or_account_threat",
        "weight": 30,
        "pattern": r"\b(kyc|pan|aadhaar|aadhar)\b.{0,60}\b(update|updation|verify|verification|expire[sd]?|expiring|suspend\w*|block\w*|deactivat\w*)\b"
                   r"|\b(account|card|sim|number)\b.{0,40}\b(blocked|suspended|deactivated|frozen|closed)\b",
    },
    {
        "name": "urgency",
        "weight": 15,
        "pattern": r"\b(immediately|urgent|urgently|right now|at once|last chance|expires? today|final (notice|warning)|within \d+ ?(hours|hrs|minutes|mins))\b",
    },
    {
        "name": "shortened_link",
        "weight": 25,
        "pattern": r"\b(bit\.ly|tinyurl\.com|goo\.gl|cutt\.ly|rb\.gy|is\.gd|shorturl\.at|ow\.ly|tiny\.cc|t\.ly|t\.co)/\S+",
    },
    {
        "name": "lottery_or_prize",
        "weight": 35,
        "pattern": r"\b(lottery|lucky draw|jackpot|you (have )?won|you are (the )?(a )?winner|prize|congratulations)\b",
    },
    {
        "name": "advance_fee",
        "weight": 25,
        "pattern": r"\b(processing|registration|claim|release|clearance|delivery|customs|gst)\s+(fee|fees|charges?)\b"
                   r"|\bpay (a |the )?(small )?(fee|amount|charges?)\b",
    },
    {
        "name": "upi_collect_request",
        "weight": 35,
        "pattern": r"\b(collect request|request money|payment request|money request)\b"
                   r"|\bapprove\b.{0,30}\b(request|collect)\b"
                   r"|\benter\b.{0,20}\bupi pin\b.{0,40}\b(receive|get|credit)\b",
    },
    {
        "name": "remote_access_app",
        "weight": 40,
        "pattern": r"\b(anydesk|any desk|teamviewer|team viewer|quicksupport|quick support|airdroid|rustdesk|ultraviewer|screen ?shar\w*|remote (access|support|control))\b",
    },
]

ADVICE = {
    "low": "No red flags matched. This does not prove the message is safe, so do not click links or share codes if you are unsure.",
    "medium": "Some red flags matched. Do not click links or share any code. Check with your bank using the number on your card.",
    "high": "Many red flags matched. This looks like a scam. Do not click, reply, pay or install anything. Call 1930 or report at cybercrime.gov.in.",
}


def scam_red_flag_score(text):
    cleaned = str(text).replace("’", "'")
    cleaned = re.sub(SAFE_PHRASES, " ", cleaned, flags=re.IGNORECASE)

    fired = []
    total = 0
    for rule in RULES:
        match = re.search(rule["pattern"], cleaned, re.IGNORECASE | re.DOTALL)
        if match:
            total = total + rule["weight"]
            fired.append({
                "rule": rule["name"],
                "weight": rule["weight"],
                "matched": match.group(0)[:60].strip(),
            })

    score = min(total, 100)
    if score >= 60:
        level = "high"
    elif score >= 25:
        level = "medium"
    else:
        level = "low"

    return {"score": score, "level": level, "fired": fired, "advice": ADVICE[level]}


if __name__ == "__main__":
    samples = [
        "Dear customer, your SBI KYC will expire today. Update immediately at bit.ly/sbi-kyc or your account will be blocked.",
        "Congratulations! You won a lottery of Rs 25,00,000. Pay a processing fee of Rs 5,000 to claim it.",
        "Hi, I am from your bank. Please install AnyDesk and tell me the 9-digit code. Also share your OTP.",
        "Approve the collect request on your UPI app to receive Rs 5000 refund.",
        "Your OTP is 482913. Do not share it with anyone. - HDFC Bank",
        "Rs 1,200 debited from A/c XX1234 on 12-Nov. Not you? Call your bank.",
    ]
    for sample in samples:
        result = scam_red_flag_score(sample)
        names = [f["rule"] for f in result["fired"]]
        print(result["score"], result["level"], names)