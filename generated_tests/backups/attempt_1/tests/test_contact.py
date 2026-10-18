import pytest
from playwright.sync_api import Page, expect
from generated_tests.pages.contact_page import ContactPage

def test_contact_page_content(page: Page):
    contact = ContactPage(page)
    contact.open()
    expect(contact.heading).to_be_visible()
