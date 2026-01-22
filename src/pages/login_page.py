from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from .base_page import BasePage


class LoginPage(BasePage):
    USERNAME = (By.CSS_SELECTOR, "[data-test='username']")
    PASSWORD = (By.CSS_SELECTOR, "[data-test='password']")
    LOGIN_BTN = (By.CSS_SELECTOR, "[data-test='login-button']")
    ERROR_MSG = (By.CSS_SELECTOR, "[data-test='error']")
    LOGIN_LOGO = (By.CSS_SELECTOR, ".login_logo")

    def open(self):
        super().open("")

    def wait_loaded(self):
        self.wait.until(EC.visibility_of_element_located(self.LOGIN_LOGO))
        self.wait.until(EC.visibility_of_element_located(self.USERNAME))
        self.wait.until(EC.visibility_of_element_located(self.PASSWORD))
        self.wait.until(EC.visibility_of_element_located(self.LOGIN_BTN))

    def login(self, username: str, password: str):
        u = self.wait.until(EC.visibility_of_element_located(self.USERNAME))
        p = self.wait.until(EC.visibility_of_element_located(self.PASSWORD))

        u.clear()
        u.send_keys(username)
        p.clear()
        p.send_keys(password)

        self.driver.find_element(*self.LOGIN_BTN).click()

    def _error(self) -> str:
        err = self.wait.until(EC.visibility_of_element_located(self.ERROR_MSG))
        return err.text

    def assert_error_contains(self, text_part: str):
        text = self._error()
        assert text_part in text, f"Expected error to contain '{text_part}', got '{text}'"
