import pytest

from app.smart_search import SmartSearch


@pytest.fixture
def searcher(records):
    return SmartSearch(records)


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("someone asked me to scan a QR code to receive money", "qr"),
        ("SIM swap duplicate SIM card", "sim"),
        ("install a screen sharing app", "screen sharing"),
    ],
)
def test_top_hit_matches_the_topic(searcher, query, expected):
    top = searcher.search(query)[0]
    assert expected in top["fraud_name"].lower()


def test_results_are_sorted_by_score_and_respect_top_n(searcher):
    results = searcher.search("OTP", top_n=3)
    assert 1 <= len(results) <= 3
    scores = [item["score"] for item in results]
    assert scores == sorted(scores, reverse=True)


def test_nonsense_query_finds_nothing(searcher):
    assert searcher.search("zzzz qqqq xxxx") == []