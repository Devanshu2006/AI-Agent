import pytest
from playwright.sync_api import expect
from generated_tests.pages.payment_page import PaymentPage

def test_payment_plans_display(auth_page):
    payment = PaymentPage(auth_page)
    payment.open()
    expect(payment.heading).to_be_visible()
    expect(payment.basic_heading).to_be_visible()
    expect(payment.moderate_heading).to_be_visible()
    expect(payment.premium_heading).to_be_visible()
    expect(payment.yearly_heading).to_be_visible()
