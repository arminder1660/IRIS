const state = {
    query: "",
    page: 1,
    pageSize: 8,
    publication: "all",
    year: "all",
    total: 0,
    terms: [],
    suggestIndex: -1,
};

const els = {
    form: document.getElementById("searchForm"),
    query: document.getElementById("searchQuery"),
    publication: document.getElementById("filterPublication"),
    year: document.getElementById("filterYear"),
    resultsWrap: document.getElementById("resultsWrap"),
    resultsList: document.getElementById("resultsList"),
    statsLine: document.getElementById("statsLine"),
    statusBox: document.getElementById("statusBox"),
    emptyState: document.getElementById("emptyState"),
    prevPage: document.getElementById("prevPage"),
    nextPage: document.getElementById("nextPage"),
    pageLabel: document.getElementById("pageLabel"),
    suggestList: document.getElementById("suggestList"),
    reader: document.getElementById("reader"),
    readerTitle: document.getElementById("readerTitle"),
    readerMeta: document.getElementById("readerMeta"),
    readerBody: document.getElementById("readerBody"),
    backdrop: document.getElementById("drawerBackdrop"),
    closeReader: document.getElementById("closeReader"),
    clearFilters: document.getElementById("clearFilters"),
};

function escapeHtml(value) {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

function highlight(text, terms) {
    const safe = escapeHtml(text);
    if (!terms.length) return safe;
    const pattern = terms
        .filter(Boolean)
        .map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
        .join("|");
    if (!pattern) return safe;
    return safe.replace(new RegExp(`\\b(${pattern})\\b`, "gi"), "<mark class=\"mark\">$1</mark>");
}

function formatNumber(n) {
    return new Intl.NumberFormat().format(n);
}

async function loadMeta() {
    const res = await fetch("/api/meta");
    const data = await res.json();
    document.getElementById("statDocs").textContent = formatNumber(data.indexed_docs);
    document.getElementById("statVocab").textContent = formatNumber(data.vocabulary);
    document.getElementById("statRanker").textContent = data.ranker;
    document.getElementById("statBuild").textContent = `${data.build_seconds}s`;

    data.publications.forEach((name) => {
        const opt = document.createElement("option");
        opt.value = name;
        opt.textContent = name;
        els.publication.appendChild(opt);
    });
    data.years.forEach((year) => {
        const opt = document.createElement("option");
        opt.value = String(year);
        opt.textContent = String(year);
        els.year.appendChild(opt);
    });
}

function showStatus(html, kind = "status") {
    els.statusBox.innerHTML = `<div class="${kind}">${html}</div>`;
}

function hideSuggestions() {
    els.suggestList.hidden = true;
    els.suggestList.innerHTML = "";
    state.suggestIndex = -1;
}

async function fetchSuggestions(q) {
    if (q.length < 2) {
        hideSuggestions();
        return;
    }
    const res = await fetch(`/api/suggest?q=${encodeURIComponent(q)}`);
    const data = await res.json();
    if (!data.suggestions?.length) {
        hideSuggestions();
        return;
    }
    els.suggestList.hidden = false;
    els.suggestList.innerHTML = data.suggestions
        .map((title, i) => `<button type="button" data-i="${i}">${escapeHtml(title)}</button>`)
        .join("");
}

async function performSearch() {
    const query = els.query.value.trim();
    state.query = query;
    hideSuggestions();
    if (!query) {
        showStatus("Enter a search term.");
        return;
    }

    els.emptyState.hidden = true;
    els.resultsWrap.hidden = false;
    els.resultsList.innerHTML = "";
    showStatus("Ranking documents with BM25…", "loading");

    const res = await fetch("/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            query,
            page: state.page,
            page_size: state.pageSize,
            publication: state.publication,
            year: state.year,
        }),
    });
    const data = await res.json();
    if (!res.ok) {
        showStatus(escapeHtml(data.error || "Search failed."), "error");
        return;
    }

    state.total = data.stats.total_results;
    state.terms = data.query_terms || [];
    const pages = Math.max(1, Math.ceil(state.total / state.pageSize));
    els.statsLine.textContent = state.total
        ? `${formatNumber(state.total)} ranked hits in ${data.stats.time_ms} ms · ${data.stats.ranker}`
        : `No ranked hits · ${data.stats.time_ms} ms`;
    els.pageLabel.textContent = `Page ${state.page} / ${pages}`;
    els.prevPage.disabled = state.page <= 1;
    els.nextPage.disabled = state.page >= pages;
    els.statusBox.innerHTML = "";

    if (!data.results.length) {
        showStatus(`No documents matched “${escapeHtml(query)}”. Try fewer filters or a broader query.`);
        return;
    }

    els.resultsList.innerHTML = data.results.map((item, index) => `
        <li>
            <article class="result" data-id="${item.doc_id}" tabindex="0">
                <div class="result-top">
                    <span>${escapeHtml(item.publication || "Unknown publication")} · ${escapeHtml(item.date || "n.d.")}${item.author ? ` · ${escapeHtml(item.author)}` : ""}</span>
                    <span>#${(state.page - 1) * state.pageSize + index + 1}</span>
                </div>
                <h3>${highlight(item.title, state.terms)}</h3>
                <p>${highlight(item.snippet, state.terms)}</p>
                <div class="relevance">
                    <div class="bar" aria-hidden="true"><span style="width:${Math.max(8, item.relevance * 100)}%"></span></div>
                    <span>BM25 ${item.score.toFixed(3)}</span>
                </div>
            </article>
        </li>
    `).join("");
}

