from app.records import load_records

REQUIRED_FIELDS = {"id", "fraud_name", "channel", "how_it_works", "warning_signs", "precautions", "source_url"}


def test_load_records_returns_a_list_of_dicts():
    records = load_records()
    assert isinstance(records, list)
    assert len(records) >= 15
    assert all(isinstance(record, dict) for record in records)


def test_every_record_has_the_required_fields(records):
    for record in records:
        assert REQUIRED_FIELDS <= set(record), record["fraud_name"]


def test_ids_are_unique(records):
    ids = [record["id"] for record in records]
    assert len(ids) == len(set(ids))


def test_records_have_text_and_a_source(records):
    for record in records:
        assert record["fraud_name"].strip()
        assert record["how_it_works"].strip()
        assert record["precautions"].strip()
        assert record["source_url"].startswith("http")