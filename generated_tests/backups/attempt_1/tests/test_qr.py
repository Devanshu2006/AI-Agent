import pytest
from playwright.sync_api import expect
from generated_tests.pages.qr_page import QrPage

def test_qr_page_elements(auth_page):
    qr = QrPage(auth_page)
    qr.open()
    expect(qr.heading).to_be_visible()
    expect(qr.table_count_input).to_be_visible()
    expect(qr.generate_button.locator("visible=True")).to_be_visible()
