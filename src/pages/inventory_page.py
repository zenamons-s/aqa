from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from .base_page import BasePage


class InventoryPage(BasePage):
    TITLE = (By.CSS_SELECTOR, ".title")
    INVENTORY_CONTAINER = (By.CSS_SELECTOR, "#inventory_container")
    BURGER_MENU = (By.CSS_SELECTOR, "#react-burger-menu-btn")

    def wait_loaded(self):
        title = self.wait.until(EC.visibility_of_element_located(self.TITLE))
        assert title.text == "Products", f"Expected title 'Products', got '{title.text}'"

        self.wait.until(EC.visibility_of_element_located(self.INVENTORY_CONTAINER))
        self.wait.until(EC.visibility_of_element_located(self.BURGER_MENU))

        self.assert_url_endswith("/inventory.html")
