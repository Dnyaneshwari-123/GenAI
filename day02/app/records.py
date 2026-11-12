
import json

def load_records():
    file = open("data/sample_records.json", "r")
    records = json.load(file)
    file.close()

    return records


def search(records, keyword):
    result = []

    for record in records:
        if keyword.lower() in record["fraud_name"].lower():
            result.append(record)

    return result


def count_by(records):
    counts = {}

    for record in records:
        category = record["category"]

        if category in counts:
            counts[category] = counts[category] + 1
        else:
            counts[category] = 1

    return counts


def get_by_id(records, record_id):
    for record in records:
        if record["id"] == record_id:
            return record

    return None
