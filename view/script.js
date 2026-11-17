let allBooks = [];

const booksGrid = document.getElementById("booksGrid");
const resultCount = document.getElementById("resultCount");
const scanTimestamp = document.getElementById("scanTimestamp");
const searchInput = document.getElementById("searchInput");
const sortSelect = document.getElementById("sortSelect");
const bookModal = document.getElementById("bookModal");
const modalBody = document.getElementById("modalBody");
const closeModal = document.getElementById("closeModal");

function init() {
  const payload = window.SHELF_DATA;

  if (!payload || !Array.isArray(payload.recommendations)) {
    resultCount.textContent = "No recommendations data found.";
    booksGrid.innerHTML = `
      <div class="empty-state">
        <h3>Repository is empty</h3>
        <p>Run <code>python main.py</code> to scan your bookshelf and populate this repository.</p>
      </div>`;
    return;
  }

  allBooks = payload.recommendations;
  if (payload.generated_at) {
    scanTimestamp.textContent = `Last scan: ${payload.generated_at}`;
  }

  renderBooks(allBooks);
}

function renderBooks(books) {
  resultCount.textContent = `Showing ${books.length} recommended ${books.length === 1 ? "book" : "books"}`;

  if (books.length === 0) {
    booksGrid.innerHTML = `
      <div class="empty-state">
        <h3>No matching books</h3>
        <p>Try clearing your search filter.</p>
      </div>`;
    return;
  }

  booksGrid.innerHTML = books
    .map((book, index) => {
      const matchPercent = Math.round((book.similarity || 0) * 100);
      const authors = Array.isArray(book.authors) ? book.authors.join(", ") : "Unknown";
      const coverHtml = book.image_url
        ? `<img class="book-cover" src="${book.image_url}" alt="${escapeHtml(book.title)}" loading="lazy" />`
        : `<div class="cover-placeholder">No Cover Available</div>`;

      return `
        <article class="book-card" data-index="${index}">
          ${coverHtml}
          <div class="book-info">
            <div>
              <span class="match-badge">${matchPercent}% Match</span>
              <h2 class="book-title">${escapeHtml(book.title)}</h2>
              <p class="book-author">${escapeHtml(authors)}</p>
              <p class="book-desc">${escapeHtml(book.description || "No description available.")}</p>
            </div>
            <span class="read-more">View details &rarr;</span>
          </div>
        </article>
      `;
    })
    .join("");

  document.querySelectorAll(".book-card").forEach((card) => {
    card.addEventListener("click", () => {
      const book = books[Number(card.dataset.index)];
      openBookModal(book);
    });
  });
}

function openBookModal(book) {
  const matchPercent = Math.round((book.similarity || 0) * 100);
  const authors = Array.isArray(book.authors) ? book.authors.join(", ") : "Unknown";
  const coverHtml = book.image_url
    ? `<img src="${book.image_url}" alt="${escapeHtml(book.title)}" />`
    : `<div class="cover-placeholder" style="width:150px;height:225px;">No Cover</div>`;

  modalBody.innerHTML = `
    ${coverHtml}
    <div class="modal-details">
      <span class="match-badge">${matchPercent}% Match</span>
      <h2>${escapeHtml(book.title)}</h2>
      <p class="author">By ${escapeHtml(authors)}</p>
      <p class="full-desc">${escapeHtml(book.description || "No description available.")}</p>
    </div>
  `;

  bookModal.classList.add("active");
  bookModal.setAttribute("aria-hidden", "false");
}

function applyFilters() {
  const query = searchInput.value.toLowerCase().trim();
  const sortBy = sortSelect.value;

  let filtered = allBooks.filter((b) => {
    const titleMatch = (b.title || "").toLowerCase().includes(query);
    const authorMatch = (b.authors || []).join(" ").toLowerCase().includes(query);
    const descMatch = (b.description || "").toLowerCase().includes(query);
    return titleMatch || authorMatch || descMatch;
  });

  if (sortBy === "title") {
    filtered.sort((a, b) => a.title.localeCompare(b.title));
  } else {
    filtered.sort((a, b) => (b.similarity || 0) - (a.similarity || 0));
  }

  renderBooks(filtered);
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

searchInput.addEventListener("input", applyFilters);
sortSelect.addEventListener("change", applyFilters);
closeModal.addEventListener("click", () => bookModal.classList.remove("active"));
bookModal.addEventListener("click", (e) => {
  if (e.target === bookModal) bookModal.classList.remove("active");
});

init();