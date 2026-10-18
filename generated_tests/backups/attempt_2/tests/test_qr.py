from playwright.sync_api import expect
from generated_tests.pages.qr_page import QrPage

def test_qr_page(auth_page):
    qr = QrPage(auth_page)
    qr.open()
    expect(qr.heading_tables).to_be_visible()
    expect(qr.input_table_count).to_be_visible()
    expect(qr.button_generate).to_be_visible()
