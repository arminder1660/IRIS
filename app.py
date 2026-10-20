from flask import Flask, jsonify, render_template, request

from ir_engine import ENGINE, search_documents

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/meta")
def meta():
    return jsonify(ENGINE.stats())


@app.route("/api/suggest")
def suggest():
    query = request.args.get("q", "").strip()
    return jsonify({"suggestions": ENGINE.suggest(query)})


@app.route("/search", methods=["POST"])
@app.route("/api/search", methods=["POST"])
def search():
    payload = request.get_json(silent=True) or {}
    query = str(payload.get("query", "")).strip()
    if not query:
        return jsonify({"error": "Enter a search query."}), 400

    page = payload.get("page", 1)
    top_k = payload.get("top_k") or payload.get("page_size") or 10
    publication = payload.get("publication") or None
    year = payload.get("year") or None
    try:
        year = int(year) if year not in (None, "", "all") else None
    except (TypeError, ValueError):
        year = None

    result = search_documents(
        query,
        top_k=int(top_k),
        page=int(page or 1),
        publication=publication if publication and publication != "all" else None,
        year=year,
    )
    stats = ENGINE.stats()
    return jsonify(
        {
            "results": result["results"],
            "stats": {
                "time": round(result["time_ms"] / 1000, 3),
                "time_ms": result["time_ms"],
                "total_results": result["total_hits"],
                "page": result["page"],
                "page_size": result["page_size"],
                "indexed_docs": stats["indexed_docs"],
                "ranker": stats["ranker"],
            },
            "query_terms": result["query_terms"],
        }
    )


@app.route("/api/document/<int:doc_id>")
def document(doc_id: int):
    doc = ENGINE.get_document(doc_id)
    if not doc:
        return jsonify({"error": "Document not found."}), 404
    return jsonify(doc)


if __name__ == "__main__":
    app.run(debug=True, threaded=True)
