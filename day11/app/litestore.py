from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.chunking import chunk_all


class LiteStore:
    """Same interface as VectorStore, but ranks chunks with TF-IDF instead of embeddings.

    It needs no PyTorch and no model download, so it fits on a small free server.
    """

    def __init__(self, chunks: list[dict[str, Any]]):
        self.chunks = chunks
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self.matrix = self.vectorizer.fit_transform([chunk["text"] for chunk in chunks])

    def count(self) -> int:
        return len(self.chunks)

    def search(self, query: str, n: int = 3) -> list[dict[str, Any]]:
        scores = cosine_similarity(self.vectorizer.transform([query]), self.matrix)[0]
        best = scores.argsort()[::-1][:n]
        hits = []
        for index in best:
            chunk = self.chunks[int(index)]
            hits.append({
                "id": chunk["id"],
                "text": chunk["text"],
                "title": chunk["title"],
                "page": chunk["page"],
                "source": chunk["source"],
                "distance": round(1 - float(scores[index]), 3),
            })
        return hits


def build_lite_store(chunk_size: int = 600, overlap: int = 100) -> LiteStore:
    return LiteStore(chunk_all(chunk_size, overlap))