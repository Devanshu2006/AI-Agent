import pytest
from playwright.sync_api import Page, expect
from generated_tests.pages.forgot_password_page import ForgotPasswordPage

def test_forgot_password_page_elements(page: Page):
    fp = ForgotPasswordPage(page)
    fp.open()
    expect(fp.reset_button).to_be_visible()
