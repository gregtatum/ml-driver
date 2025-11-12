"""Firefox inference helpers exposed as a reusable module."""

from __future__ import annotations

from importlib import resources
from pathlib import Path
import subprocess
import time
from typing import Any, Dict, List, Optional

from selenium import webdriver

import logging


__all__ = ["FirefoxInference"]


logger = logging.getLogger("firefox-ml")


def _load_runner_js() -> str:
  """Return the contents of runner.js bundled with the package."""
  runner_path = resources.files(__package__).joinpath("runner.js")
  return runner_path.read_text()


class FirefoxInference:
  """High-level helper for driving Firefox ML APIs via Marionette."""

  driver: webdriver.Firefox
  runner_js: str

  def __init__(
    self,
    headless: bool = False,
    firefox_bin: Optional[Path] = None,
    log_firefox: bool = False,
    ml_prefs: Optional[Dict[str, Any]] = None,
  ) -> None:
    if not logger.handlers:
      logging.basicConfig(level=logging.INFO, format="[%(name)s] %(message)s")
    logger.setLevel(logging.INFO)

    self.driver = FirefoxInference.setup_driver(
      headless, firefox_bin, log_firefox, ml_prefs
    )
    self.runner_js = _load_runner_js()

  def _run_page_extractor(self, command: str, *args: Any) -> Any:
    with self.driver.context(self.driver.CONTEXT_CHROME):
      response = self.driver.execute_async_script(self.runner_js, command, *args)

    response_name = response and response.get("name")
    if response_name == "success":
      return response["result"]

    if response_name == "error":
      error_details = response.get("error") or {}
      message = error_details.get("message") or response.get("error")
      raise RuntimeError(f"{command} failed: {message}")

    raise RuntimeError(f"{command} failed with no response: {response}")

  def _extract_after_navigation(self, url: str, command: str, *args: Any) -> Any:
    logger.info("Loading page for %s -> %s", command, url)
    self.driver.get(url)
    time.sleep(1)
    return self._run_page_extractor(command, *args)

  @staticmethod
  def setup_driver(
    headless: bool,
    firefox_bin: Optional[Path],
    log_firefox: bool,
    ml_prefs: Optional[Dict[str, Any]] = None,
  ) -> webdriver.Firefox:
    options = webdriver.FirefoxOptions()
    options.add_argument("-remote-allow-system-access")
    if headless:
      options.add_argument("-headless")

    if firefox_bin:
      if not firefox_bin.exists():
        raise FileNotFoundError(f"Firefox binary not found: {firefox_bin}")
      options.binary_location = str(firefox_bin)

    service = None
    if log_firefox:
      service = webdriver.FirefoxService(
        log_output=subprocess.STDOUT, service_args=["--log-no-truncate"]
      )

    prefs = {
      "browser.ml.enable": True,
      "browser.ml.logLevel": "All",
      "browser.translations.enable": True,
      "browser.translations.logLevel": "All",
      "browser.translations.automaticallyPopup": False,
    }
    if ml_prefs:
      prefs.update(ml_prefs)

    for pref, value in prefs.items():
      options.set_preference(pref, value)

    return webdriver.Firefox(options=options, service=service)

  def get_page_text(
    self, url: str, options: Optional[Dict[str, Any]] = None
  ) -> Dict[str, Any]:
    """Use the PageExtractor to get page text and metadata."""
    return self._extract_after_navigation(url, "get_page_text", options or {})

  def get_reader_mode_content(self, url: str, force: bool = False) -> Optional[str]:
    """Force reader-mode extraction or only run when the page is readerable."""
    return self._extract_after_navigation(url, "get_reader_mode_content", force)

  def get_page_info(
    self, url: str, options: Optional[Dict[str, Any]] = None
  ) -> Optional[Dict[str, Any]]:
    """Retrieve pagination metadata for the current page."""
    return self._extract_after_navigation(url, "get_page_info", options or {})

  def get_selection_text(self, url: str) -> str:
    """Return the currently selected text from the loaded page."""
    return self._extract_after_navigation(url, "get_selection_text")

  def get_headless_page_text(
    self, url: str, options: Optional[Dict[str, Any]] = None
  ) -> Dict[str, Any]:
    """Use the headless PageExtractor API to load a hidden page."""
    return self._run_page_extractor("get_headless_page_text", url, options or {})

  def create_ml_engine(self, options: Dict[str, Any]) -> Dict[str, Any]:
    """Initialize an ML engine using EngineProcess.createEngine."""
    return self._run_page_extractor("create_ml_engine", options)

  def run_ml_engine(
    self,
    engine_id: str,
    *,
    args: List[Any],
    options: Optional[Dict[str, Any]] = None,
  ) -> Dict[str, Any]:
    """Run inference on an existing engine."""
    request = {"args": args}
    if options:
      request["options"] = options
    return self._run_page_extractor("run_ml_engine", engine_id, request)

  def destroy_ml_engine(
    self, engine_id: str, shutdown: bool = True
  ) -> Dict[str, Any]:
    """Terminate the underlying ML engine process."""
    return self._run_page_extractor(
      "destroy_ml_engine", engine_id, {"shutdown": shutdown}
    )

  def create_translations_session(self, language_pair: Dict[str, str]) -> Dict[str, Any]:
    """Initialize a translations engine for a given language pair."""
    return self._run_page_extractor(
      "create_translations_session", {"languagePair": language_pair}
    )

  def run_translations_session(
    self, session_id: str, *, text: str, is_html: bool = False
  ) -> Dict[str, Any]:
    """Translate arbitrary text (plain or HTML) with an existing session."""
    request = {"text": text, "isHTML": is_html}
    return self._run_page_extractor("run_translations_session", session_id, request)

  def destroy_translations_session(
    self, session_id: str, discard_translations: bool = True
  ) -> Dict[str, Any]:
    """Tear down the translations engine session and release its resources."""
    options = {"discardTranslations": discard_translations}
    return self._run_page_extractor(
      "destroy_translations_session", session_id, options
    )

  def quit(self) -> None:
    """Exit Firefox at the end of a session."""
    self.driver.quit()
