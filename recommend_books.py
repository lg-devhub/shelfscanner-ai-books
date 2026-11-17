import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Lightweight multilingual semantic embedding model
embedder = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")


def recommend_books(bookshelf_books, candidates_catalog, top_k=5):
    """Rank candidate books by cosine similarity and return full metadata + score."""
    bookshelf_texts = [
        f"{b['title']} - {', '.join(b['categories'])}. {b['description']}".strip()
        for b in bookshelf_books
        if b.get("title")
    ]

    if not bookshelf_texts or not candidates_catalog:
        return []

    bookshelf_vectors = embedder.encode(bookshelf_texts)
    user_profile = np.mean(bookshelf_vectors, axis=0).reshape(1, -1)

    catalog_texts = [
        f"{c['title']} - {', '.join(c['categories'])}. {c['description']}".strip()
        for c in candidates_catalog
    ]
    catalog_vectors = embedder.encode(catalog_texts)

    similarities = cosine_similarity(user_profile, catalog_vectors)[0]
    top_indices = np.argsort(similarities)[::-1]

    existing_titles = {b["title"].lower() for b in bookshelf_books}
    recommendations = []

    for idx in top_indices:
        candidate = candidates_catalog[idx]
        if candidate["title"].lower() not in existing_titles:
            book_result = candidate.copy()
            book_result["similarity"] = float(similarities[idx])
            recommendations.append(book_result)
        if len(recommendations) == top_k:
            break

    return recommendations