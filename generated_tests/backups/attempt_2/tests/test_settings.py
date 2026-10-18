from playwright.sync_api import expect
from generated_tests.pages.settings_page import SettingsPage

def test_settings_page(auth_page):
    settings = SettingsPage(auth_page)
    settings.open()
    expect(settings.heading_payment_info).to_be_visible()
    expect(settings.heading_delete_account).to_be_visible()
    expect(settings.input_upi_id).to_be_visible()
    expect(settings.input_current_password).to_be_visible()
    expect(settings.input_new_password).to_be_visible()
    expect(settings.input_confirm_password).to_be_visible()
    expect(settings.button_delete_account).to_be_visible()