async function openDocument(docId) {
    els.reader.hidden = false;
    els.backdrop.hidden = false;
    els.readerTitle.textContent = "Loading…";
    els.readerMeta.textContent = "";
    els.readerBody.textContent = "";
    const res = await fetch(`/api/document/${docId}`);
    const doc = await res.json();
    if (!res.ok) {
        els.readerTitle.textContent = "Unavailable";
        els.readerBody.textContent = doc.error || "Could not load this article.";
        return;
    }
    els.readerTitle.innerHTML = highlight(doc.title, state.terms);
    els.readerMeta.textContent = [doc.publication, doc.date, doc.author].filter(Boolean).join(" · ");
    els.readerBody.innerHTML = highlight(doc.content, state.terms);
}

function closeReader() {
    els.reader.hidden = true;
    els.backdrop.hidden = true;
}

els.form.addEventListener("submit", (event) => {
    event.preventDefault();
    state.page = 1;
    performSearch();
});

els.query.addEventListener("input", () => {
    fetchSuggestions(els.query.value.trim());
});

els.suggestList.addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button) return;
    els.query.value = button.textContent;
    hideSuggestions();
    state.page = 1;
    performSearch();
});

document.getElementById("featuredQueries").addEventListener("click", (event) => {
    const chip = event.target.closest("[data-q]");
    if (!chip) return;
    els.query.value = chip.dataset.q;
    state.page = 1;
    performSearch();
});

els.publication.addEventListener("change", () => {
    state.publication = els.publication.value;
    state.page = 1;
    if (state.query) performSearch();
});

els.year.addEventListener("change", () => {
    state.year = els.year.value;
    state.page = 1;
    if (state.query) performSearch();
});

els.clearFilters.addEventListener("click", () => {
    els.publication.value = "all";
    els.year.value = "all";
    state.publication = "all";
    state.year = "all";
    if (state.query) {
        state.page = 1;
        performSearch();
    }
});

els.prevPage.addEventListener("click", () => {
    if (state.page > 1) {
        state.page -= 1;
        performSearch();
    }
});

els.nextPage.addEventListener("click", () => {
    state.page += 1;
    performSearch();
});

els.resultsList.addEventListener("click", (event) => {
    const card = event.target.closest(".result");
    if (card) openDocument(card.dataset.id);
});

els.resultsList.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
        const card = event.target.closest(".result");
        if (card) openDocument(card.dataset.id);
    }
});

els.closeReader.addEventListener("click", closeReader);
els.backdrop.addEventListener("click", closeReader);

document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
        closeReader();
        hideSuggestions();
    }
    if (event.key === "/" && document.activeElement !== els.query) {
        event.preventDefault();
        els.query.focus();
    }
});

loadMeta().catch(() => {
    document.getElementById("statDocs").textContent = "offline";
});
