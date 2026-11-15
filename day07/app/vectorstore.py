import os
import chromadb

from app.chunking import chunk_all
from app.embed import Embedder

BASE = os.path.dirname(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE, "chroma_db")


class VectorStore:

    def __init__(self, path=DB_PATH):
        self.client = chromadb.PersistentClient(path=path)
        self.collection = self.client.get_or_create_collection(name="cybersuraksha")
        self.embedder = Embedder()

    def count(self):
        return self.collection.count()

    def index(self, chunks):
        texts = [chunk["text"] for chunk in chunks]
        vectors = self.embedder.embed(texts)
        self.collection.upsert(
            ids=[chunk["id"] for chunk in chunks],
            documents=texts,
            embeddings=vectors,
            metadatas=[
                {"source": chunk["source"], "page": chunk["page"], "title": chunk["title"]}
                for chunk in chunks
            ],
        )

    def search(self, query, n=3):
        vector = self.embedder.embed([query])
        result = self.collection.query(query_embeddings=vector, n_results=n)

        hits = []
        for i in range(len(result["ids"][0])):
            metadata = result["metadatas"][0][i]
            hits.append({
                "id": result["ids"][0][i],
                "text": result["documents"][0][i],
                "title": metadata["title"],
                "page": metadata["page"],
                "source": metadata["source"],
                "distance": round(result["distances"][0][i], 3),
            })
        return hits


if __name__ == "__main__":
    store = VectorStore()
    store.index(chunk_all())
    print("Chunks in the collection:", store.count())