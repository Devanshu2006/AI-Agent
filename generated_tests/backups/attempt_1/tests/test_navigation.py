import pytest
from playwright.sync_api import expect
from generated_tests.pages.home_page import HomePage
from generated_tests.pages.login_page import LoginPage
from generated_tests.pages.shipping_page import ShippingPage

def test_home_to_login_navigation(page):
    home = HomePage(page)
    home.open()
    home.click_login()
    expect(page).to_url("https://denqr.onrender.com/login")

def test_home_to_signup_navigation(page):
    home = HomePage(page)
    home.open()
    home.click_signup()
    expect(page).to_url("https://denqr.onrender.com/Admin")

def test_login_to_staff_login_navigation(page):
    login = LoginPage(page)
    login.open()
    login.click_staff_login()
    expect(page).to_url("https://denqr.onrender.com/staff_login")

def test_shipping_back_home_navigation(page):
    shipping = ShippingPage(page)
    shipping.open()
    shipping.back_home_link.click()
    expect(page).to_url("https://denqr.onrender.com/")
