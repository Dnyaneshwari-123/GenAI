import json
import os
import re
from pypdf import PdfReader

BASE = os.path.dirname(os.path.dirname(__file__))
FOOTER = r"Office of RBI Ombudsman\s+https://cms\.rbi\.org\.in/\s*\d*"

DOCUMENTS = [
    {
        "id": "beaware",
        "path": os.path.join(BASE, "data", "raw", "beaware.pdf"),
        "title": "BE(A)WARE: Booklet on Modus Operandi of Financial Fraudsters",
        "source": "https://rbidocs.rbi.org.in/rdocs/content/pdfs/BEAWARE07032022.pdf",
    },
]


def clean(text):
    text = re.sub(FOOTER, " ", text)
    text = re.sub(r"[➢•●]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def split_text(text, size=600, overlap=100):
    pieces = []
    start = 0
    while start < len(text):
        end = start + size
        if end < len(text):
            space = text.rfind(" ", start, end)
            if space > start + size // 2:
                end = space
        piece = text[start:end].strip()
        if piece:
            pieces.append(piece)
        if end >= len(text):
            break
        start = end - overlap
    return pieces


def chunk_document(doc):
    reader = PdfReader(doc["path"])
    chunks = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = clean(page.extract_text() or "")
        for number, piece in enumerate(split_text(text)):
            chunks.append({
                "id": doc["id"] + "-p" + str(page_number) + "-c" + str(number),
                "text": piece,
                "source": doc["source"],
                "page": page_number,
                "title": doc["title"],
            })
    return chunks


def chunk_all():
    chunks = []
    for doc in DOCUMENTS:
        chunks = chunks + chunk_document(doc)
    return chunks


if __name__ == "__main__":
    chunks = chunk_all()
    print("Total chunks:", len(chunks))
    print(chunks[len(chunks) // 2])
    with open(os.path.join(BASE, "data", "chunks.json"), "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)