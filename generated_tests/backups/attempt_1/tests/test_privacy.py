import pytest
from playwright.sync_api import Page, expect
from generated_tests.pages.privacy_page import PrivacyPage

def test_privacy_page_content(page: Page):
    privacy = PrivacyPage(page)
    privacy.open()
    expect(privacy.heading).to_be_visible()
