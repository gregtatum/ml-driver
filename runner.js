const { PageExtractorParent } = ChromeUtils.importESModule(
  "resource://gre/actors/PageExtractorParent.sys.mjs"
);
const { createEngine } = ChromeUtils.importESModule(
  "chrome://global/content/ml/EngineProcess.sys.mjs"
);
const { MLEngine } = ChromeUtils.importESModule(
  "resource://gre/actors/MLEngineParent.sys.mjs"
);

async function createMlEngine(options = {}) {
  const engine = await createEngine(options);
  return {
    engineId: engine.engineId,
    status: engine.engineStatus,
  };
}

async function runMlEngine(engineId, request = {}) {
  const engine = getExistingEngine(engineId);
  const response = await engine.run(request);
  return serializeInferenceResponse(response);
}

async function destroyMlEngine(engineId, { shutdown = true } = {}) {
  const engine = getExistingEngine(engineId);
  await engine.terminate(shutdown, false);
  return { engineId, status: engine.engineStatus };
}

function getExistingEngine(engineId) {
  if (!engineId) {
    throw new Error("engineId is required");
  }

  const engine = MLEngine.getInstance(engineId);
  if (!engine) {
    throw new Error(`Engine ${engineId} not found`);
  }
  return engine;
}

/**
 * Use the PageExtractor in a hidden browser to avoid disturbing the visible tab.
 *
 * @param {string} url
 * @param {Record<string, any>} options
 */
async function runHeadlessExtractor(url, options) {
  if (!url) {
    throw new Error("A URL is required to run the headless extractor");
  }

  return PageExtractorParent.getHeadlessExtractor(url, (actor) =>
    actor.getText(options)
  );
}

function serializeInferenceResponse(response) {
  if (!response || typeof response !== "object") {
    return response;
  }

  const entries = Array.isArray(response)
    ? response.map((entry) => serializeEntry(entry))
    : serializeEntry(response);

  return {
    entries,
    metrics: response.metrics ?? null,
  };
}

function serializeEntry(entry) {
  if (!entry || typeof entry !== "object") {
    return entry;
  }

  const serialized = { ...entry };
  if (entry.data instanceof ArrayBuffer) {
    serialized.data = Array.from(new Uint8Array(entry.data));
  }
  return serialized;
}

/**
 * @returns {PageExtractorParent}
 */
function getPageExtractor() {
  const actor =
    gBrowser.selectedBrowser.browsingContext.currentWindowGlobal.getActor(
      "PageExtractor"
    );

  if (!actor) {
    throw new Error(
      "PageExtractor actor is not available for the selected tab"
    );
  }

  return actor;
}

async function handleMessage(name, ...args) {
  switch (name) {
    case "create_ml_engine": {
      const [options] = args;
      return createMlEngine(options);
    }
    case "run_ml_engine": {
      const [engineId, request] = args;
      return runMlEngine(engineId, request);
    }
    case "destroy_ml_engine": {
      const [engineId, options] = args;
      return destroyMlEngine(engineId, options);
    }
    case "get_page_text": {
      const [options] = args;
      return getPageExtractor().getText(options ?? {});
    }
    case "get_reader_mode_content": {
      const [force] = args;
      return getPageExtractor().getReaderModeContent(Boolean(force));
    }
    case "get_page_info": {
      const [options] = args;
      return getPageExtractor().getPageInfo(options ?? {});
    }
    case "get_selection_text": {
      const [options] = args;
      return getPageExtractor().getSelectionText(options ?? {});
    }
    case "get_headless_page_text": {
      const [url, options] = args;
      return runHeadlessExtractor(url, options ?? {});
    }
    default:
      throw new Error(`Unknown message: ${name}`);
  }
}

async function run(done, args) {
  try {
    done({ name: "success", result: await handleMessage(...args) });
  } catch (error) {
    done({ name: "error", error: serializeError(error) });
  }
}

/**
 * @param {unknown} error
 * @returns {{ message?: string; name?: string; stack?: string }}
 */
function serializeError(error) {
  if (error && typeof error === "object") {
    const { message, name, stack } = /** @type {Error} */ (error);
    return { message, name, stack };
  }
  return { message: String(error) };
}

// The last argument is the "done" callback. Split those up after initialization.
run(
  arguments[arguments.length - 1],
  [...arguments].slice(0, arguments.length - 1)
);
