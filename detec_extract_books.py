import cv2
import easyocr
import requests
from ultralytics import YOLO

# Load models (COCO class 73 = 'book')
detector = YOLO("yolo11n.pt")
reader = easyocr.Reader(['pt', 'en'])


def search_books_official(raw_text):
    """Query Google Books API (with Open Library fallback) to fetch official metadata."""
    cleaned = " ".join(word for word in raw_text.split() if len(word) > 1)
    if len(cleaned) < 4:
        return None

    # 1. Primary: Google Books API
    try:
        res = requests.get(
            "https://www.googleapis.com/books/v1/volumes",
            params={"q": cleaned, "maxResults": 1},
            timeout=8,
        ).json()
        if "items" in res:
            info = res["items"][0]["volumeInfo"]
            image_links = info.get("imageLinks", {})
            cover_url = image_links.get("thumbnail") or image_links.get("smallThumbnail") or ""
            return {
                "title": info.get("title"),
                "authors": info.get("authors", ["Unknown"]),
                "description": info.get("description", "No description available."),
                "categories": info.get("categories", []),
                "image_url": cover_url.replace("http://", "https://"),
            }
    except Exception as e:
        print(f"  [Google Books Warning]: {e}")

    # 2. Fallback: Open Library API
    try:
        ol_res = requests.get(
            "https://openlibrary.org/search.json",
            params={"q": cleaned, "limit": 1},
            timeout=8,
        ).json()
        if ol_res.get("docs"):
            doc = ol_res["docs"][0]
            cover_id = doc.get("cover_i")
            cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg" if cover_id else ""
            return {
                "title": doc.get("title"),
                "authors": doc.get("author_name", ["Unknown"]),
                "description": ", ".join(doc.get("subject", [])[:5]) or "No description available.",
                "categories": doc.get("subject", [])[:3],
                "image_url": cover_url,
            }
    except Exception as e:
        print(f"  [Open Library Warning]: {e}")

    return None


def extract_cover_query(detections):
    """For single book covers, prioritize the largest text blocks (title & author)."""
    scored_texts = []
    for bbox, text, conf in detections:
        if conf < 0.35 or len(text.strip()) < 2:
            continue
        # Calculate bounding box height as a proxy for font size
        height = abs(bbox[2][1] - bbox[0][1])
        y_top = bbox[0][1]
        scored_texts.append((height, y_top, text.strip()))

    if not scored_texts:
        return ""

    # Keep texts that are at least 45% as tall as the largest font on the cover
    max_height = max(item[0] for item in scored_texts)
    main_blocks = [item for item in scored_texts if item[0] >= max_height * 0.45]

    # Sort top-to-bottom to preserve natural reading order (e.g., Author + Title)
    main_blocks.sort(key=lambda item: item[1])
    return " ".join(item[2] for item in main_blocks)


def bookshelf_process(img_path):
    """Detect book spines via YOLO or fall back to single-cover/full-image OCR."""
    img = cv2.imread(img_path)
    if img is None:
        raise FileNotFoundError(f"Could not load image at: {img_path}")

    # Resize large images for faster, cleaner inference
    max_dim = 1600
    h, w = img.shape[:2]
    if max(h, w) > max_dim:
        scale = max_dim / max(h, w)
        img = cv2.resize(img, (int(w * scale), int(h * scale)))

    results = detector(img, classes=[73], conf=0.15, imgsz=1280)
    results[0].save("debug_yolo.jpg")

    found_books = []
    boxes = results[0].boxes

    # CASE A: Multiple books/spines detected on a shelf
    if len(boxes) > 0:
        print(f"YOLO detected {len(boxes)} candidate books. Extracting text...")
        for box in boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            crop = img[y1:y2, x1:x2]

            ch, cw, _ = crop.shape
            orientations = (
                [cv2.rotate(crop, cv2.ROTATE_90_CLOCKWISE), cv2.rotate(crop, cv2.ROTATE_90_COUNTERCLOCKWISE)]
                if ch > cw * 1.3
                else [crop]
            )

            for oriented_crop in orientations:
                texts = reader.readtext(oriented_crop, detail=0)
                unified_text = " ".join(texts)
                book = search_books_official(unified_text)
                if book and not any(b["title"] == book["title"] for b in found_books):
                    found_books.append(book)
                    break

    # CASE B (Fallback): Single full-frame book cover or shelf missed by YOLO
    else:
        print("No bounding boxes from YOLO. Analyzing as full cover / shelf OCR...")
        detections = reader.readtext(img, detail=1)
        cover_query = extract_cover_query(detections)
        print(f"  [OCR Main Text] Extracted query: '{cover_query}'")

        book = search_books_official(cover_query)
        if book:
            found_books.append(book)
        else:
            # If upright reading fails, test 90-degree rotations (for vertical spines)
            for rot_code in [cv2.ROTATE_90_CLOCKWISE, cv2.ROTATE_90_COUNTERCLOCKWISE]:
                rot_img = cv2.rotate(img, rot_code)
                rot_detections = reader.readtext(rot_img, detail=1)
                rot_query = extract_cover_query(rot_detections)
                book = search_books_official(rot_query)
                if book and not any(b["title"] == book["title"] for b in found_books):
                    found_books.append(book)

    return found_books