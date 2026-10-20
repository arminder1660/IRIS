# IRIS — Information Retrieval Index

IRIS is a Flask-based news article search application. It indexes a local CSV corpus and ranks results with Okapi BM25. The web interface includes query suggestions, publication and year filters, pagination, relevance scores, and an on-demand article reader.

> The repository intentionally does not include the article corpus or generated search indexes. Article text may be copyrighted, and the dataset and indexes are too large for ordinary GitHub hosting. Use only a corpus you are authorized to store and process.

## Features

- BM25 lexical retrieval with title, publication, and author boosting
- Query-focused result snippets and highlighted search terms
- Publication and year facets
- Query suggestions based on article titles
- Paginated results and on-demand full-article retrieval
- Disk caching of the built index
- Built-in sample documents when no local corpus is present

## Requirements

- Python 3.10 or newer
- The dependencies listed in `requirements.txt`
- Optional: a compatible local CSV corpus (not included)

## Run locally

From the repository root, create and activate a virtual environment, then install dependencies:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Start the development server:

```powershell
python app.py
```

Open <http://127.0.0.1:5000>. If `data/articles1.csv` is absent, IRIS starts with four sample documents. The first run with a real corpus builds and caches the index under `data/`; subsequent starts reuse it while the CSV remains unchanged.

For a local corpus, place an authorized CSV at `data/articles1.csv`. The indexer recognizes `id`, `title`, `publication`, `author`, `date`, `year`, and `content` columns (column names are normalized to lowercase). Rows need a non-empty `title` or `content`. Keep local datasets and generated cache files out of version control.

## API

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/meta` | Corpus/index statistics and available publication/year filters |
| `GET` | `/api/suggest?q=<text>` | Matching title suggestions |
| `POST` | `/api/search` | Search the corpus; `/search` is an alias |
| `GET` | `/api/document/<doc_id>` | Fetch a full indexed document |

Example search request:

```json
{
  "query": "health care",
  "page": 1,
  "page_size": 8,
  "publication": "all",
  "year": "all"
}
```

Search requests require a non-empty `query`. Pagination and filters are optional. A successful response includes `results`, timing and pagination statistics, and the parsed `query_terms`.

## Project layout

```text
app.py                 Flask routes and JSON API
ir_engine.py           CSV loading, BM25 indexing, search, and snippets
requirements.txt       Python dependencies
static/                 Browser JavaScript and CSS
templates/index.html   Search interface
data/                   Local corpus and generated index cache (not committed)
```

## Production note

The Flask development server is for local use. A basic WSGI launch command is:

```powershell
gunicorn --workers 1 --threads 4 app:app
```

Loading a large corpus requires significant memory; size deployment resources for the corpus and index. The application currently loads the index into memory when its process starts.
