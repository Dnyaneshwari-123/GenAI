import json
import os

BASE = os.path.dirname(os.path.dirname(__file__))
DATA_FILE = os.path.join(BASE, "data", "records.json")


def load_records():
    with open(DATA_FILE, encoding="utf-8") as f:
        return json.load(f)