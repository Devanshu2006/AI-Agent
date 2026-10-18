from playwright.sync_api import Page
from generated_tests.pages.home_page import HomePage
from generated_tests.pages.login_page import LoginPage
from generated_tests.pages.signup_page import SignupPage
from generated_tests.pages.policy_pages import PolicyPages
from generated_tests.pages.auth_extras_page import AuthExtrasPage

def test_homepage(page: Page):
    home = HomePage(page)
    home.navigate()
    home.verify_main_heading()

def test_login_page(page: Page):
    login = LoginPage(page)
    login.navigate()
    login.verify_elements()

def test_signup_page(page: Page):
    signup = SignupPage(page)
    signup.navigate()
    signup.verify_elements()

def test_privacy_policy(page: Page):
    policies = PolicyPages(page)
    policies.navigate_privacy()
    policies.verify_privacy()

def test_terms_conditions(page: Page):
    policies = PolicyPages(page)
    policies.navigate_terms()
    policies.verify_terms()

def test_contact_page(page: Page):
    policies = PolicyPages(page)
    policies.navigate_contact()
    policies.verify_contact()

def test_refund_policy(page: Page):
    policies = PolicyPages(page)
    policies.navigate_refund()
    policies.verify_refund()

def test_shipping_policy(page: Page):
    policies = PolicyPages(page)
    policies.navigate_shipping()
    policies.verify_shipping()

def test_forgot_password_page(page: Page):
    extras = AuthExtrasPage(page)
    extras.navigate_forgot_password()
    extras.verify_forgot_password()

def test_staff_login_page(page: Page):
    extras = AuthExtrasPage(page)
    extras.navigate_staff_login()
    extras.verify_staff_login()