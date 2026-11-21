from tests.conftest import FakeLLM


def test_health_reports_records_and_llm(make_client):
    client = make_client(llm=FakeLLM())
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["records"] >= 15
    assert body["llm_ready"] is True


def test_health_works_without_an_llm_key(make_client):
    body = make_client(llm=None).get("/health").json()
    assert body["status"] == "ok"
    assert body["llm_ready"] is False


def test_records_limit(make_client):
    client = make_client()
    assert len(client.get("/records", params={"limit": 3}).json()) == 3


def test_record_by_id_and_404(make_client):
    client = make_client()
    assert client.get("/records/1").json()["id"] == 1
    assert client.get("/records/999").status_code == 404


def test_search_endpoint_returns_ranked_records(make_client):
    results = make_client().get("/search", params={"q": "QR code"}).json()
    assert results
    assert "qr" in results[0]["fraud_name"].lower()