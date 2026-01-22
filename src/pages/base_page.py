from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait


class BasePage:
    def __init__(self, driver: WebDriver, base_url: str, timeout: int = 10):
        self.driver = driver
        self.base_url = base_url.rstrip("/")
        self.wait = WebDriverWait(driver, timeout)

    def open(self, path: str = ""):
        url = f"{self.base_url}/{path.lstrip('/')}" if path else f"{self.base_url}/"
        self.driver.get(url)

    @property
    def current_url(self) -> str:
        return self.driver.current_url

    def assert_url_equals(self, expected: str):
        actual = self.current_url
        assert actual == expected, f"Expected URL '{expected}', got '{actual}'"

    def assert_url_endswith(self, suffix: str):
        actual = self.current_url
        assert actual.endswith(suffix), f"Expected URL to end with '{suffix}', got '{actual}'"
