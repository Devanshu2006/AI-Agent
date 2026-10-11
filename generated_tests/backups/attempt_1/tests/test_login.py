import pytest
from playwright.sync_api import Page

from generated_tests.pages.login_page import LoginPage


def test_page_title_and_elements(page: Page):
    login_page = LoginPage(page)
    login_page.navigate()
    assert login_page.get_title() == "Swag Labs"
    assert login_page.app_logo.is_visible()
    assert login_page.credentials_heading.is_visible()


def test_login_elements_visible(page: Page):
    login_page = LoginPage(page)
    login_page.navigate()
    assert login_page.username_input.is_visible()
    assert login_page.password_input.is_visible()
    assert login_page.login_button.is_visible()
    assert not login_page.login_button.is_disabled()


def test_successful_login(page: Page):
    login_page = LoginPage(page)
    login_page.navigate()
    login_page.login("standard_user", "secret_sauce")
    assert page.url == "https://www.saucedemo.com/inventory.html"


def test_empty_credentials_login(page: Page):
    login_page = LoginPage(page)
    login_page.navigate()
    login_page.login("", "")
    assert login_page.login_button.is_visible()
    assert page.url == "https://www.saucedemo.com/"


def test_locked_out_user_login(page: Page):
    login_page = LoginPage(page)
    login_page.navigate()
    login_page.login("locked_out_user", "secret_sauce")
    assert page.url == "https://www.saucedemo.com/"
    assert login_page.login_button.is_visible()