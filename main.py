import os
import json
import webbrowser
from datetime import datetime
import requests
from detec_extract_books import bookshelf_process
from recommend_books import recommend_books


def search_dynamic_candidates(bookshelf_books, max_per_query=15):
    """Build a candidate catalog dynamically with full metadata and cover images."""
    queries = []
    for book in bookshelf_books:
        for cat in book.get("categories", [])[:2]:
            queries.append(f"subject:{cat}")
        for author in book.get("authors", [])[:1]:
            if author != "Unknown":
                queries.append(f"inauthor:{author}")
        if book.get("title"):
            queries.append(book["title"])

    unique_queries = list(dict.fromkeys(queries))[:4]
    candidates = []
    seen_titles = set()

    # 1. Primary: Google Books API
    for q in unique_queries:
        try:
            res = requests.get(
                "https://www.googleapis.com/books/v1/volumes",
                params={"q": q, "maxResults": max_per_query},
                timeout=8,
            ).json()
        except Exception:
            continue

        for item in res.get("items", []):
            info = item.get("volumeInfo", {})
            title = info.get("title")
            if title and title.lower() not in seen_titles:
                seen_titles.add(title.lower())
                image_links = info.get("imageLinks", {})
                cover_url = image_links.get("thumbnail") or image_links.get("smallThumbnail") or ""

                candidates.append({
                    "title": title,
                    "authors": info.get("authors", ["Unknown"]),
                    "description": info.get("description", "No description available."),
                    "categories": info.get("categories", []),
                    "image_url": cover_url.replace("http://", "https://"),
                })

    # 2. Fallback: Open Library API
    if not candidates and bookshelf_books:
        fallback_term = (
            bookshelf_books[0]["categories"][0]
            if bookshelf_books[0].get("categories")
            else bookshelf_books[0]["authors"][0]
        )
        try:
            ol_res = requests.get(
                "https://openlibrary.org/search.json",
                params={"q": fallback_term, "limit": max_per_query},
                timeout=8,
            ).json()
            for doc in ol_res.get("docs", []):
                title = doc.get("title")
                if title and title.lower() not in seen_titles:
                    seen_titles.add(title.lower())
                    cover_id = doc.get("cover_i")
                    cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg" if cover_id else ""

                    candidates.append({
                        "title": title,
                        "authors": doc.get("author_name", ["Unknown"]),
                        "description": ", ".join(doc.get("subject", [])[:5]) or "No description available.",
                        "categories": doc.get("subject", [])[:3],
                        "image_url": cover_url,
                    })
        except Exception:
            pass

    return candidates


def export_to_view(recommendations):
    """Export recommendations exclusively to the view/ repository page and open it."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    view_dir = os.path.join(base_dir, "view")
    os.makedirs(view_dir, exist_ok=True)

    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "recommendations": recommendations,
    }

    data_js_path = os.path.join(view_dir, "data.js")
    with open(data_js_path, "w", encoding="utf-8") as f:
        f.write(f"window.SHELF_DATA = {json.dumps(payload, ensure_ascii=False, indent=2)};")

    index_path = os.path.join(view_dir, "index.html")
    webbrowser.open(f"file:///{index_path.replace(os.sep, '/')}")


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    photo_path = os.path.join(base_dir, "content", "book1.jpg")

    if not os.path.exists(photo_path):
        print(f"Error: Image not found at '{photo_path}'")
        exit(1)

    print("1. Scanning bookshelf image...")
    books_on_bookshelf = bookshelf_process(photo_path)

    if not books_on_bookshelf:
        print("No books could be clearly identified.")
    else:
        print(f"Detected {len(books_on_bookshelf)} book(s). Fetching recommendations...")
        candidates = search_dynamic_candidates(books_on_bookshelf)

        if candidates:
            recommendations = recommend_books(books_on_bookshelf, candidates, top_k=6)
            export_to_view(recommendations)
            print("Done! Opening repository page in your browser...")
        else:
            print("Could not build a candidate catalog.")