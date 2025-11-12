"""
Run an automated Firefox for Machine Learning tasks and evaluations.
"""

from pathlib import Path
import subprocess
from typing import Any, Dict, Optional
from selenium import webdriver
import logging

logging.basicConfig(level=logging.INFO, format="[%(name)s] %(message)s")
logger = logging.getLogger("firefox-ml")
logger.setLevel(logging.INFO)


class FirefoxInference:
    # The webdriver for Firefox.
    driver: webdriver.Firefox
    # The JS code to run privileged commands and receive a response.
    runner_js: str

    def __init__(
        self,
        headless: bool = False,
        firefox_bin: Optional[Path] = None,
        log_firefox: bool = False,
    ) -> None:

        self.driver = FirefoxInference.setup_driver(headless, firefox_bin, log_firefox)

        with Path("runner.js").open() as path:
            self.runner_js = path.read()

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
        logger.info(f"Loading page for {command} -> {url}")
        self.driver.get(url)
        return self._run_page_extractor(command, *args)

    @staticmethod
    def setup_driver(
        headless: bool, firefox_bin: Optional[Path], log_firefox: bool
    ) -> webdriver.Firefox:
        options = webdriver.FirefoxOptions()
        options.add_argument("-remote-allow-system-access")
        if headless:
            options.add_argument("-headless")

        if firefox_bin:
            assert (
                firefox_bin.exists()
            ), f"The Firefox binary did not exist: {firefox_bin}"
            options.binary_location = str(firefox_bin)

        service = None
        if log_firefox:
            service = webdriver.FirefoxService(
                log_output=subprocess.STDOUT, service_args=["--log-no-truncate"]
            )

        return webdriver.Firefox(options=options, service=service)

    def get_page_text(
        self, url: str, options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Use the PageExtractor to get page text and metadata from the active tab.
        """
        return self._extract_after_navigation(url, "get_page_text", options or {})

    def get_reader_mode_content(self, url: str, force: bool = False) -> Optional[str]:
        """
        Force Reader Mode extraction or only run when the page is readerable.
        """
        return self._extract_after_navigation(url, "get_reader_mode_content", force)

    def get_page_info(
        self, url: str, options: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve pagination metadata for the current page.
        """
        return self._extract_after_navigation(url, "get_page_info", options or {})

    def get_selection_text(self, url: str) -> str:
        """
        Return the currently selected text from the loaded page.
        """
        return self._extract_after_navigation(url, "get_selection_text")

    def get_headless_page_text(
        self, url: str, options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Use the headless PageExtractor API which loads the page in a hidden browser.
        """
        return self._run_page_extractor("get_headless_page_text", url, options or {})

    def quit(self):
        """
        Exit Firefox at the end of a session.
        """
        self.driver.quit()


def main() -> None:
    firefox_inference = FirefoxInference(headless=True, log_firefox=False)
    url = "https://arstechnica.com/culture/2025/11/nintendo-drops-official-trailer-for-super-mario-galaxy-movie/"
    page_text = firefox_inference.get_reader_mode_content(url)
    print(page_text)


if __name__ == "__main__":
    main()
