"""Simple interactive CLI for Firefox-powered translations."""

from __future__ import annotations

import argparse

from firefox_inference import FirefoxInference


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    description=(
      "Translate text interactively using Firefox's local translations engine."
    )
  )
  parser.add_argument(
    "--source-language",
    default="en",
    help="BCP-47 language tag for the input text (default: en)",
  )
  parser.add_argument(
    "--target-language",
    default="es",
    help="BCP-47 language tag for the translated output (default: es)",
  )
  parser.add_argument(
    "--show-browser",
    action="store_true",
    help="Launch Firefox with a visible window instead of headless mode.",
  )
  return parser.parse_args()


def main() -> None:
  args = parse_args()
  firefox = FirefoxInference(headless=not args.show_browser, log_firefox=False)
  session_id = None

  try:
    session = firefox.create_translations_session(
      {
        "sourceLanguage": args.source_language,
        "targetLanguage": args.target_language,
      }
    )
    session_id = session["sessionId"]

    print(
      "Type text to translate (blank line, EOF, or 'exit'/'quit' to stop).\n"
      f"Translating {args.source_language} → {args.target_language}."
    )

    while True:
      try:
        raw = input("> ")
      except EOFError:
        print()
        break

      text = raw.strip()
      if not text or text.lower() in {"exit", "quit"}:
        break

      try:
        result = firefox.run_translations_session(session_id, text=text)
      except Exception as error:  # pragma: no cover - interactive helper
        print(f"[error] {error}")
        continue

      translated = result.get("targetText")
      print(translated or "<no translation>")
  finally:
    if session_id:
      firefox.destroy_translations_session(session_id)
    firefox.quit()


if __name__ == "__main__":
  main()
