"""
Run an automated Firefox for Machine Learning tasks and evaluations.
"""

import argparse
from pathlib import Path
import subprocess
from typing import Optional
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

    def get_page_text(self, url: str):
        """
        Use the PageExtractor to get page text
        """
        logger.info(f"Loading page to get text {url}")
        self.driver.get(url)
        with self.driver.context(self.driver.CONTEXT_CHROME):
            response = self.driver.execute_async_script(self.runner_js, "get_page_text")
            response_name = response and response.get("name")
            if response_name == "success":
                return response["result"]
            if response_name == "error":
                print(response.get("error"))
                raise Exception(f"get_page_text failed to run for {url}")

            print(response)
            raise Exception(f"get_page_text failed with no response")

    def quit(self):
        """
        Exit Firefox at the end of a session.
        """
        self.driver.quit()


def main() -> None:
    firefox_inference = FirefoxInference(headless=True, log_firefox=False)
    page_text = firefox_inference.get_page_text(
        "https://arstechnica.com/culture/2025/11/nintendo-drops-official-trailer-for-super-mario-galaxy-movie/"
    )
    print(page_text)


if __name__ == "__main__":
    main()
