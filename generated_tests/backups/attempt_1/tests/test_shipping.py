import pytest
from playwright.sync_api import expect
from generated_tests.pages.shipping_page import ShippingPage

def test_shipping_page_navigation(page):
    shipping = ShippingPage(page)
    shipping.open()
    expect(shipping.heading).to_be_visible()
    expect(shipping.back_home_link).to_be_visible()
    shipping.back_home_link.click()
    expect(page).to_url("https://denqr.onrender.com/")
