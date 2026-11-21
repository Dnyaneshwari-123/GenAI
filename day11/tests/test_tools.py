import pytest

from app.tools import scam_red_flag_score

KYC_SMS = "Dear customer, your SBI KYC will expire today. Update immediately at bit.ly/sbi-kyc or your account will be blocked."


@pytest.mark.parametrize(
    ("message", "rule"),
    [
        ("Please share your OTP with me", "otp_or_pin_request"),
        ("Your KYC will expire, update it now", "kyc_or_account_threat"),
        ("Act immediately", "urgency"),
        ("Click bit.ly/abc123 to continue", "shortened_link"),
        ("You won a lottery", "lottery_or_prize"),
        ("Pay the processing fee first", "advance_fee"),
        ("Approve the collect request on your UPI app", "upi_collect_request"),
        ("Please install AnyDesk", "remote_access_app"),
    ],
)
def test_each_rule_fires_on_its_own_example(message, rule):
    result = scam_red_flag_score(message)
    assert rule in [item["rule"] for item in result["fired"]]


def test_scam_sms_is_high_risk():
    result = scam_red_flag_score(KYC_SMS)
    assert result["score"] == 70
    assert result["level"] == "high"


def test_genuine_otp_message_scores_zero():
    result = scam_red_flag_score("Your OTP is 482913. Do not share it with anyone. - HDFC Bank")
    assert result["score"] == 0
    assert result["fired"] == []


def test_curly_apostrophe_in_a_safe_phrase_is_handled():
    assert scam_red_flag_score("Don’t share your OTP with anyone.")["score"] == 0


def test_score_is_capped_at_100():
    text = "Share your OTP. Install AnyDesk. You won a lottery, pay a processing fee. Approve the collect request. KYC update at bit.ly/x immediately"
    assert scam_red_flag_score(text)["score"] == 100


def test_empty_text_is_low_risk():
    result = scam_red_flag_score("")
    assert result["score"] == 0
    assert result["level"] == "low"


def test_result_has_the_expected_shape():
    result = scam_red_flag_score(KYC_SMS)
    assert set(result) == {"score", "level", "fired", "advice"}
    for item in result["fired"]:
        assert set(item) == {"rule", "weight", "matched"}