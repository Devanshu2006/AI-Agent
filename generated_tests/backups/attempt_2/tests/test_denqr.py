from playwright.sync_api import Page, expect
from generated_tests.pages.home_page import HomePage
from generated_tests.pages.login_page import LoginPage
from generated_tests.pages.signup_page import SignupPage
from generated_tests.pages.forgot_password_page import ForgotPasswordPage
from generated_tests.pages.staff_login_page import StaffLoginPage
from generated_tests.pages.privacy_page import PrivacyPage

def test_home_page_elements(page: Page):
    home_page = HomePage(page)
    home_page.load()
    expect(page).to_have_title("DenQr - Effortless Restaurant Ordering")
    expect(home_page.heading).to_be_visible()
    expect(home_page.login_link).to_be_visible()
    expect(home_page.signup_link).to_be_visible()

def test_login_page_elements(page: Page):
    login_page = LoginPage(page)
    login_page.load()
    expect(page).to_have_title("Login page")
    login_page.verify_elements()

def test_signup_page_elements(page: Page):
    signup_page = SignupPage(page)
    signup_page.load()
    expect(page).to_have_title("Create Account")
    signup_page.verify_elements()

def test_forgot_password_page_elements(page: Page):
    forgot_page = ForgotPasswordPage(page)
    forgot_page.load()
    expect(page).to_have_title("Forgot Password")
    forgot_page.verify_elements()

def test_staff_login_page_elements(page: Page):
    staff_page = StaffLoginPage(page)
    staff_page.load()
    expect(page).to_have_title("Login page")
    staff_page.verify_elements()

def test_privacy_page_elements(page: Page):
    privacy_page = PrivacyPage(page)
    privacy_page.load()
    expect(page).to_have_title("Privacy Policy")
    privacy_page.verify_elements()