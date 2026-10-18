import pytest
from playwright.sync_api import Page, expect
from generated_tests.pages.terms_page import TermsPage

def test_terms_page_content(page: Page):
    terms = TermsPage(page)
    terms.open()
    expect(terms.heading).to_be_visible()
