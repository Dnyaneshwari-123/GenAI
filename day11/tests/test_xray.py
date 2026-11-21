import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.tools import scam_red_flag_score
from ui.xray import call_1930_html, highlight, match_pattern, money_lost, run_xray

with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "records.json"), encoding="utf-8") as f:
    RECORDS = json.load(f)

KYC_SMS = "Dear customer, your SBI KYC will expire today. Update immediately at bit.ly/sbi-kyc or your account will be blocked."
GOOD_OTP = "Your OTP is 482913. Do not share it with anyone. - HDFC Bank"


def test_scores_for_known_messages():
    assert scam_red_flag_score(KYC_SMS)["score"] == 70
    assert scam_red_flag_score(GOOD_OTP)["score"] == 0
    assert scam_red_flag_score("")["level"] == "low"


def test_score_is_capped_at_100():
    text = "Share your OTP. Install AnyDesk. You won a lottery, pay a processing fee. Approve the collect request. KYC update at bit.ly/x immediately"
    assert scam_red_flag_score(text)["score"] == 100


def test_highlight_finds_the_five_required_categories():
    text = "Urgent: share your OTP, update KYC at bit.ly/abc to claim your prize"
    _, hits = highlight(text)
    categories = {h["category"] for h in hits}
    assert {"Urgent", "OTP / PIN", "KYC", "Link", "Prize"} <= categories


def test_highlight_wraps_phrases_in_red_marks():
    page, hits = highlight("Share your OTP now")
    assert "<mark" in page and "#b00020" in page
    assert hits[0]["text"] == "OTP"


def test_highlight_skips_the_do_not_share_warning():
    page, hits = highlight("Never share your OTP with anyone. Regards, Bank")
    assert hits == []
    assert "<mark" not in page


def test_genuine_otp_message_is_not_highlighted_in_the_full_xray():
    out = run_xray(GOOD_OTP, RECORDS)
    assert out["score"] == 0 and out["hits"] == [] and "<mark" not in out["html"]


def test_otp_is_highlighted_when_it_is_requested():
    out = run_xray("Please share your OTP to avoid blocking", RECORDS)
    assert any(h["category"] == "OTP / PIN" for h in out["hits"])


def test_highlight_escapes_html():
    page, _ = highlight("<script>alert(1)</script> share your OTP")
    assert "<script>" not in page
    assert "&lt;script&gt;" in page


def test_highlight_keeps_original_text():
    text = "Hello world, no risk here"
    page, hits = highlight(text)
    assert page == text and hits == []


def test_money_lost_detection():
    assert money_lost("I already paid the fee and now they are not replying")
    assert money_lost("I shared my OTP and 20000 was debited")
    assert money_lost("Unauthorised transaction on my account")
    assert not money_lost(KYC_SMS)
    assert not money_lost("What is a SIM swap?")


def test_pattern_match_uses_the_records():
    assert match_pattern(scam_red_flag_score(KYC_SMS), RECORDS)["fraud_name"] == "Phishing links"
    anydesk = scam_red_flag_score("Install AnyDesk and tell me the code")
    assert "screen sharing" in match_pattern(anydesk, RECORDS)["fraud_name"].lower()
    assert match_pattern(scam_red_flag_score(GOOD_OTP), RECORDS) is None


def test_run_xray_ties_everything_together():
    out = run_xray(KYC_SMS, RECORDS)
    assert out["level"] == "high" and out["lost"] is False
    assert out["pattern"]["fraud_name"] == "Phishing links"
    assert run_xray(KYC_SMS, RECORDS, lost_checked=True)["lost"] is True


def test_call_1930_card_has_the_number():
    card = call_1930_html()
    assert "Call 1930 now" in card and "tel:1930" in card