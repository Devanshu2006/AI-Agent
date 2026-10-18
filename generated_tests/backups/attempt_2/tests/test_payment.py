from playwright.sync_api import expect
from generated_tests.pages.payment_page import PaymentPage

def test_payment_page(auth_page):
    payment = PaymentPage(auth_page)
    payment.open()
    expect(payment.heading_journey).to_be_visible()
    expect(payment.heading_basic).to_be_visible()
    expect(payment.heading_moderate).to_be_visible()
    expect(payment.heading_premium).to_be_visible()
    expect(payment.heading_yearly).to_be_visible()
