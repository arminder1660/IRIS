# IRIS HTTP API

The Flask application exposes JSON endpoints under `/api`. Unless noted otherwise, responses use `application/json`.

## `GET /api/meta`

Returns index information for the interface.

```json
{
  "indexed_docs": 4,
  "vocabulary": 44,
  "publications": ["Sample Press"],
  "years": [2024],
  "build_seconds": 0.01,
  "ranker": "Okapi BM25"
}
```

The values above illustrate the built-in sample corpus; values for a local corpus will differ.

## `GET /api/suggest?q=<text>`

Returns up to six article titles containing the query as a case-insensitive substring. Queries shorter than two characters return an empty list.

Example: `GET /api/suggest?q=python`

```json
{
  "suggestions": ["Python Flask for web applications"]
}
```

## `POST /api/search`

`POST /search` is an alias. Send a JSON object with the following fields:

| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| `query` | string | Required | Must contain non-whitespace text |
| `page` | integer | `1` | Pages are one-based |
| `page_size` | integer | `10` | `top_k` is accepted as an alias; values are clamped from 1 to 50 |
| `publication` | string | No filter | Exact publication name; `"all"` means no filter |
| `year` | integer or string | No filter | `"all"` or an empty value means no filter |

Example request:

```json
{
  "query": "health care",
  "page": 1,
  "page_size": 8,
  "publication": "all",
  "year": "all"
}
```

Example response shape:

```json
{
  "results": [
    {
      "doc_id": 0,
      "title": "Example article title",
      "publication": "Example Press",
      "author": "A. Writer",
      "date": "2024-01-01",
      "year": 2024,
      "snippet": "A short excerpt around the matching query terms…",
      "score": 2.1345,
      "relevance": 1.0
    }
  ],
  "stats": {
    "time": 0.002,
    "time_ms": 2.01,
    "total_results": 1,
    "page": 1,
    "page_size": 8,
    "indexed_docs": 4,
    "ranker": "Okapi BM25"
  },
  "query_terms": ["health", "care"]
}
```

The example scores and timings are illustrative. `total_results` is the number of matching documents, not just the number on the current page. An empty match returns an empty `results` array and zero `total_results`.

An empty query returns HTTP `400`:

```json
{
  "error": "Enter a search query."
}
```

## `GET /api/document/<doc_id>`

Returns the full indexed article for a result's integer `doc_id`.

```json
{
  "doc_id": 0,
  "title": "Example article title",
  "publication": "Example Press",
  "author": "A. Writer",
  "date": "2024-01-01",
  "year": 2024,
  "content": "Full article text..."
}
```

An unknown document ID returns HTTP `404`:

```json
{
  "error": "Document not found."
}
```
