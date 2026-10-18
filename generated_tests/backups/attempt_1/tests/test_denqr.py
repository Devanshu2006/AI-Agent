import pytest
from playwright.sync_api import Page, expect
from generated_tests.pages.home_page import HomePage
from generated_tests.pages.login_page import LoginPage
from generated_tests.pages.signup_page import SignupPage
from generated_tests.pages.privacy_page import PrivacyPage
from generated_tests.pages.contact_page import ContactPage
from generated_tests.pages.staff_login_page import StaffLoginPage

def test_homepage_headings(page: Page):
    home = HomePage(page)
    home.navigate()
    expect(home.get_main_heading()).to_be_visible()
    expect(home.get_subtitle_heading()).to_be_visible()

def test_login_page_elements(page: Page):
    login = LoginPage(page)
    login.navigate()
    expect(login.get_heading()).to_be_visible()
    expect(login.get_username_input()).to_be_visible()
    expect(login.get_password_input()).to_be_visible()
    expect(login.get_login_button()).to_be_visible()

def test_signup_page_elements(page: Page):
    signup = SignupPage(page)
    signup.navigate()
    expect(signup.get_heading()).to_be_visible()
    expect(signup.get_username_input()).to_be_visible()
    expect(signup.get_email_input()).to_be_visible()
    expect(signup.get_password_input()).to_be_visible()
    expect(signup.get_confirm_password_input()).to_be_visible()
    expect(signup.get_continue_button()).to_be_visible()

def test_privacy_page_heading(page: Page):
    privacy = PrivacyPage(page)
    privacy.navigate()
    expect(privacy.get_heading()).to_be_visible()
    expect(page).toHaveTitle("Privacy Policy")

def test_contact_page_heading(page: Page):
    contact = ContactPage(page)
    contact.navigate()
    expect(contact.get_heading()).to_be_visible()

def test_staff_login_page_elements(page: Page):
    staff_login = StaffLoginPage(page)
    staff_login.navigate()
    expect(staff_login.get_heading()).to_be_visible()
    expect(staff_login.get_name_input()).to_be_visible()
    expect(staff_login.get_role_input()).to_be_visible()
    expect(staff_login.get_contact_input()).to_be_visible()