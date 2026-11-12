import json
import re
from pypdf import PdfReader
from app.models import Record

RAW_FILE = "data/raw/beaware.pdf"
TEXT_FILE = "data/raw/beaware_text.txt"
OUT_FILE = "data/records.json"
SOURCE_URL = "https://rbidocs.rbi.org.in/rdocs/content/pdfs/BEAWARE07032022.pdf"
FOOTER = r"Office of RBI Ombudsman\s+https://cms\.rbi\.org\.in/\s*\d*"

CHANNELS = [
    ("online sales", "Online marketplace"),
    ("screen sharing", "Remote access app"),
    ("mobile app", "Mobile app"),
    ("loan websites", "Website"),
    ("search engine", "Search engine"),
    ("qr code", "QR code"),
    ("sim swap", "SIM/Mobile network"),
    ("atm", "ATM"),
    ("social media", "Social media"),
    ("juice", "Physical device"),
    ("vishing", "Phone call"),
    ("phishing", "SMS/Link"),
    ("sms", "SMS/Link"),
    ("otp", "SMS/Link"),
    ("lottery", "Email/Phone call"),
    ("job", "Website"),
    ("mule", "Email"),
    ("advertisement", "Email"),
    ("ponzi", "Investment scheme"),
    ("forged", "Documents"),
]


def clean(text):
    text = re.sub(r"[➢•●]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def guess_channel(name):
    name = name.lower()
    for word, channel in CHANNELS:
        if word in name:
            return channel
    return "Other"


def make_record(part):
    lines = part.strip().split("\n")
    name = clean(re.sub(r"^\d+\s*\.?\s*", "", lines[0]))
    if not re.match(r"^\d{1,2}\s*\.\s*\S", lines[0]):
        raise ValueError("not a numbered heading")
    body = re.sub(FOOTER, " ", "\n".join(lines[1:]))

    start = re.search(r"modus\s+operandi", body, re.IGNORECASE)
    if start is None:
        raise ValueError("no 'Modus Operandi' found")
    rest = body[start.end():]
    pre = re.search(r"precautions?", rest, re.IGNORECASE)
    if pre is None:
        raise ValueError("no 'Precautions' found")

    how = clean(rest[:pre.start()])
    precautions = clean(rest[pre.end():])
    for stop in ["Modus Operandi and Precautions", "General Precautions"]:
        if stop in precautions:
            precautions = precautions.split(stop)[0].strip()
    precautions = re.sub(r"\s+\d{1,2}$", "", precautions)

    if len(how) < 40 or len(precautions) < 20:
        raise ValueError("too short, not a real fraud entry")

    return Record(name, guess_channel(name), how, "", precautions, SOURCE_URL)


try:
    reader = PdfReader(RAW_FILE)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
except Exception as error:
    print("Could not read the PDF:", error)
    raise SystemExit

with open(TEXT_FILE, "w", encoding="utf-8") as f:
    f.write(text)

records = []
for part in re.split(r"\n(?=\d{1,2}\.\s+[A-Z])", text):
    try:
        records.append(make_record(part))
    except ValueError as error:
        print("Bad row skipped:", error, "->", part[:50].replace("\n", " "))

# Juice jacking is sometimes lost by the PDF reader, so add it by hand if missing
if not any("juice" in r.fraud_name.lower() for r in records):
    print("Juice jacking missing from the PDF text, adding it by hand")
    records.insert(10, Record(
        "Juice jacking",
        "Physical device",
        "When a phone is plugged into an unknown or tampered public charging port or cable, malware can be installed and the fraudster can reach sensitive data on the phone.",
        "",
        "Avoid public or unknown charging ports and cables. Use your own charger or power bank.",
        SOURCE_URL,
    ))

for number, rec in enumerate(records, start=1):
    rec.id = number

with open(OUT_FILE, "w", encoding="utf-8") as f:
    json.dump([r.to_dict() for r in records], f, indent=4, ensure_ascii=False)

print("Total records:", len(records))