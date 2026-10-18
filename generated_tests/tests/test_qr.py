import pytest
from playwright.sync_api import Page, expect
from generated_tests.pages.qr_page import QrPage

def test_qr_page_elements(auth_page: Page):
    qr = QrPage(auth_page)
    qr.open()
    expect(qr.table_count_input).to_be_visible()
    expect(qr.generate_button).to_be_visible()
