import pytest
from playwright.sync_api import expect
from generated_tests.pages.settings_page import SettingsPage

def test_settings_page_elements(auth_page):
    settings = SettingsPage(auth_page)
    settings.open()
    expect(settings.payment_info_heading).to_be_visible()
    expect(settings.delete_heading).to_be_visible()
    expect(settings.account_info_button).to_be_visible()
    expect(settings.submit_upi_button).to_be_visible()
    expect(settings.update_upi_button).to_be_visible()
    expect(settings.change_password_button).to_be_visible()
    expect(settings.logout_link).to_be_visible()
    expect(settings.delete_account_button).to_be_visible()
