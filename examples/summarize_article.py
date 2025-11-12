"""Summarize a Wikipedia article via Firefox's ML pipeline."""

from __future__ import annotations

from firefox_inference import FirefoxInference


def main() -> None:
  firefox = FirefoxInference(headless=True, log_firefox=False)
  try:
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
      print("Summarized text:", inference["entries"][0]["summary_text"])
    finally:
      firefox.destroy_ml_engine(engine_id)
  finally:
    firefox.quit()


if __name__ == "__main__":
  main()
