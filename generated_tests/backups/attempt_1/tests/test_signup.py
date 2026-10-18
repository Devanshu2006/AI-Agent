import pytest
from playwright.sync_api import Page, expect
from generated_tests.pages.signup_page import SignupPage

def test_signup_page_elements(page: Page):
    signup = SignupPage(page)
    signup.open()
    expect(signup.fullname_input).to_be_visible()
    expect(signup.email_input).to_be_visible()
    expect(signup.password_input).to_be_visible()
    expect(signup.confirm_password_input).to_be_visible()
    expect(signup.continue_button).to_be_visible()
