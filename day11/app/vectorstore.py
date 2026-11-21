import os

import chromadb

from app.chunking import chunk_all
from app.embed import Embedder

BASE = os.path.dirname(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE, "chroma_db")


class VectorStore:

    def __init__(self, name="cybersuraksha", embedder=None, path=DB_PATH):
        self.name = name
        self.client = chromadb.PersistentClient(path=path)
        self.collection = self.client.get_or_create_collection(name=name)
        self.embedder = embedder or Embedder()

    def count(self):
        return self.collection.count()

    def index(self, chunks):
        self.client.delete_collection(self.name)
        self.collection = self.client.get_or_create_collection(name=self.name)

        texts = [chunk["text"] for chunk in chunks]
        vectors = self.embedder.embed(texts)
        self.collection.add(
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


def build_store(chunk_size=600, overlap=100, embedder=None):
    name = "cs_" + str(chunk_size) + "_" + str(overlap)
    store = VectorStore(name=name, embedder=embedder)
    if store.count() == 0:
        store.index(chunk_all(chunk_size, overlap))
    return store

if __name__ == "__main__":
    store = build_store(600, 100)
    print("Chunks in the collection:", store.count())