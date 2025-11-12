from pathlib import Path
import subprocess
from selenium import webdriver

options = webdriver.FirefoxOptions()
options.add_argument("-headless")
options.add_argument("-remote-allow-system-access")
# options.binary_location = firefox_bin

service = webdriver.FirefoxService(
    # log_output=subprocess.STDOUT, service_args=["--log-no-truncate"]
)

driver = webdriver.Firefox(options=options, service=service)

driver.get("https://gregtatum.com")


with Path("runner.js").open() as path:
    runner_js = path.read()

with driver.context(driver.CONTEXT_CHROME):
    print("Get the page text:")
    results = driver.execute_async_script(runner_js, "get_page_text")
    print("Page text:", results)

driver.get("https://example.com")
print(driver.title)
driver.quit()
