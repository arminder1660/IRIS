# Contributing

Thanks for helping improve IRIS.

## Before you start

- Keep changes focused and explain the user-visible or technical reason for them.
- Do not commit article data, generated indexes, credentials, or local environment files.
- Confirm you have permission before adding any dataset or sample article content.
- Avoid adding dependencies unless they are necessary.

## Local development

1. Create and activate a Python 3.10+ virtual environment. See the setup commands in the [README](README.md#run-locally).
2. Install dependencies with `python -m pip install -r requirements.txt`.
3. Run the application with `python app.py` and try it at <http://127.0.0.1:5000>.
4. If changing search behavior, try queries against the built-in sample corpus and, where authorized, a representative local dataset.

## Submitting a change

- Keep formatting consistent with the existing Python, JavaScript, HTML, and CSS.
- Update the README or API documentation when behavior, setup, or endpoints change.
- Run `python -m py_compile app.py ir_engine.py` after Python changes.
- Describe what changed, how you checked it, and any known limitations in your pull request.

There is currently no automated test suite configured in this repository. Do not report an unrun test suite as passing.
