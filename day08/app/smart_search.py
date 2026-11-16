from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class SmartSearch:
    def __init__(self, records):
        self.records = records
        texts = []
        for r in records:
            texts.append(r["fraud_name"] + " " + r["channel"] + " " +
                         r["how_it_works"] + " " + r["precautions"])
        self.vectorizer = TfidfVectorizer(stop_words="english")
        self.matrix = self.vectorizer.fit_transform(texts)

    def search(self, query, top_n=5):
        query_vector = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vector, self.matrix)[0]
        ranked = sorted(zip(scores, self.records), key=lambda x: x[0], reverse=True)

        results = []
        for score, record in ranked[:top_n]:
            if score > 0:
                item = dict(record)
                item["score"] = round(float(score), 3)
                results.append(item)
        return results