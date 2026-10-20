"""In-memory BM25 search index for the news corpus.

The previous implementation re-read and re-preprocessed the entire CSV on
every query, computed dense cosine similarity against all documents, then
returned full article bodies. This module loads the corpus once, caches the
index on disk, and ranks with sparse BM25 + argpartition.
"""

from __future__ import annotations

import os
import re
import time
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer

DATA_CSV = os.path.join("data", "articles1.csv")
INDEX_CACHE = os.path.join("data", "bm25_index.joblib")
INDEX_VERSION = 2

TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9]{1,}")


def _tokenize_terms(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower()) if text else []


class BM25Index:
    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.vectorizer: CountVectorizer | None = None
        self.tf = None
        self.idf: np.ndarray | None = None
        self.doc_len: np.ndarray | None = None
        self.avgdl: float = 0.0
        self.docs: list[dict[str, Any]] = []
        self.publications: list[str] = []
        self.years: list[int] = []
        self.pub_arr = np.array([], dtype=object)
        self.year_arr = np.array([], dtype=np.int32)
        self.ready = False
        self.build_seconds: float = 0.0

    def _search_text(self, row: dict[str, Any]) -> str:
        title = row.get("title") or ""
        content = row.get("content") or ""
        publication = row.get("publication") or ""
        author = row.get("author") or ""
        # Title/publication repeated so lexical matches in those fields rank higher.
        return f"{title} {title} {title} {publication} {author} {content}"

    def build_from_csv(self, path: str) -> None:
        started = time.perf_counter()
        df = pd.read_csv(
            path,
            usecols=lambda c: c.lower() in {
                "id", "title", "publication", "author", "date", "year", "content"
            } or c == "id",
            low_memory=False,
        )
        df.columns = [str(c).strip().lower() for c in df.columns]
        for col in ("title", "publication", "author", "date", "content"):
            if col not in df.columns:
                df[col] = ""
            df[col] = df[col].fillna("").astype(str)
        if "year" not in df.columns:
            df["year"] = 0
        else:
            df["year"] = pd.to_numeric(df["year"], errors="coerce").fillna(0).astype(int)
        if "id" not in df.columns:
            df["id"] = np.arange(len(df))

        df = df[df["content"].str.strip().astype(bool) | df["title"].str.strip().astype(bool)]
        df = df.reset_index(drop=True)

        self.docs = [
            {
                "doc_id": int(i),
                "source_id": str(row["id"]),
                "title": row["title"].strip() or f"Untitled article {i + 1}",
                "publication": row["publication"].strip(),
                "author": row["author"].strip(),
                "date": row["date"].strip()[:10],
                "year": int(row["year"]) if row["year"] else None,
                "content": row["content"],
            }
            for i, row in enumerate(df.to_dict("records"))
        ]
        self._fit_bm25([self._search_text(d) for d in self.docs])
        self._refresh_facets()
        self._refresh_arrays()
        self.ready = True
        self.build_seconds = round(time.perf_counter() - started, 2)

    def build_from_sample(self) -> None:
        started = time.perf_counter()
        samples = [
            {
                "doc_id": 0,
                "source_id": "1",
                "title": "Artificial intelligence is transforming industry",
                "publication": "Sample Press",
                "author": "IR Lab",
                "date": "2024-01-01",
                "year": 2024,
                "content": "Artificial intelligence is transforming industries by automating complex tasks.",
            },
            {
                "doc_id": 1,
                "source_id": "2",
                "title": "Machine learning needs large datasets",
                "publication": "Sample Press",
                "author": "IR Lab",
                "date": "2024-01-02",
                "year": 2024,
                "content": "Machine learning algorithms require large datasets to achieve high accuracy.",
            },
            {
                "doc_id": 2,
                "source_id": "3",
                "title": "Information retrieval finds relevant documents",
                "publication": "Sample Press",
                "author": "IR Lab",
                "date": "2024-01-03",
                "year": 2024,
                "content": "This information retrieval system helps users find relevant documents quickly.",
            },
            {
                "doc_id": 3,
                "source_id": "4",
                "title": "Python Flask for web applications",
                "publication": "Sample Press",
                "author": "IR Lab",
                "date": "2024-01-04",
                "year": 2024,
                "content": "Python Flask is a lightweight framework for building web applications.",
            },
        ]
        self.docs = samples
        self._fit_bm25([self._search_text(d) for d in self.docs])
        self._refresh_facets()
        self._refresh_arrays()
        self.ready = True
        self.build_seconds = round(time.perf_counter() - started, 2)

    def _fit_bm25(self, corpus: list[str]) -> None:
        self.vectorizer = CountVectorizer(
            lowercase=True,
            stop_words="english",
            max_features=35000,
            ngram_range=(1, 1),
            min_df=2 if len(corpus) > 50 else 1,
            max_df=0.85 if len(corpus) > 50 else 1.0,
            token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z0-9]{1,}\b",
        )
        self.tf = self.vectorizer.fit_transform(corpus)
        n_docs = self.tf.shape[0]
        df = np.asarray((self.tf > 0).sum(axis=0)).ravel().astype(np.float32)
        self.idf = np.log((n_docs - df + 0.5) / (df + 0.5) + 1.0).astype(np.float32)
        self.doc_len = np.asarray(self.tf.sum(axis=1)).ravel().astype(np.float32)
        self.avgdl = float(self.doc_len.mean()) if n_docs else 1.0

    def _refresh_facets(self) -> None:
        pubs = sorted({d["publication"] for d in self.docs if d["publication"]})
        years = sorted({d["year"] for d in self.docs if d["year"]}, reverse=True)
        self.publications = pubs
        self.years = years

    def _refresh_arrays(self) -> None:
        self.pub_arr = np.array([d["publication"].lower() for d in self.docs], dtype=object)
        self.year_arr = np.array([d["year"] or 0 for d in self.docs], dtype=np.int32)

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        joblib.dump(
            {
                "version": INDEX_VERSION,
                "k1": self.k1,
                "b": self.b,
                "vectorizer": self.vectorizer,
                "tf": self.tf,
                "idf": self.idf,
                "doc_len": self.doc_len,
                "avgdl": self.avgdl,
                "docs": self.docs,
                "publications": self.publications,
                "years": self.years,
                "build_seconds": self.build_seconds,
            },
            path,
            compress=3,
        )

    def load(self, path: str) -> None:
        payload = joblib.load(path)
        if payload.get("version") != INDEX_VERSION:
            raise ValueError("Stale index cache")
        self.k1 = payload["k1"]
        self.b = payload["b"]
        self.vectorizer = payload["vectorizer"]
        self.tf = payload["tf"]
        self.idf = payload["idf"]
        self.doc_len = payload["doc_len"]
        self.avgdl = payload["avgdl"]
        self.docs = payload["docs"]
        self.publications = payload["publications"]
        self.years = payload["years"]
        self.build_seconds = payload.get("build_seconds", 0)
        self._refresh_arrays()
        self.ready = True

    def stats(self) -> dict[str, Any]:
        return {
            "indexed_docs": len(self.docs),
            "vocabulary": int(len(self.vectorizer.vocabulary_)) if self.vectorizer else 0,
            "publications": self.publications,
            "years": self.years,
            "build_seconds": self.build_seconds,
            "ranker": "Okapi BM25",
        }

    def get_document(self, doc_id: int) -> dict[str, Any] | None:
        if doc_id < 0 or doc_id >= len(self.docs):
            return None
        doc = self.docs[doc_id]
        return {
            "doc_id": doc["doc_id"],
            "title": doc["title"],
            "publication": doc["publication"],
            "author": doc["author"],
            "date": doc["date"],
            "year": doc["year"],
            "content": doc["content"],
        }

    def suggest(self, query: str, limit: int = 6) -> list[str]:
        q = (query or "").strip().lower()
        if len(q) < 2:
            return []
        seen: set[str] = set()
        hits: list[str] = []
        for doc in self.docs:
            title = doc["title"]
            low = title.lower()
            if q in low and low not in seen:
                seen.add(low)
                hits.append(title)
                if len(hits) >= limit:
                    break
        return hits

    def search(
        self,
        query: str,
        top_k: int = 10,
        page: int = 1,
        publication: str | None = None,
        year: int | None = None,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        query = (query or "").strip()
        page = max(1, int(page or 1))
        top_k = max(1, min(int(top_k or 10), 50))

        empty = {
            "results": [],
            "total_hits": 0,
            "page": page,
            "page_size": top_k,
            "time_ms": 0,
            "query_terms": [],
        }
        if not query or self.tf is None or self.vectorizer is None:
            empty["time_ms"] = round((time.perf_counter() - started) * 1000, 2)
            return empty

        q_vec = self.vectorizer.transform([query])
        term_indices = q_vec.indices
        query_terms = _tokenize_terms(query)
        if term_indices.size == 0:
            empty["query_terms"] = query_terms
            empty["time_ms"] = round((time.perf_counter() - started) * 1000, 2)
            return empty

        tf_q = self.tf[:, term_indices].astype(np.float32)
        tf_arr = tf_q.toarray()
        idf_q = self.idf[term_indices]
        denom = tf_arr + self.k1 * (1.0 - self.b + self.b * (self.doc_len[:, None] / max(self.avgdl, 1.0)))
        scores = (idf_q * ((tf_arr * (self.k1 + 1.0)) / denom)).sum(axis=1)

        if publication:
            scores[self.pub_arr != publication.lower()] = -1.0
        if year:
            scores[self.year_arr != int(year)] = -1.0

        scored_mask = scores > 0
        total_hits = int(scored_mask.sum())
        if total_hits == 0:
            empty["query_terms"] = query_terms
            empty["time_ms"] = round((time.perf_counter() - started) * 1000, 2)
            return empty

        start = (page - 1) * top_k
        if start >= total_hits:
            empty["total_hits"] = total_hits
            empty["query_terms"] = query_terms
            empty["time_ms"] = round((time.perf_counter() - started) * 1000, 2)
            return empty

        take = min(start + top_k, total_hits)
        # Only the positive scores matter; argpartition over all docs is still cheap at 50k.
        candidate_count = min(take, scores.size)
        top_idx = np.argpartition(-scores, candidate_count - 1)[:candidate_count]
        top_idx = top_idx[np.argsort(-scores[top_idx])]
        page_idx = top_idx[start:take]

        max_score = float(scores[top_idx[0]]) if top_idx.size else 1.0
        results = []
        for idx in page_idx:
            doc = self.docs[int(idx)]
            score = float(scores[int(idx)])
            results.append(
                {
                    "doc_id": doc["doc_id"],
                    "title": doc["title"],
                    "publication": doc["publication"],
                    "author": doc["author"],
                    "date": doc["date"],
                    "year": doc["year"],
                    "snippet": _make_snippet(doc["content"], query_terms, doc["title"]),
                    "score": round(score, 4),
                    "relevance": round(score / max_score, 3) if max_score else 0,
                }
            )

        return {
            "results": results,
            "total_hits": total_hits,
            "page": page,
            "page_size": top_k,
            "time_ms": round((time.perf_counter() - started) * 1000, 2),
            "query_terms": query_terms,
        }


def _make_snippet(content: str, terms: list[str], title: str, width: int = 240) -> str:
    text = re.sub(r"\s+", " ", content or "").strip()
    if not text:
        return (title or "")[:width]
    if not terms:
        return text[:width] + ("…" if len(text) > width else "")

    lower = text.lower()
    hit_at = -1
    for term in terms:
        pos = lower.find(term.lower())
        if pos != -1 and (hit_at == -1 or pos < hit_at):
            hit_at = pos
    if hit_at == -1:
        return text[:width] + ("…" if len(text) > width else "")

    start = max(0, hit_at - 80)
    end = min(len(text), start + width)
    snippet = text[start:end].strip()
    if start > 0:
        snippet = "…" + snippet
    if end < len(text):
        snippet += "…"
    return snippet


def _csv_mtime(path: str) -> float:
    return os.path.getmtime(path) if os.path.exists(path) else 0.0


def load_index() -> BM25Index:
    index = BM25Index()
    csv_mtime = _csv_mtime(DATA_CSV)
    if os.path.exists(INDEX_CACHE):
        try:
            index.load(INDEX_CACHE)
            stamp_path = INDEX_CACHE + ".mtime"
            cached_mtime = float(open(stamp_path, encoding="utf-8").read()) if os.path.exists(stamp_path) else None
            if cached_mtime == csv_mtime and index.ready:
                return index
        except Exception:
            index = BM25Index()

    if os.path.exists(DATA_CSV):
        index.build_from_csv(DATA_CSV)
    else:
        print("Warning: data/articles1.csv not found. Using sample documents.")
        index.build_from_sample()

    try:
        index.save(INDEX_CACHE)
        with open(INDEX_CACHE + ".mtime", "w", encoding="utf-8") as handle:
            handle.write(str(csv_mtime))
    except Exception as exc:
        print(f"Could not cache index: {exc}")
    return index


ENGINE = load_index()


def search_documents(
    query: str,
    top_k: int = 10,
    page: int = 1,
    publication: str | None = None,
    year: int | None = None,
) -> dict[str, Any]:
    return ENGINE.search(
        query,
        top_k=top_k,
        page=page,
        publication=publication or None,
        year=year,
    )
