import allure
import pytest

from src.pages.login_page import LoginPage
from src.pages.inventory_page import InventoryPage


@allure.feature("Authorization")
@allure.story("Successful login")
@pytest.mark.smoke
def test_login_success(driver, base_url):
    login = LoginPage(driver, base_url)
    inventory = InventoryPage(driver, base_url)

    with allure.step("Given: открыта страница логина"):
        login.open()
        login.wait_loaded()
        login.assert_url_equals(f"{base_url}/")

    with allure.step("When: выполняю логин standard_user / secret_sauce"):
        login.login("standard_user", "secret_sauce")

    with allure.step("Then: открыта inventory (Products) и URL оканчивается на /inventory.html"):
        inventory.wait_loaded()


@allure.feature("Authorization")
@allure.story("Invalid password")
def test_login_wrong_password(driver, base_url):
    login = LoginPage(driver, base_url)

    with allure.step("Given: открыта страница логина"):
        login.open()
        login.wait_loaded()
        login.assert_url_equals(f"{base_url}/")

    with allure.step("When: ввожу корректный username и неверный password"):
        login.login("standard_user", "wrong_password")

    with allure.step("Then: остаюсь на странице логина и вижу сообщение об ошибке"):
        login.assert_url_equals(f"{base_url}/")
        login.assert_error_contains("Username and password do not match")


@allure.feature("Authorization")
@allure.story("Locked out user")
def test_login_locked_out_user(driver, base_url):
    login = LoginPage(driver, base_url)

    with allure.step("Given: открыта страница логина"):
        login.open()
        login.wait_loaded()
        login.assert_url_equals(f"{base_url}/")

    with allure.step("When: пытаюсь войти пользователем locked_out_user"):
        login.login("locked_out_user", "secret_sauce")

    with allure.step("Then: остаюсь на странице логина и вижу ошибку о блокировке"):
        login.assert_url_equals(f"{base_url}/")
        login.assert_error_contains("Sorry, this user has been locked out")


@allure.feature("Authorization")
@allure.story("Empty fields")
def test_login_empty_fields(driver, base_url):
    login = LoginPage(driver, base_url)

    with allure.step("Given: открыта страница логина"):
        login.open()
        login.wait_loaded()
        login.assert_url_equals(f"{base_url}/")

    with allure.step("When: нажимаю Login с пустыми полями"):
        login.login("", "")

    with allure.step("Then: вижу валидационное сообщение 'Username is required'"):
        login.assert_url_equals(f"{base_url}/")
        login.assert_error_contains("Username is required")


@allure.feature("Authorization")
@allure.story("Performance glitch user")
@pytest.mark.flaky
def test_login_performance_glitch_user(driver, base_url):
    # timeout повышаем только тут: пользователь может логиниться дольше
    login = LoginPage(driver, base_url, timeout=15)
    inventory = InventoryPage(driver, base_url, timeout=15)

    with allure.step("Given: открыта страница логина"):
        login.open()
        login.wait_loaded()
        login.assert_url_equals(f"{base_url}/")

    with allure.step("When: выполняю логин performance_glitch_user / secret_sauce (возможны задержки)"):
        login.login("performance_glitch_user", "secret_sauce")

    with allure.step("Then: открыта inventory (Products), элементы видимы, URL корректный"):
        inventory.wait_loaded()
