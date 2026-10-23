import pytest
from playwright.sync_api import expect
from generated_tests.pages.contact_page import ContactPage

def test_contact_page_content(page):
    contact = ContactPage(page)
    contact.open()
    expect(contact.heading).to_be_visible()
    expect(contact.general_inquiries).to_be_visible()
    expect(contact.subscription_support).to_be_visible()
    expect(contact.mailing_address).to_be_visible()
    expect(contact.feedback_suggestions).to_be_visible()
    expect(contact.support_email).to_be_visible()
    expect(contact.subscriptions_email).to_be_visible()
    expect(contact.feedback_email).to_be_visible()
