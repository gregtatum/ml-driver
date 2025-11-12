// The last argument is the "done" callback. Split those up.
run(
  arguments[arguments.length - 1],
  [...arguments].slice(0, arguments.length - 1)
);

async function run(done, args) {
  try {
    done({ name: "success", result: await handleMessage(...args) });
  } catch (error) {
    done({ name: "error", error });
  }
}

function handleMessage(name, ...args) {
  switch (name) {
    case "get_page_text":
      return gBrowser.selectedBrowser.browsingContext.currentWindowGlobal
        .getActor("PageExtractor")
        .getText();
    default:
      throw new Error("Unknown message");
  }
}
