import pytest
from playwright.sync_api import Page, expect
from generated_tests.pages.refund_page import RefundPage

def test_refund_page_content(page: Page):
    refund = RefundPage(page)
    refund.open()
    expect(refund.heading).to_be_visible()
