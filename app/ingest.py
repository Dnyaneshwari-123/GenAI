import json
import re
from pypdf import PdfReader
from app.models import Record

RAW_FILE = "data/raw/beaware.pdf"
OUT_FILE = "data/records.json"
SOURCE_URL = "https://rbidocs.rbi.org.in/rdocs/content/pdfs/BEAWARE07032022.pdf"


def clean(text):
    text = re.sub(r"[➢•●]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def guess_channel(text):
    text = text.lower()
    if "sms" in text or "link" in text:
        return "SMS/Link"
    elif "call" in text:
        return "Phone call"
    elif "atm" in text:
        return "ATM"
    elif "qr" in text:
        return "QR code"
    elif "sim" in text:
        return "SIM/Mobile network"
    elif "email" in text:
        return "Email"
    elif "social media" in text:
        return "Social media"
    else:
        return "Other"


def make_record(part):
    lines = part.strip().split("\n")
    name = clean(re.sub(r"^\d+\.\s*", "", lines[0]))
    body = "\n".join(lines[1:])
    low = body.lower()

    start = low.index("modus operandi")      # error if missing
    pre = low.index("precautions", start)    # error if missing
    how = clean(body[start + 14:pre])
    precautions = clean(body[pre + 11:])[:800]

    if not name or not how or not precautions:
        raise ValueError("empty field")

    return Record(name, guess_channel(name + " " + how), how, "", precautions, SOURCE_URL)


try:
    reader = PdfReader(RAW_FILE)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
except Exception as error:
    print("Could not read the PDF:", error)
    raise SystemExit

with open("data/raw/beaware_text.txt", "w", encoding="utf-8") as f:
    f.write(text)

records = []
for part in re.split(r"\n(?=\d{1,2}\.\s+[A-Z])", text):
    try:
        records.append(make_record(part).to_dict())
    except ValueError as error:
        print("Bad row skipped:", error)

with open(OUT_FILE, "w", encoding="utf-8") as f:
    json.dump(records, f, indent=4, ensure_ascii=False)

print("Total records:", len(records))