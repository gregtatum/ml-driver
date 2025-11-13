"""Translate an article excerpt using Firefox Translations."""

from __future__ import annotations

from firefox_inference import FirefoxInference


def main() -> None:
    firefox = FirefoxInference(headless=True, log_firefox=False)
    try:
        url = "https://gregtatum.com/writing/2021/encoding-text-utf-32-utf-16-unicode/"
        text = firefox.get_reader_mode_content(url)
        if not text:
            text = firefox.get_page_text(url)
        if not text:
            raise RuntimeError("Unable to find page text for that url")

        session = firefox.create_translations_session(
            {"sourceLanguage": "en", "targetLanguage": "es"}
        )
        session_id = session["sessionId"]
        try:
            translation = firefox.run_translations_session(session_id, text=text[:500])
            print("Translated excerpt:", translation["targetText"])
        finally:
            firefox.destroy_translations_session(session_id)
    finally:
        firefox.quit()


if __name__ == "__main__":
    main()
