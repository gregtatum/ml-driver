const { PageExtractorParent } = ChromeUtils.importESModule(
  "resource://gre/actors/PageExtractorParent.sys.mjs"
);
const { createEngine } = ChromeUtils.importESModule(
  "chrome://global/content/ml/EngineProcess.sys.mjs"
);
const { MLEngine } = ChromeUtils.importESModule(
  "resource://gre/actors/MLEngineParent.sys.mjs"
);
const { TranslationsParent } = ChromeUtils.importESModule(
  "resource://gre/actors/TranslationsParent.sys.mjs"
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

function createDeferred() {
  let settled = false;
  let resolveFn;
  let rejectFn;

  const promise = new Promise((resolve, reject) => {
    resolveFn = (value) => {
      if (!settled) {
        settled = true;
        resolve(value);
      }
    };
    rejectFn = (error) => {
      if (!settled) {
        settled = true;
        reject(error);
      }
    };
  });

  return {
    promise,
    resolve: resolveFn,
    reject: rejectFn,
    isSettled: () => settled,
  };
}

function normalizeLanguagePair(pair = {}) {
  const { sourceLanguage, targetLanguage } = pair;
  if (!sourceLanguage || !targetLanguage) {
    throw new Error(
      "Translations languagePair requires both sourceLanguage and targetLanguage"
    );
  }

  return {
    sourceLanguage: String(sourceLanguage),
    targetLanguage: String(targetLanguage),
  };
}

const translationSessions = new Map();
let nextTranslationSessionId = 1;

async function createTranslationsSession(options = {}) {
  const languagePair = normalizeLanguagePair(options.languagePair || options);
  const port = await TranslationsParent.requestTranslationsPort(languagePair);
  if (!port) {
    throw new Error("Failed to acquire a translations port from Firefox");
  }

  const sessionId = `translation-session-${nextTranslationSessionId++}`;
  const session = {
    id: sessionId,
    languagePair,
    port,
    ready: createDeferred(),
    status: "initializing",
    pendingRequests: new Map(),
    nextTranslationId: 1,
  };

  translationSessions.set(sessionId, session);
  attachPortHandlers(session);
  if (typeof port.start === "function") {
    port.start();
  }

  port.postMessage({ type: "TranslationsPort:GetEngineStatusRequest" });
  await session.ready.promise;

  return {
    sessionId,
    status: session.status,
    languagePair,
  };
}

function attachPortHandlers(session) {
  const { port } = session;

  port.onmessage = (event) => {
    const data = event.data || {};
    switch (data.type) {
      case "TranslationsPort:GetEngineStatusResponse": {
        session.status = data.status;
        if (data.status === "ready") {
          session.ready.resolve({ status: data.status });
        } else {
          const error = new Error(
            data.error || "Translations engine failed to initialize"
          );
          session.ready.reject(error);
          failTranslationsSession(session, error);
        }
        break;
      }
      case "TranslationsPort:TranslationResponse": {
        const pending = session.pendingRequests.get(data.translationId);
        if (pending) {
          session.pendingRequests.delete(data.translationId);
          pending.resolve({
            translationId: data.translationId,
            targetText: data.targetText,
          });
        }
        break;
      }
      case "TranslationsPort:EngineTerminated": {
        failTranslationsSession(
          session,
          new Error("Translations engine terminated unexpectedly")
        );
        break;
      }
      default:
        console.error("Unknown translations port message", data);
    }
  };

  port.onmessageerror = () => {
    failTranslationsSession(
      session,
      new Error("Translations port failed to deserialize a message")
    );
  };
}

function failTranslationsSession(session, error) {
  cleanupTranslationSession(session, error);
  translationSessions.delete(session.id);
}

function cleanupTranslationSession(session, error) {
  if (session.port) {
    try {
      session.port.onmessage = null;
      session.port.onmessageerror = null;
      session.port.close();
    } catch (closeError) {
      console.error("Failed to close translations port", closeError);
    }
    session.port = null;
  }

  if (error) {
    if (!session.ready.isSettled()) {
      session.ready.reject(error);
    }
    for (const pending of session.pendingRequests.values()) {
      pending.reject(error);
    }
  } else {
    for (const pending of session.pendingRequests.values()) {
      pending.reject(new Error("Translations session was destroyed"));
    }
  }
  session.pendingRequests.clear();
}

async function runTranslationsSession(sessionId, request = {}) {
  const session = translationSessions.get(sessionId);
  if (!session) {
    throw new Error(`Translations session not found: ${sessionId}`);
  }

  await session.ready.promise;

  const text =
    typeof request.text === "string"
      ? request.text
      : typeof request.sourceText === "string"
        ? request.sourceText
        : null;

  if (text === null) {
    throw new Error("Translations request missing text/sourceText field");
  }

  const translationId = session.nextTranslationId++;
  const pending = createDeferred();
  session.pendingRequests.set(translationId, pending);

  session.port.postMessage({
    type: "TranslationsPort:TranslationRequest",
    translationId,
    sourceText: text,
    isHTML: Boolean(request.isHTML || request.isHtml),
  });

  const response = await pending.promise;
  return {
    sessionId,
    translationId: response.translationId,
    targetText: response.targetText,
    languagePair: session.languagePair,
  };
}

function destroyTranslationsSession(sessionId, options = {}) {
  const session = translationSessions.get(sessionId);
  if (!session) {
    return { sessionId, destroyed: false };
  }

  if (options.discardTranslations !== false && session.port) {
    session.port.postMessage({
      type: "TranslationsPort:DiscardTranslations",
    });
  }

  cleanupTranslationSession(session);
  translationSessions.delete(sessionId);

  return {
    sessionId,
    destroyed: true,
  };
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
    case "create_translations_session": {
      const [options] = args;
      return createTranslationsSession(options ?? {});
    }
    case "run_translations_session": {
      const [sessionId, request] = args;
      return runTranslationsSession(sessionId, request ?? {});
    }
    case "destroy_translations_session": {
      const [sessionId, options] = args;
      return destroyTranslationsSession(sessionId, options ?? {});
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
