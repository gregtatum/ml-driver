"""Translate an article excerpt using Firefox Translations."""

from __future__ import annotations

from firefox_inference import FirefoxInference


def main() -> None:
  firefox = FirefoxInference(headless=True, log_firefox=False)
  try:
    es_url = "https://es.wikipedia.org/wiki/Money_(canci%C3%B3n_de_Pink_Floyd)"
    spanish_content = firefox.get_reader_mode_content(es_url, force=True)
    if not spanish_content:
      raise RuntimeError("Unable to fetch Spanish article content")
    spanish_excerpt = spanish_content[:500]

    session = firefox.create_translations_session(
      {"sourceLanguage": "es", "targetLanguage": "en"}
    )
    session_id = session["sessionId"]
    try:
      translation = firefox.run_translations_session(
        session_id, text=spanish_excerpt
      )
      print("Translated excerpt:", translation["targetText"])
    finally:
      firefox.destroy_translations_session(session_id)
  finally:
    firefox.quit()


if __name__ == "__main__":
  main()
