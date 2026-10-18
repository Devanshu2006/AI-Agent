import pytest
from playwright.sync_api import Page, expect
from generated_tests.pages.settings_page import SettingsPage

def test_settings_page_elements(auth_page: Page):
    settings = SettingsPage(auth_page)
    settings.open()
    expect(settings.current_password_input).to_be_visible()
    expect(settings.new_password_input).to_be_visible()
    expect(settings.confirm_password_input).to_be_visible()
