## Firefox Inference Playground

This repo wires a local Firefox build to a Selenium-controlled harness so we can:

- Run privileged `PageExtractor` APIs (reader mode, headless extraction, pagination info, etc.).
- Spin up Firefox’s ML pipelines (`createEngine`/`run`) from Python and exercise inference tasks.

All of the orchestration happens in `script.py`, which loads `runner.js` into the chrome context and forwards commands to Firefox window actors.

### Prerequisites

- Python 3.13

### Setup

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Running the demo script

```bash
python script.py
```

What it does:

1. Launches Firefox headlessly with the necessary ML prefs enabled.
2. Uses `PageExtractor` to load a sample URL and pull out reader-mode content.
3. Calls `create_ml_engine` with a `test-echo` pipeline, runs one inference (`run_ml_engine`), prints the response, and tears the engine down.

### Using the helpers in your own code

Instantiate `FirefoxInference` (optionally overriding `ml_prefs` or the Firefox binary), then call any of:

- `get_page_text`, `get_reader_mode_content`, `get_page_info`, `get_selection_text`, `get_headless_page_text`
- `create_ml_engine`, `run_ml_engine`, `destroy_ml_engine`

Each helper returns a Python dict mirroring the structured data returned from Firefox’s JS actors, so you can compose new workflows or plug in real ML models/tasks.
