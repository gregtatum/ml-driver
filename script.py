"""Convenience script that chains the built-in demo flows."""

from __future__ import annotations

from firefox_inference import FirefoxInference


def run_summarization_demo(firefox: FirefoxInference) -> str:
  url = "https://en.wikipedia.org/wiki/Money_(Pink_Floyd_song)"
  page_text = firefox.get_reader_mode_content(url)
  if not page_text:
    page_text = firefox.get_page_text(url)
  if not page_text:
    raise RuntimeError("Unable to find page text for that url")

  engine = firefox.create_ml_engine(
    {
      "taskName": "summarization",
      "modelId": "mozilla/text_summarization",
      "modelRevision": "main",
    }
  )
  engine_id = engine["engineId"]
  try:
    inference = firefox.run_ml_engine(
      engine_id, args=[page_text], options={"max_new_tokens": 1000}
    )
    return inference["entries"][0]["summary_text"]
  finally:
    firefox.destroy_ml_engine(engine_id)


def run_translation_demo(firefox: FirefoxInference) -> str:
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
    translation = firefox.run_translations_session(session_id, text=spanish_excerpt)
    return translation["targetText"]
  finally:
    firefox.destroy_translations_session(session_id)


def main() -> None:
  firefox = FirefoxInference(headless=True, log_firefox=False)
  try:
    print("Summarized text:", run_summarization_demo(firefox))
    print("Translated excerpt:", run_translation_demo(firefox))
  finally:
    firefox.quit()


if __name__ == "__main__":
  main()
