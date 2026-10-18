import pytest
from playwright.sync_api import Page, expect
from generated_tests.pages.home_page import HomePage

def test_home_page_elements(page: Page):
    home = HomePage(page)
    home.open()
    expect(home.main_heading).to_be_visible()
    expect(home.login_link).to_be_visible()
    expect(home.signup_link).to_be_visible()
