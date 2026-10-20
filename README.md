# IRIS — Information Retrieval Index

IRIS is a small full-stack news search application. A Flask API serves a browser interface, and a local CSV corpus is indexed and ranked using Okapi BM25.

Search for articles by title and text, narrow results by publication or year, browse query-focused snippets, and open full articles on demand.

## Contents

- [Features](#features)
- [How search works](#how-search-works)
- [Requirements](#requirements)
- [Run locally](#run-locally)
- [Use your own corpus](#use-your-own-corpus)
- [HTTP API](#http-api)
- [Project structure](#project-structure)
- [Troubleshooting](#troubleshooting)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [Data, copyright, and license](#data-copyright-and-license)

## Features

- Okapi BM25 lexical search, with extra weight for article titles, publication names, and authors.
- Query-aware snippets, relevance scores, and highlighted query terms.
- Exact publication and year filters, plus paginated results.
- Title-based query suggestions.
- Full article reader that fetches article text only when opened.
- On-disk index cache to avoid rebuilding an unchanged corpus at startup.
- Four built-in sample documents when no local CSV corpus is available.

## How search works

At startup, IRIS loads the local CSV, creates a sparse term-frequency matrix, and computes BM25 inverse document frequencies. It uses `k1 = 1.5` and `b = 0.75`. Title text is repeated in the indexed text to increase its influence; publication and author text are included too. The vectorizer uses English stop words and a vocabulary limit of 35,000 terms.

This is lexical retrieval, not semantic search: matching terms affect ranking, so a query and a relevant article that use different vocabulary may not match. Results are ranked in memory. The compressed joblib index and its CSV modification-time marker are written under `data/`.

## Requirements

- Python 3.10 or newer.
- Dependencies from [`requirements.txt`](requirements.txt).
- Optional: a CSV corpus that you have permission to use.

## Run locally

Run these commands from the repository root.

### Windows PowerShell

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python app.py
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python app.py
```

Open <http://127.0.0.1:5000>. Without `data/articles1.csv`, the app indexes its four sample articles. The first run with a corpus builds the index; later starts can load the cache if the CSV has not changed.

The built-in Flask server is for development. See [Deployment](#deployment) before exposing the app to users.

## Use your own corpus

1. Obtain a dataset you are authorized to store, index, and serve.
2. Create the `data` directory if it does not exist.
3. Put the CSV at `data/articles1.csv`.
4. Start the app. IRIS will build its index automatically.

The corpus and generated cache are ignored by Git. They are intentionally not distributed with this source repository: article text may be copyrighted, and the original dataset's redistribution terms are not established.

Column names are normalized to lowercase. The indexer uses these columns:

| Column | Required | Description |
| --- | --- | --- |
| `title` | No* | Article title |
| `content` | No* | Article body |
| `id` | No | Source identifier; an ID is generated when omitted |
| `publication` | No | Publication name |
| `author` | No | Author name |
| `date` | No | Date string; the first 10 characters are retained |
| `year` | No | Numeric year used by the year filter |

*Each indexed row needs a non-empty `title` or `content`. Missing optional fields are treated as empty. If `year` is absent or cannot be parsed, it is treated as unknown and will not appear as a year filter.

Example CSV header:

```csv
id,title,publication,author,date,year,content
```

To rebuild after replacing a corpus but preserving its modification time, delete the generated `data/bm25_index.joblib` and `data/bm25_index.joblib.mtime` before restarting. Do not load joblib index files from untrusted sources.

## HTTP API

The API is documented with request and response examples in [`docs/API.md`](docs/API.md).

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/meta` | Index statistics and available filters |
| `GET` | `/api/suggest?q=<text>` | Suggest matching article titles |
| `POST` | `/api/search` | Search the index |
| `POST` | `/search` | Alias for `/api/search` |
| `GET` | `/api/document/<doc_id>` | Retrieve one full indexed article |

## Project structure

```text
.
├── app.py                 Flask app and HTTP routes
├── ir_engine.py           CSV loading, index building, BM25 search
├── requirements.txt       Python dependencies
├── docs/
│   └── API.md              API request and response reference
├── static/
│   ├── css/style.css       Application styles
│   └── js/script.js        Browser interactions and API calls
├── templates/
│   └── index.html          Search page
└── data/                   Local corpus and generated index (not committed)
```

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| The app starts with only four documents | Confirm the corpus is named `data/articles1.csv` relative to the repository root. |
| Startup takes a long time | The first run builds the index. Later starts should reuse the cache if the CSV is unchanged. |
| A corpus replacement appears not to take effect | Delete `data/bm25_index.joblib` and `data/bm25_index.joblib.mtime`, then restart. |
| No search results appear | Try a broader query, check spelling, and confirm that the corpus contains matching words. Search is lexical, not semantic. |
| A publication or year filter has no effect | Use a publication/year present in `/api/meta`; publication matching is case-insensitive and exact. |
| Dependency installation fails | Use Python 3.10+ and install from the repository root with `python -m pip install -r requirements.txt`. |

## Deployment

Do not use `app.run()`'s development server for production. The project includes Gunicorn in `requirements.txt`; on a supported environment, start a WSGI server with:

```bash
gunicorn --workers 1 --threads 4 app:app
```

The corpus and index are loaded into each application process. A large corpus can require substantial memory and slow cold starts; size the host accordingly and account for per-worker memory usage. This project does not include a container image, deployment manifest, authentication, or production traffic controls.

## Contributing

Contributions are welcome. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the local development and change-submission checklist.

## Data, copyright, and license

The repository does not include a news corpus or generated index. You are responsible for confirming the rights and terms for any corpus you use, including whether you may store, index, and serve article text.

No software license has been selected for this repository. Unless a license is added by the project owner, do not assume that the source is licensed for reuse, redistribution, or modification.
