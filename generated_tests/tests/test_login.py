import pytest
from playwright.sync_api import Page, expect
from generated_tests.pages.login_page import LoginPage

def test_login_page_elements(page: Page):
    login = LoginPage(page)
    login.open()
    expect(login.email_input).to_be_visible()
    expect(login.password_input).to_be_visible()
    expect(login.login_button).to_be_visible()
