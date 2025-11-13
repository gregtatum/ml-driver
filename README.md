## Firefox Inference Playground

`firefox-inference` wires a local Firefox build to a Selenium-controlled harness so you can:

> **Warning:** this is experimental demonstration code only. It will probably break in the future as it's accessing Firefox internals, and the implementation is just quick prototype code.

- Run privileged `PageExtractor` APIs (reader mode, headless extraction, pagination info, etc.).
- Spin up Firefox’s ML pipelines (`createEngine`/`run`) from Python and exercise inference tasks.

All of the orchestration lives in the `FirefoxInference` class, which loads a bundled `runner.js` into the chrome context and forwards commands to Firefox window actors.

### Installation

```bash
pip install firefox-inference
```

Running from source? Create a venv and install the local package:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Running the demo script

```bash
python script.py
```

What it does:

1. Launches Firefox headlessly with the necessary ML prefs enabled.
2. Uses `PageExtractor` to load a sample URL and pull out reader-mode content.
3. Calls `create_ml_engine` with a `test-echo` pipeline, runs one inference (`run_ml_engine`), prints the response, and tears the engine down.
4. Starts a Spanish → English translations session, translates an excerpt from the related article, and destroys the session.

### Using the helpers in your own code

Instantiate `FirefoxInference` (optionally overriding `ml_prefs` or the Firefox binary), then call any of:

- `get_page_text`, `get_reader_mode_content`, `get_page_info`, `get_selection_text`, `get_headless_page_text`
- `create_ml_engine`, `run_ml_engine`, `destroy_ml_engine`
- `create_translations_session`, `run_translations_session`, `destroy_translations_session`

Each helper returns a Python dict mirroring the structured data returned from Firefox’s JS actors, so you can compose new workflows or plug in real ML models/tasks.

### Examples

The `examples/` directory contains standalone scripts for the demo flows showcased in `script.py`—use them as starting points for new experiments.

Run them after installing the package (e.g., `pip install -e .`), or point Python at the local sources:

```bash
PYTHONPATH=src python examples/summarize_article.py
PYTHONPATH=src python examples/translate_article.py
```
