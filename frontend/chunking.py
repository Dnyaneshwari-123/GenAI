"""Splits record text into overlapping chunks. Used by the Chunking tab in frontend.py."""


def chunk_text(text, size=600, overlap=100):
    """Cut text into pieces of at most `size` characters; each piece repeats the last `overlap` characters of the previous one."""
    if size <= 0:
        raise ValueError("size must be greater than 0")
    if not 0 <= overlap < size:
        raise ValueError("overlap must be 0 or more and smaller than size")

    text = " ".join(text.split())
    if not text:
        return []

    chunks = []
    start = 0
    step = size - overlap
    while start < len(text):
        chunks.append(text[start:start + size])
        if start + size >= len(text):
            break
        start += step
    return chunks


def record_text(record):
    """Join the useful fields of one fraud record into a single text."""
    parts = [
        record.get("fraud_name", ""),
        record.get("how_it_works", ""),
        record.get("warning_signs", ""),
        record.get("precautions", ""),
    ]
    return ". ".join(p.strip() for p in parts if p and p.strip())


def chunk_records(records, size, overlap):
    """Chunk every record. Returns a list of {record, part, text}."""
    result = []
    for record in records:
        pieces = chunk_text(record_text(record), size, overlap)
        for number, piece in enumerate(pieces, 1):
            result.append({
                "record": record.get("fraud_name", "?"),
                "part": number,
                "text": piece,
            })
    return result


def compare(records, configs):
    """configs: list of (name, size, overlap). Returns one summary row per config."""
    rows = []
    for name, size, overlap in configs:
        chunks = chunk_records(records, size, overlap)
        lengths = [len(c["text"]) for c in chunks]
        rows.append({
            "Config": name,
            "Chunk size": size,
            "Overlap": overlap,
            "Chunks": len(chunks),
            "Avg length": round(sum(lengths) / len(lengths)) if lengths else 0,
        })
    return rows
