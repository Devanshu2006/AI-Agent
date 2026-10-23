import pytest
from playwright.sync_api import expect
from generated_tests.pages.privacy_page import PrivacyPage
from generated_tests.pages.terms_page import TermsPage
from generated_tests.pages.contact_page import ContactPage
from generated_tests.pages.refund_page import RefundPage
from generated_tests.pages.shipping_page import ShippingPage

def test_privacy_policy_content(page):
    privacy = PrivacyPage(page)
    privacy.open()
    expect(privacy.heading).to_be_visible()

def test_terms_conditions_content(page):
    terms = TermsPage(page)
    terms.open()
    expect(terms.heading).to_be_visible()

def test_contact_us_content(page):
    contact = ContactPage(page)
    contact.open()
    expect(contact.heading).to_be_visible()
    expect(contact.support_email).to_be_visible()

def test_refund_policy_content(page):
    refund = RefundPage(page)
    refund.open()
    expect(refund.heading).to_be_visible()

def test_shipping_policy_content(page):
    shipping = ShippingPage(page)
    shipping.open()
    expect(shipping.heading).to_be_visible()
