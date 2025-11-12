// The last argument is the "done" callback. Split those up.
run(
  arguments[arguments.length - 1],
  [...arguments].slice(0, arguments.length - 1)
);

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
    case "get_page_text": {
      const [options] = args;
      return getPageExtractor().getText(options);
    }
    case "get_reader_mode_content": {
      const [force] = args;
      return getPageExtractor().getReaderModeContent(Boolean(force));
    }
    case "get_page_info": {
      const [options] = args;
      return getPageExtractor().getPageInfo(options);
    }
    case "get_selection_text": {
      const [options] = args;
      return getPageExtractor().getSelectionText(options);
    }
    case "get_headless_page_text": {
      const [url, options] = args;
      return runHeadlessExtractor(url, options);
    }
    default:
      throw new Error(`Unknown message: ${name}`);
  }
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

  const { PageExtractorParent } = ChromeUtils.importESModule(
    "resource://gre/actors/PageExtractorParent.sys.mjs"
  );

  return PageExtractorParent.getHeadlessExtractor(url, (actor) =>
    actor.getText(options)
  );
}
