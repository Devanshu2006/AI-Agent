import pytest
from playwright.sync_api import Page, expect
from generated_tests.pages.payment_page import PaymentPage

def test_payment_page_elements(auth_page: Page):
    payment = PaymentPage(auth_page)
    payment.open()
    expect(payment.basic_heading).to_be_visible()
    expect(payment.moderate_heading).to_be_visible()
